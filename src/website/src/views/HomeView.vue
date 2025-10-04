<script setup lang="ts">
import HexWorldMap from '@/components/HexWorldMapOptimized.vue'
import IndustryPieChart from '@/components/IndustryPieChart.vue'
import ETFAllocationTable from '@/components/ETFAllocationTable.vue'
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { optimizePortfolio, getDefaultMSCIWorldData, getDefaultETFAllocation, getAvailableCountries, getAvailableIndustries, getAvailableCategories } from '@/services/etfService'

// Category definitions with descriptions
const CATEGORY_INFO = {
  'Core Market': 'Broad market indices like S&P 500, MSCI World, and country/regional ETFs providing diversified global exposure',
  'Sectors': 'Industry-specific ETFs focused on sectors like Technology, Healthcare, Financials, Energy, and more',
  'Thematic': 'Innovation and trend-focused ETFs covering AI, Clean Energy, Electric Vehicles, Commodities, and emerging themes',
  'Strategy': 'Factor-based ETFs using systematic strategies like Dividend, Quality, Value, Momentum, and Equal Weight',
  'Stability': 'Fixed income ETFs including Government Bonds, Corporate Bonds, Treasuries, and other debt instruments',
  'Values': 'ESG and sustainable investing ETFs aligned with environmental, social, and governance principles'
}

// State
const allocations = reactive({
  countries: {} as Record<string, number>,
  industries: {} as Record<string, number>
})

const portfolioResult = ref(null as any)
const etfAllocations = ref(getDefaultETFAllocation())
const loading = ref(false)
const scrollY = ref(0)
const countrySearch = ref('')
const industrySearch = ref('')
const windowHeight = ref(0)
const heroSectionRef = ref<HTMLElement>()
const mapSectionRef = ref<HTMLElement>()

// Default MSCI World for initial display
const defaultData = getDefaultMSCIWorldData()
const currentCountryData = ref<Record<string, number>>(defaultData.countries)
const currentIndustryData = ref<Record<string, number>>(defaultData.industries)

const availableCountries = ref<string[]>([])
const availableIndustries = ref<string[]>([])
const availableCategories = ref<string[]>([])
const selectedCategories = ref<Set<string>>(new Set(['Core Market', 'Sectors', 'Thematic']))
const showCategoryInfo = ref<string | null>(null)
const maxETFs = ref(3)

// Close tooltip when clicking outside
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.category-pill-container')) {
    showCategoryInfo.value = null
  }
}

// Arrow opacity - fades when scrolling
const arrowOpacity = computed(() => {
  return Math.max(0, 1 - scrollY.value / 100)
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

// Labels opacity - fades in gradually as you scroll
const labelsOpacity = computed(() => {
  // Fade in over the first 500px of scrolling
  return Math.min(1, scrollY.value / 500)
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
    allocated: allocations.countries[name] !== undefined ? allocations.countries[name] : (currentCountryData.value[name] || 0)
  }))
})

const topIndustries = computed(() => {
  return selectedIndustries.value.map(name => ({
    name,
    current: currentIndustryData.value[name] || 0,
    allocated: allocations.industries[name] !== undefined ? allocations.industries[name] : (currentIndustryData.value[name] || 0)
  }))
})

// Check if more items can be added
const canAddMoreCountries = computed(() => selectedCountries.value.length < MAX_DISPLAYED_ITEMS)
const canAddMoreIndustries = computed(() => selectedIndustries.value.length < MAX_DISPLAYED_ITEMS)

// Top countries for map legend (sorted by percentage, top 3)
const topCountriesForLegend = computed(() => {
  return Object.entries(currentCountryData.value)
    .map(([name, weight]) => ({ name, weight }))
    .filter(d => d.weight > 0)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 3)
})

// Get opacity for country based on weight
function getCountryOpacity(weight: number): number {
  const maxWeight = Math.max(...Object.values(currentCountryData.value))
  const intensity = weight / maxWeight
  return Math.max(0.3 + intensity * 0.7, 0.3)
}

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
  scrollY.value = window.scrollY
}

function handleResize() {
  windowHeight.value = window.innerHeight
}

