<script setup lang="ts">
import HexWorldMap from '@/components/HexWorldMapOptimized.vue'
import IndustryPieChart from '@/components/IndustryPieChart.vue'
import PortfolioOutput from '@/components/PortfolioOutput.vue'
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { optimizePortfolio, getDefaultMSCIWorldData, getAvailableCountries, getAvailableIndustries } from '@/services/etfService'

// State
const allocations = reactive({
  countries: {} as Record<string, number>,
  industries: {} as Record<string, number>
})

const portfolioResult = ref(null as any)
const loading = ref(false)
const scrollY = ref(0)
const countrySearch = ref('')
const industrySearch = ref('')
const windowHeight = ref(0)
const scrollLocked = ref(false)
const lockScrollPosition = ref(0)

// Default MSCI World for initial display
const defaultData = getDefaultMSCIWorldData()
const currentCountryData = ref<Record<string, number>>(defaultData.countries)
const currentIndustryData = ref<Record<string, number>>(defaultData.industries)

const availableCountries = ref<string[]>([])
const availableIndustries = ref<string[]>([])

// Arrow opacity - fades when scrolling
const arrowOpacity = computed(() => {
  return Math.max(0, 1 - scrollY.value / 200)
})

// Check if map should be sticky
const mapIsSticky = computed(() => {
  return scrollY.value > windowHeight.value * 0.33
})

// Header sticky state - becomes small and moves to top left
const headerIsSticky = computed(() => {
  return scrollY.value > 100
})

// Divider opacity - fades in when scrolling
const dividerOpacity = computed(() => {
  return Math.min(1, scrollY.value / 200)
})

// Computed values
const unallocatedCountries = computed(() => {
  const allocated = Object.values(allocations.countries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

const unallocatedIndustries = computed(() => {
  const allocated = Object.values(allocations.industries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

// Selected countries and industries (displayed in the UI)
const selectedCountries = ref<string[]>([])
const selectedIndustries = ref<string[]>([])

// Max items that can be displayed
const MAX_DISPLAYED_ITEMS = 5

// Top countries and industries
const topCountries = computed(() => {
  return selectedCountries.value.map(name => ({
    name,
    current: currentCountryData.value[name] || 0,
    allocated: allocations.countries[name] || currentCountryData.value[name] || 0
  }))
})

const topIndustries = computed(() => {
  return selectedIndustries.value.map(name => ({
    name,
    current: currentIndustryData.value[name] || 0,
    allocated: allocations.industries[name] || currentIndustryData.value[name] || 0
  }))
})

// Check if more items can be added
const canAddMoreCountries = computed(() => selectedCountries.value.length < MAX_DISPLAYED_ITEMS)
const canAddMoreIndustries = computed(() => selectedIndustries.value.length < MAX_DISPLAYED_ITEMS)

// Filtered countries for search
const filteredCountries = computed(() => {
  if (!countrySearch.value) return []
  const search = countrySearch.value.toLowerCase()
  return availableCountries.value
    .filter(c => 
      c.toLowerCase().includes(search) && 
      !selectedCountries.value.includes(c)
    )
    .slice(0, 10)
})

const filteredIndustries = computed(() => {
  if (!industrySearch.value) return []
  const search = industrySearch.value.toLowerCase()
  return availableIndustries.value
    .filter(i => 
      i.toLowerCase().includes(search) && 
      !selectedIndustries.value.includes(i)
    )
    .slice(0, 10)
})

// Scroll handler
function handleScroll() {
  const currentScroll = window.scrollY
  
  // Lock position is roughly when map reaches the top (after ~66% of viewport height)
  const lockPosition = windowHeight.value * 0.64
  
  // Once we pass the lock position, prevent scrolling back up
  if (currentScroll >= lockPosition && !scrollLocked.value) {
    scrollLocked.value = true
    lockScrollPosition.value = lockPosition
  }
  
  // Prevent scrolling back above the lock position
  if (scrollLocked.value && currentScroll < lockScrollPosition.value) {
    window.scrollTo(0, lockScrollPosition.value)
    scrollY.value = lockScrollPosition.value
    return
  }
  
  scrollY.value = currentScroll
}

function handleResize() {
  windowHeight.value = window.innerHeight
}

onMounted(async () => {
  window.addEventListener('scroll', handleScroll)
  window.addEventListener('resize', handleResize)
  windowHeight.value = window.innerHeight
  
  // Load available options
  try {
    const [countries, industries] = await Promise.all([
      getAvailableCountries(),
      getAvailableIndustries()
    ])
    availableCountries.value = countries
    availableIndustries.value = industries
  } catch (error) {
    console.error('Failed to load available options:', error)
  }
  
  // Initialize selected countries and industries with top 3
  const sortedCountries = Object.entries(currentCountryData.value)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name]) => name)
  
  const sortedIndustries = Object.entries(currentIndustryData.value)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name]) => name)
  
  selectedCountries.value = sortedCountries
  selectedIndustries.value = sortedIndustries
  
  // Initialize allocations with selected items only
  sortedCountries.forEach(name => {
    allocations.countries[name] = currentCountryData.value[name]
  })
  sortedIndustries.forEach(name => {
    allocations.industries[name] = currentIndustryData.value[name]
  })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('resize', handleResize)
})

