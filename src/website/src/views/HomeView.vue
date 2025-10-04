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

// Computed values
const unallocatedCountries = computed(() => {
  const allocated = Object.values(allocations.countries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

const unallocatedIndustries = computed(() => {
  const allocated = Object.values(allocations.industries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

// Top countries and industries
const topCountries = computed(() => {
  return Object.entries(currentCountryData.value)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, current]) => ({ 
      name, 
      current,
      allocated: allocations.countries[name] || current
    }))
})

const topIndustries = computed(() => {
  return Object.entries(currentIndustryData.value)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, current]) => ({ 
      name, 
      current,
      allocated: allocations.industries[name] || current
    }))
})

// Filtered countries for search
const filteredCountries = computed(() => {
  if (!countrySearch.value) return []
  const search = countrySearch.value.toLowerCase()
  return availableCountries.value
    .filter(c => c.toLowerCase().includes(search))
    .slice(0, 10)
})

const filteredIndustries = computed(() => {
  if (!industrySearch.value) return []
  const search = industrySearch.value.toLowerCase()
  return availableIndustries.value
    .filter(i => i.toLowerCase().includes(search))
    .slice(0, 10)
})

// Scroll handler
function handleScroll() {
  scrollY.value = window.scrollY
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
  
  // Initialize allocations with current data
  Object.entries(currentCountryData.value).forEach(([name, value]) => {
    allocations.countries[name] = value
  })
  Object.entries(currentIndustryData.value).forEach(([name, value]) => {
    allocations.industries[name] = value
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
    const result = await optimizePortfolio(allocations.countries, allocations.industries)
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
  const currentValue = currentCountryData.value[country] || 5
  allocations.countries[country] = currentValue
  countrySearch.value = ''
}

function addIndustryFromSearch(industry: string) {
  const currentValue = currentIndustryData.value[industry] || 5
  allocations.industries[industry] = currentValue
  industrySearch.value = ''
}

function resetToMSCI() {
  Object.keys(allocations.countries).forEach(key => delete allocations.countries[key])
  Object.keys(allocations.industries).forEach(key => delete allocations.industries[key])
  
  currentCountryData.value = defaultData.countries
  currentIndustryData.value = defaultData.industries
  
  // Re-initialize with default
  Object.entries(defaultData.countries).forEach(([name, value]) => {
    allocations.countries[name] = value
  })
  Object.entries(defaultData.industries).forEach(([name, value]) => {
    allocations.industries[name] = value
  })
  
  portfolioResult.value = null
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="min-h-screen bg-black text-white">
    
    <!-- Hero Section - Simple 3-part layout -->
    <div class="h-screen flex flex-col relative">
      
      <!-- Top 1/3 - Centered Text -->
      <div class="flex-1 flex items-center justify-center px-6">
        <div class="text-center space-y-6 max-w-lg">
          <h1 class="text-4xl md:text-6xl font-light leading-tight">
            Build <span class="border-b-4 border-white">Your</span> ETF
          </h1>
          <p class="text-lg md:text-xl text-gray-300">
            Choose your allocation.
          </p>
        </div>
      </div>

      <!-- Middle 1/3 - Country Allocation Map (Becomes sticky on scroll) -->
      <div class="flex-1 px-6 flex items-center justify-center sticky top-0" style="z-index: 10;">
        <div class="w-full max-w-4xl h-full flex items-center">
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
        

        <!-- Industry Pie Chart -->
        <div class="space-y-4">
          <h3 class="text-xl font-medium">Industry Allocation</h3>
          <div class="rounded-lg border border-gray-800 overflow-hidden bg-black" style="height: 500px;">
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
                class="w-full bg-gray-900 border border-gray-700 rounded px-4 py-2 text-sm focus:outline-none focus:border-white"
              />
              <div 
                v-if="filteredCountries.length > 0"
                class="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded max-h-48 overflow-y-auto z-10"
              >
                <button
                  v-for="country in filteredCountries"
                  :key="country"
                  @click="addCountryFromSearch(country)"
                  class="w-full text-left px-4 py-2 hover:bg-gray-800 text-sm"
                >
                  {{ country }}
                </button>
              </div>
            </div>

            <!-- Top 5 Countries with Sliders -->
            <div class="space-y-4">
              <div 
                v-for="item in topCountries" 
                :key="item.name"
                class="space-y-2"
              >
                <div class="flex justify-between text-sm">
                  <span class="font-medium">{{ item.name }}</span>
                  <span class="text-gray-400">{{ item.allocated.toFixed(1) }}%</span>
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
                class="w-full bg-gray-900 border border-gray-700 rounded px-4 py-2 text-sm focus:outline-none focus:border-white"
              />
              <div 
                v-if="filteredIndustries.length > 0"
                class="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded max-h-48 overflow-y-auto z-10"
              >
                <button
                  v-for="industry in filteredIndustries"
                  :key="industry"
                  @click="addIndustryFromSearch(industry)"
                  class="w-full text-left px-4 py-2 hover:bg-gray-800 text-sm"
                >
                  {{ industry }}
                </button>
              </div>
            </div>

            <!-- Top 5 Industries with Sliders -->
            <div class="space-y-4">
              <div 
                v-for="item in topIndustries" 
                :key="item.name"
                class="space-y-2"
              >
                <div class="flex justify-between text-sm">
                  <span class="font-medium">{{ item.name }}</span>
                  <span class="text-gray-400">{{ item.allocated.toFixed(1) }}%</span>
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