onMounted(async () => {
  window.addEventListener('scroll', handleScroll)
  window.addEventListener('resize', handleResize)
  window.addEventListener('click', handleClickOutside)
  windowHeight.value = window.innerHeight
  
  // Ensure page starts at the top on load/reload
  window.scrollTo(0, 0)
  scrollY.value = 0
  
  // Load available options
  try {
    const [countries, industries, categories] = await Promise.all([
      getAvailableCountries(),
      getAvailableIndustries(),
      getAvailableCategories()
    ])
    availableCountries.value = countries
    availableIndustries.value = industries
    availableCategories.value = categories
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
  window.removeEventListener('click', handleClickOutside)
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
    
    // Convert selected categories Set to Array
    const categoryFilters = Array.from(selectedCategories.value)
    
    const result = await optimizePortfolio(
      selectedCountryAllocations, 
      selectedIndustryAllocations,
      categoryFilters.length > 0 ? categoryFilters : undefined
    )
    portfolioResult.value = result
    
    // Update current data with achieved allocations
    currentCountryData.value = result.achieved_countries
    currentIndustryData.value = result.achieved_industries
    
    // Update ETF allocations (limited to maxETFs)
    etfAllocations.value = result.etf_allocations.slice(0, maxETFs.value)
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
  
  // Reset categories to default
  selectedCategories.value = new Set(['Core Market', 'Sectors', 'Thematic'])
  
  portfolioResult.value = null
  etfAllocations.value = getDefaultETFAllocation()
  
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function toggleCategory(category: string) {
  if (selectedCategories.value.has(category)) {
    selectedCategories.value.delete(category)
  } else {
    selectedCategories.value.add(category)
  }
  // Force reactivity
  selectedCategories.value = new Set(selectedCategories.value)
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
    <div ref="heroSectionRef" class="h-screen flex flex-col relative">
      
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
      <div ref="mapSectionRef" class="flex-1 px-6 flex flex-col items-center justify-center sticky top-1/3 md:top-1/4 gap-3">
        <div class="w-full max-w-6xl flex-1 flex items-center justify-center">
          <div class="w-full h-full max-h-[500px] flex items-center justify-center">
            <HexWorldMap :countryData="currentCountryData" class="w-full h-full" />
          </div>
        </div>
        
        <!-- Legend below map -->
        <div class="w-full max-w-6xl transition-opacity duration-300" :style="{ opacity: labelsOpacity }">
          <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400 justify-center">
            <div
              v-for="country in topCountriesForLegend"
              :key="country.name"
              class="flex items-center gap-1.5"
            >
              <div 
                class="w-3 h-3 rounded-sm"
                :style="{ backgroundColor: `rgba(255, 255, 255, ${getCountryOpacity(country.weight)})` }"
              ></div>
              <span>{{ country.name }} <span class="text-gray-500">({{ country.weight.toFixed(1) }}%)</span></span>
            </div>
          </div>
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
      <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- Industry Bar Chart -->
        <div class="space-y-4">
          <div class="bg-black" style="height: 120px;">
            <IndustryPieChart :industryData="currentIndustryData" :labelsOpacity="labelsOpacity" />
          </div>
        </div>

        <!-- ETF Allocation Table -->
        <div class="space-y-4">
          <h3 class="text-xl font-light">ETF Allocation</h3>
          <ETFAllocationTable :allocations="etfAllocations" />
        </div>
      </div>
    </div>

    <!-- Controls Section -->
    <div class="relative bg-black border-t border-gray-800  px-4 pt-8">
      <div class="max-w-6xl mx-auto">
        
        <!-- Header -->
        <div class="mb-8 flex justify-between items-center">
          <h2 class="text-2xl font-light">Customize Your Portfolio</h2>
          <button 
            @click="resetToMSCI"
            class="text-xs border border-gray-600 px-4 py-2 hover:bg-white hover:text-black transition-colors rounded-lg"
          >
            Reset
          </button>
        </div>

        <!-- Category Pills -->
        <div class="mb-8">
          <div class="flex justify-between items-start mb-3">
            <h3 class="text-sm font-medium text-gray-400">ETF Categories</h3>
            <div class="flex items-center gap-2 text-xs">
              <label class="text-gray-500">Show top</label>
              <select
                v-model.number="maxETFs"
                class="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white focus:outline-none focus:border-white cursor-pointer hover:border-gray-500 transition-colors"
              >
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="5">5</option>
                <option :value="10">10</option>
                <option :value="15">15</option>
                <option :value="20">20</option>
              </select>
              <label class="text-gray-500">ETFs</label>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <div 
              v-for="category in availableCategories" 
              :key="category"
              class="relative group category-pill-container"
            >
              <button
                @click="toggleCategory(category)"
                :class="[
                  'px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 flex items-center gap-2',
                  selectedCategories.has(category)
                    ? 'bg-white text-black'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
                ]"
              >
                <span>{{ category }}</span>
                <button
                  @click.stop="showCategoryInfo = showCategoryInfo === category ? null : category"
                  :class="[
                    'w-4 h-4 rounded-full flex items-center justify-center text-xs transition-colors',
                    selectedCategories.has(category)
                      ? 'bg-black text-white'
                      : 'bg-gray-700 text-gray-400 group-hover:bg-gray-600'
                  ]"
                  title="Info"
                >
                  i
                </button>
              </button>
              
              <!-- Info tooltip -->
              <div
                v-if="showCategoryInfo === category"
                class="absolute z-20 top-full mt-2 left-0 w-72 bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs text-gray-300 shadow-xl"
              >
                <button
                  @click.stop="showCategoryInfo = null"
                  class="absolute top-2 right-2 text-gray-500 hover:text-white"
                >
                  ✕
                </button>
                <div class="pr-6">
                  {{ CATEGORY_INFO[category as keyof typeof CATEGORY_INFO] }}
                </div>
              </div>
            </div>
          </div>
          <div class="text-xs text-gray-500 mt-2">
            {{ selectedCategories.size }} {{ selectedCategories.size === 1 ? 'category' : 'categories' }} selected
          </div>
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
            class="w-full bg-white text-black py-4 text-lg font-medium hover:bg-gray-200 transition-colors disabled:bg-gray-700 disabled:text-gray-400 rounded-lg"
          >
            {{ loading ? 'Customizing...' : 'Customize Portfolio' }}
          </button>
        </div>
      </div>
    </div>
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