async function optimizeAndUpdate() {
  if (loading.value) return
  
  loading.value = true
  try {
    // Only send allocations for selected/displayed items
    const selectedCountryAllocations: Record<string, number> = {}
    const selectedIndustryAllocations: Record<string, number> = {}
    
    selectedCountries.value.forEach(country => {
      selectedCountryAllocations[country] = allocations.countries[country] || 0
    })
    
    selectedIndustries.value.forEach(industry => {
      selectedIndustryAllocations[industry] = allocations.industries[industry] || 0
    })
    
    const result = await optimizePortfolio(selectedCountryAllocations, selectedIndustryAllocations)
    portfolioResult.value = result
    
    // Update current data with achieved allocations
    currentCountryData.value = result.achieved_countries
    currentIndustryData.value = result.achieved_industries
  } catch (error) {
    console.error('Optimization failed:', error)
  } finally {
    loading.value = false
  }
}

function updateCountryAllocation(country: string, value: number) {
  allocations.countries[country] = value
}

function updateIndustryAllocation(industry: string, value: number) {
  allocations.industries[industry] = value
}

function addCountryFromSearch(country: string) {
  if (!canAddMoreCountries.value) return
  
  const currentValue = currentCountryData.value[country] || 5
  selectedCountries.value.push(country)
  allocations.countries[country] = currentValue
  countrySearch.value = ''
}

function addIndustryFromSearch(industry: string) {
  if (!canAddMoreIndustries.value) return
  
  const currentValue = currentIndustryData.value[industry] || 5
  selectedIndustries.value.push(industry)
  allocations.industries[industry] = currentValue
  industrySearch.value = ''
}

function removeCountry(country: string) {
  const index = selectedCountries.value.indexOf(country)
  if (index > -1) {
    selectedCountries.value.splice(index, 1)
    delete allocations.countries[country]
  }
}

function removeIndustry(industry: string) {
  const index = selectedIndustries.value.indexOf(industry)
  if (index > -1) {
    selectedIndustries.value.splice(index, 1)
    delete allocations.industries[industry]
  }
}

