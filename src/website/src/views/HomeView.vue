<script setup lang="ts">
import HexWorldMap from '@/components/HexWorldMapOptimized.vue'
import IndustryPieChart from '@/components/IndustryPieChart.vue'
import AllocationControls from '@/components/AllocationControls.vue'
import PortfolioOutput from '@/components/PortfolioOutput.vue'
import { ref, reactive, watch, computed } from 'vue'
import { optimizePortfolio, getDefaultMSCIWorldData } from '@/services/etfService'

// State
const allocations = reactive({
  countries: {} as Record<string, number>,
  industries: {} as Record<string, number>
})

const portfolioResult = ref(null as any)
const loading = ref(false)
const showBuilder = ref(false)

// Default MSCI World for initial display
const defaultData = getDefaultMSCIWorldData()
// Default data with flexible types
const currentCountryData = ref<Record<string, number>>(defaultData.countries)
const currentIndustryData = ref<Record<string, number>>(defaultData.industries)

// Computed values
const unallocatedCountries = computed(() => {
  const allocated = Object.values(allocations.countries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

const unallocatedIndustries = computed(() => {
  const allocated = Object.values(allocations.industries).reduce((sum, val) => sum + val, 0)
  return Math.max(0, 100 - allocated)
})

// Watch for allocation changes and optimize
watch([() => ({ ...allocations.countries }), () => ({ ...allocations.industries })], 
  async () => {
    if (Object.keys(allocations.countries).length > 0 || Object.keys(allocations.industries).length > 0) {
      await optimizeAndUpdate()
    }
  },
  { deep: true }
)

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

function startBuilding() {
  showBuilder.value = true
}

function resetToMSCI() {
  Object.keys(allocations.countries).forEach(key => delete allocations.countries[key])
  Object.keys(allocations.industries).forEach(key => delete allocations.industries[key])
  
  currentCountryData.value = defaultData.countries
  currentIndustryData.value = defaultData.industries
  portfolioResult.value = null
  showBuilder.value = false
}
</script>

<template>
  <div class="min-h-screen bg-black text-white">
    <!-- Hero Section -->
    <div class="relative">
      <div class="flex min-h-screen">
        <!-- Left Side - Text -->
        <div class="w-1/2 flex flex-col justify-center px-16">
          <div class="space-y-8">
            <div class="space-y-4">
              <h1 class="text-6xl font-light leading-tight">
                Build <span class="border-b-4 border-white">Your</span> ETF
              </h1>
              <p class="text-xl text-gray-300 max-w-lg leading-relaxed">
                Because you should be allowed to choose and find exactly what you need.
              </p>
            </div>
            
            <div class="space-y-4">
              <p class="text-gray-400">
                Start with the MSCI World index, then customize your allocation across countries and industries 
                to create the perfect ETF portfolio for your needs.
              </p>
              
              <button 
                @click="startBuilding"
                class="bg-white text-black px-8 py-4 hover:bg-gray-200 transition-colors font-medium"
              >
                Start Building
              </button>
              
              <button 
                v-if="showBuilder"
                @click="resetToMSCI"
                class="ml-4 border border-white px-8 py-4 hover:bg-white hover:text-black transition-colors"
              >
                Reset to MSCI World
              </button>
            </div>
          </div>
        </div>

        <!-- Right Side - Hex Map -->
        <div class="w-1/2 relative p-8">
          <div class="w-full h-full rounded-2xl overflow-hidden shadow-2xl">
            <HexWorldMap :countryData="currentCountryData" class="w-full h-full" />
          </div>
        </div>
      </div>
    </div>

    <!-- Builder Section -->
    <div v-if="showBuilder" class="border-t border-gray-800">
      <!-- Display Section -->
      <section class="py-16 px-16">
        <div class="mb-12">
          <h2 class="text-3xl font-light mb-4">Current Distribution</h2>
          <div class="grid grid-cols-2 gap-16">
            <!-- World Map -->
            <div class="space-y-4">
              <h3 class="text-xl font-medium">Geographic Allocation</h3>
              <div class="rounded-xl overflow-hidden border border-gray-800 h-96">
                <HexWorldMap :countryData="currentCountryData" class="w-full h-full" />
              </div>
            </div>

            <!-- Industry Chart -->
            <div class="space-y-4">
              <h3 class="text-xl font-medium">Industry Allocation</h3>
              <div class="rounded-xl border border-gray-800 h-96 flex items-center justify-center bg-black">
                <IndustryPieChart :industryData="currentIndustryData" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Controls Section -->
      <section class="py-16 px-16 border-t border-gray-800">
        <div class="mb-12">
          <h2 class="text-3xl font-light mb-4">Allocation Controls</h2>
          <AllocationControls 
            v-model:countries="allocations.countries"
            v-model:industries="allocations.industries"
            :unallocatedCountries="unallocatedCountries"
            :unallocatedIndustries="unallocatedIndustries"
            :loading="loading"
          />
        </div>
      </section>

      <!-- Portfolio Output Section -->
      <section v-if="portfolioResult" class="py-16 px-16 border-t border-gray-800">
        <div class="mb-12">
          <h2 class="text-3xl font-light mb-4">Your ETF Portfolio</h2>
          <PortfolioOutput :result="portfolioResult" />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
</style>