function resetToMSCI() {
  Object.keys(allocations.countries).forEach(key => delete allocations.countries[key])
  Object.keys(allocations.industries).forEach(key => delete allocations.industries[key])
  
  currentCountryData.value = defaultData.countries
  currentIndustryData.value = defaultData.industries
  
  // Re-initialize with top 3
  const sortedCountries = Object.entries(defaultData.countries)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name]) => name)
  
  const sortedIndustries = Object.entries(defaultData.industries)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([name]) => name)
  
  selectedCountries.value = sortedCountries
  selectedIndustries.value = sortedIndustries
  
  sortedCountries.forEach(name => {
    allocations.countries[name] = (defaultData.countries as Record<string, number>)[name]
  })
  sortedIndustries.forEach(name => {
    allocations.industries[name] = (defaultData.industries as Record<string, number>)[name]
  })
  
  portfolioResult.value = null
  
  // Unlock scroll when resetting
  scrollLocked.value = false
  lockScrollPosition.value = 0
  
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="min-h-screen bg-black text-white">
    
    <!-- Sticky Header - Logo and Title -->
    <div 
      class="fixed top-0 left-0 right-0 bg-black transition-all duration-300 z-50"
      :class="headerIsSticky ? 'translate-y-0' : '-translate-y-full'"
    >
      <div class="px-6 py-4 flex items-center gap-3">
        <!-- Logo -->
        <img 
          src="/logo-cropped.png" 
          alt="Build your ETF Logo" 
          class="w-8 h-8 object-contain"
        />
        <!-- Text -->
        <h1 class="text-xl font-light">
          Build <span class="border-b-2 border-white">Your</span> ETF
        </h1>
      </div>
      <!-- Divider -->
      <div 
        class="h-px bg-gray-800 transition-opacity duration-300"
        :style="{ opacity: dividerOpacity }"
      ></div>
    </div>
    
    <!-- Hero Section - Simple 3-part layout -->
    <div class="h-screen flex flex-col relative">
      
      <!-- Top 1/3 - Centered Text -->
      <div class="flex-1 flex items-center justify-center px-6">
        <div class="flex items-center gap-6 max-w-4xl">
          <!-- Logo -->
          <img 
            src="/logo-cropped.png" 
            alt="Build your ETF Logo" 
            class="w-24 h-24 md:w-24 md:h-24 object-contain"
          />
          <!-- Text -->
          <div class="space-y-4">
            <h1 class="text-4xl md:text-6xl font-light leading-tight">
              Build <span class="border-b-4 border-white">Your</span> ETF
            </h1>
          </div>
        </div>
      </div>

      <!-- Middle 1/3 - Country Allocation Map (Sticky in center) -->
      <div class="flex-1 px-6 flex items-center justify-center sticky top-1/3">
        <div class="w-full max-w-6xl h-full flex items-center">
          <HexWorldMap :countryData="currentCountryData" class="w-full h-full" />
        </div>
      </div>

      <!-- Bottom 1/3 - Pulsing Arrow -->
      <div 
        class="flex-1 flex items-center justify-center transition-opacity duration-300"
        :style="{ opacity: arrowOpacity }"
      >
        <div class="text-center">
          <div class="text-gray-400 text-sm mb-4">Scroll to customize</div>
          <div class="animate-bounce">
            <svg class="w-8 h-8 mx-auto text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Section - Stacked -->
    <div class=" bg-black px-6 py-12">
      <div class="max-w-6xl mx-auto space-y-12">
        

        <!-- Industry Bar Chart -->
        <div class="space-y-4">
          <div class="bg-black" style="height: 120px;">
            <IndustryPieChart :industryData="currentIndustryData" />
          </div>
        </div>
      </div>
    </div>

    <!-- Controls Section -->
    <div class="relative bg-black border-t border-gray-800 min-h-screen px-4 py-8">
      <div class="max-w-6xl mx-auto">
        
        <!-- Header -->
        <div class="mb-8 flex justify-between items-center">
          <h2 class="text-2xl font-light">Customize Your Portfolio</h2>
          <button 
            @click="resetToMSCI"
            class="text-xs border border-gray-600 px-4 py-2 hover:bg-white hover:text-black transition-colors"
          >
            Reset
          </button>
        </div>

        <!-- Split Controls -->
        <div class="grid md:grid-cols-2 gap-6 mb-8">
          
          <!-- Countries Column -->
          <div class="space-y-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-medium">Countries</h3>
              <span class="text-sm text-gray-400">
                {{ unallocatedCountries.toFixed(1) }}% unallocated
              </span>
            </div>

            <!-- Search -->
            <div class="relative">
              <input
                v-model="countrySearch"
                type="text"
                placeholder="Search countries..."
                :disabled="!canAddMoreCountries"
                class="w-full bg-gray-900 border border-gray-700 rounded px-4 py-2 text-sm focus:outline-none focus:border-white disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <div 
                v-if="filteredCountries.length > 0 && canAddMoreCountries"
                class="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded max-h-48 overflow-y-auto z-10"
              >
                <button
                  v-for="country in filteredCountries"
                  :key="country"
                  @click="addCountryFromSearch(country)"
                  class="w-full text-left px-4 py-2 hover:bg-gray-800 text-sm flex items-center justify-between group"
                >
                  <span>{{ country }}</span>
                  <span class="text-xs text-gray-500 group-hover:text-white">+ Add</span>
                </button>
              </div>
            </div>
            
            <div v-if="!canAddMoreCountries" class="text-xs text-gray-500">
              Maximum of {{ MAX_DISPLAYED_ITEMS }} countries. Remove one to add more.
            </div>

            <!-- Countries with Sliders -->
            <div class="space-y-4">
              <div 
                v-for="item in topCountries" 
                :key="item.name"
                class="space-y-2"
              >
                <div class="flex justify-between text-sm items-center">
                  <span class="font-medium">{{ item.name }}</span>
                  <div class="flex items-center gap-2">
                    <span class="text-gray-400">{{ item.allocated.toFixed(1) }}%</span>
                    <button
                      @click="removeCountry(item.name)"
                      class="text-red-500 hover:text-red-400 text-xs"
                      title="Remove country"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                
                <!-- Slider with current value indicator -->
                <div class="relative">
                  <input
                    type="range"
                    :value="item.allocated"
                    @input="updateCountryAllocation(item.name, parseFloat(($event.target as HTMLInputElement).value))"
                    min="0"
                    max="100"
                    step="0.1"
                    class="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <!-- Current value indicator (dashed line) -->
                  <div 
                    class="absolute top-0 bottom-0 w-0.5 border-l-2 border-dashed border-gray-500 pointer-events-none"
                    :style="{ left: `${item.current}%` }"
                  ></div>
                </div>
              </div>
            </div>

          </div>

          <!-- Industries Column -->
          <div class="space-y-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-medium">Industries</h3>
              <span class="text-sm text-gray-400">
                {{ unallocatedIndustries.toFixed(1) }}% unallocated
              </span>
            </div>

            <!-- Search -->
            <div class="relative">
              <input
                v-model="industrySearch"
                type="text"
                placeholder="Search industries..."
                :disabled="!canAddMoreIndustries"
                class="w-full bg-gray-900 border border-gray-700 rounded px-4 py-2 text-sm focus:outline-none focus:border-white disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <div 
                v-if="filteredIndustries.length > 0 && canAddMoreIndustries"
                class="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded max-h-48 overflow-y-auto z-10"
              >
                <button
                  v-for="industry in filteredIndustries"
                  :key="industry"
                  @click="addIndustryFromSearch(industry)"
                  class="w-full text-left px-4 py-2 hover:bg-gray-800 text-sm flex items-center justify-between group"
                >
                  <span>{{ industry }}</span>
                  <span class="text-xs text-gray-500 group-hover:text-white">+ Add</span>
                </button>
              </div>
            </div>
            
            <div v-if="!canAddMoreIndustries" class="text-xs text-gray-500">
              Maximum of {{ MAX_DISPLAYED_ITEMS }} industries. Remove one to add more.
            </div>

            <!-- Industries with Sliders -->
            <div class="space-y-4">
              <div 
                v-for="item in topIndustries" 
                :key="item.name"
                class="space-y-2"
              >
                <div class="flex justify-between text-sm items-center">
                  <span class="font-medium">{{ item.name }}</span>
                  <div class="flex items-center gap-2">
                    <span class="text-gray-400">{{ item.allocated.toFixed(1) }}%</span>
                    <button
                      @click="removeIndustry(item.name)"
                      class="text-red-500 hover:text-red-400 text-xs"
                      title="Remove industry"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                
                <!-- Slider with current value indicator -->
                <div class="relative">
                  <input
                    type="range"
                    :value="item.allocated"
                    @input="updateIndustryAllocation(item.name, parseFloat(($event.target as HTMLInputElement).value))"
                    min="0"
                    max="100"
                    step="0.1"
                    class="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <!-- Current value indicator (dashed line) -->
                  <div 
                    class="absolute top-0 bottom-0 w-0.5 border-l-2 border-dashed border-gray-500 pointer-events-none"
                    :style="{ left: `${item.current}%` }"
                  ></div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Optimize Button -->
        <div class="sticky bottom-0 bg-black py-6 border-t border-gray-800">
          <button
            @click="optimizeAndUpdate"
            :disabled="loading"
            class="w-full bg-white text-black py-4 text-lg font-medium hover:bg-gray-200 transition-colors disabled:bg-gray-700 disabled:text-gray-400"
          >
            {{ loading ? 'Optimizing...' : 'Optimize Portfolio' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Portfolio Output Section -->
    <section v-if="portfolioResult" class="py-16 px-4 border-t border-gray-800 bg-black">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-3xl font-light mb-8">Your Optimized ETF Portfolio</h2>
        <PortfolioOutput :result="portfolioResult" />
      </div>
    </section>
  </div>
</template>

<style scoped>
/* Custom slider styling */
.slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: 2px solid black;
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  cursor: pointer;
  border: 2px solid black;
}

.slider::-webkit-slider-track {
  background: #1f2937;
  border-radius: 4px;
}

.slider::-moz-range-track {
  background: #1f2937;
  border-radius: 4px;
}
</style>