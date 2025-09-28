<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAvailableCountries, getAvailableIndustries } from '@/services/etfService'

interface Props {
  countries: Record<string, number>
  industries: Record<string, number>
  unallocatedCountries: number
  unallocatedIndustries: number
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:countries': [value: Record<string, number>]
  'update:industries': [value: Record<string, number>]
}>()

const availableCountries = ref<string[]>([])
const availableIndustries = ref<string[]>([])
const loadingData = ref(true)

// Common countries and industries for quick access
const popularCountries = [
  'United States', 'Japan', 'United Kingdom', 'France', 'Canada', 
  'Switzerland', 'Germany', 'Australia', 'South Korea', 'Taiwan'
]

const popularIndustries = [
  'Information Technology', 'Financials', 'Healthcare', 'Consumer Discretionary',
  'Communication Services', 'Industrials', 'Consumer Staples', 'Energy',
  'Materials', 'Real Estate', 'Utilities'
]

onMounted(async () => {
  try {
    const [countries, industries] = await Promise.all([
      getAvailableCountries(),
      getAvailableIndustries()
    ])
    availableCountries.value = countries
    availableIndustries.value = industries
  } catch (error) {
    console.error('Failed to load available options:', error)
  } finally {
    loadingData.value = false
  }
})

function updateCountryAllocation(country: string, value: string) {
  const numValue = parseFloat(value)
  const newCountries = { ...props.countries }
  
  if (isNaN(numValue) || numValue <= 0) {
    delete newCountries[country]
  } else {
    newCountries[country] = Math.min(numValue, 100)
  }
  
  emit('update:countries', newCountries)
}

function updateIndustryAllocation(industry: string, value: string) {
  const numValue = parseFloat(value)
  const newIndustries = { ...props.industries }
  
  if (isNaN(numValue) || numValue <= 0) {
    delete newIndustries[industry]
  } else {
    newIndustries[industry] = Math.min(numValue, 100)
  }
  
  emit('update:industries', newIndustries)
}

function removeCountryAllocation(country: string) {
  const newCountries = { ...props.countries }
  delete newCountries[country]
  emit('update:countries', newCountries)
}

function removeIndustryAllocation(industry: string) {
  const newIndustries = { ...props.industries }
  delete newIndustries[industry]
  emit('update:industries', newIndustries)
}

function addCountry(country: string) {
  if (!props.countries[country]) {
    updateCountryAllocation(country, '10')
  }
}

function addIndustry(industry: string) {
  if (!props.industries[industry]) {
    updateIndustryAllocation(industry, '10')
  }
}

const isOverAllocated = computed(() => {
  return props.unallocatedCountries < 0 || props.unallocatedIndustries < 0
})
</script>

<template>
  <div class="space-y-12">
    <!-- Status indicators -->
    <div class="grid grid-cols-2 gap-8">
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-lg">Country Allocation</span>
          <span class="text-sm" :class="{ 
            'text-red-400': unallocatedCountries < 0,
            'text-yellow-400': unallocatedCountries > 0,
            'text-green-400': unallocatedCountries === 0
          }">
            {{ unallocatedCountries < 0 ? 'Over-allocated' : 
               unallocatedCountries > 0 ? `${unallocatedCountries.toFixed(1)}% remaining` : 
               'Fully allocated' }}
          </span>
        </div>
        <div class="w-full bg-gray-800 h-2">
          <div 
            class="h-2 transition-all duration-300" 
            :class="{ 
              'bg-red-500': unallocatedCountries < 0,
              'bg-white': unallocatedCountries >= 0
            }"
            :style="{ width: `${Math.min(100 - unallocatedCountries, 100)}%` }"
          ></div>
        </div>
      </div>
      
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-lg">Industry Allocation</span>
          <span class="text-sm" :class="{ 
            'text-red-400': unallocatedIndustries < 0,
            'text-yellow-400': unallocatedIndustries > 0,
            'text-green-400': unallocatedIndustries === 0
          }">
            {{ unallocatedIndustries < 0 ? 'Over-allocated' : 
               unallocatedIndustries > 0 ? `${unallocatedIndustries.toFixed(1)}% remaining` : 
               'Fully allocated' }}
          </span>
        </div>
        <div class="w-full bg-gray-800 h-2">
          <div 
            class="h-2 transition-all duration-300" 
            :class="{ 
              'bg-red-500': unallocatedIndustries < 0,
              'bg-white': unallocatedIndustries >= 0
            }"
            :style="{ width: `${Math.min(100 - unallocatedIndustries, 100)}%` }"
          ></div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-16">
      <!-- Country Controls -->
      <div class="space-y-6">
        <h3 class="text-xl font-medium">Country Allocation</h3>
        
        <!-- Current allocations -->
        <div class="space-y-3">
          <div 
            v-for="[country, allocation] in Object.entries(countries)" 
            :key="country"
            class="flex items-center gap-4 p-4 border border-gray-800"
          >
            <span class="flex-1">{{ country }}</span>
            <input
              type="number"
              :value="allocation"
              @input="updateCountryAllocation(country, ($event.target as HTMLInputElement).value)"
              class="w-20 bg-black border border-gray-600 px-2 py-1 text-center"
              min="0"
              max="100"
              step="0.1"
            />
            <span class="text-gray-400">%</span>
            <button
              @click="removeCountryAllocation(country)"
              class="w-8 h-8 border border-gray-600 hover:bg-red-600 hover:border-red-500 transition-colors flex items-center justify-center"
            >
              ×
            </button>
          </div>
        </div>
        
        <!-- Add new country -->
        <div class="space-y-4">
          <h4 class="text-lg">Popular Countries</h4>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="country in popularCountries"
              :key="country"
              @click="addCountry(country)"
              :disabled="!!countries[country]"
              class="p-2 text-sm border border-gray-600 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {{ country }}
            </button>
          </div>
        </div>
      </div>

      <!-- Industry Controls -->
      <div class="space-y-6">
        <h3 class="text-xl font-medium">Industry Allocation</h3>
        
        <!-- Current allocations -->
        <div class="space-y-3">
          <div 
            v-for="[industry, allocation] in Object.entries(industries)" 
            :key="industry"
            class="flex items-center gap-4 p-4 border border-gray-800"
          >
            <span class="flex-1">{{ industry }}</span>
            <input
              type="number"
              :value="allocation"
              @input="updateIndustryAllocation(industry, ($event.target as HTMLInputElement).value)"
              class="w-20 bg-black border border-gray-600 px-2 py-1 text-center"
              min="0"
              max="100"
              step="0.1"
            />
            <span class="text-gray-400">%</span>
            <button
              @click="removeIndustryAllocation(industry)"
              class="w-8 h-8 border border-gray-600 hover:bg-red-600 hover:border-red-500 transition-colors flex items-center justify-center"
            >
              ×
            </button>
          </div>
        </div>
        
        <!-- Add new industry -->
        <div class="space-y-4">
          <h4 class="text-lg">Popular Industries</h4>
          <div class="grid grid-cols-1 gap-2">
            <button
              v-for="industry in popularIndustries"
              :key="industry"
              @click="addIndustry(industry)"
              :disabled="!!industries[industry]"
              class="p-2 text-sm border border-gray-600 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-left"
            >
              {{ industry }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
      <p class="mt-2 text-gray-400">Optimizing your portfolio...</p>
    </div>

    <!-- Warning for over-allocation -->
    <div v-if="isOverAllocated" class="p-4 border border-red-500 bg-red-900/20">
      <h4 class="text-red-400 font-medium">Over-allocation Warning</h4>
      <p class="text-red-300 text-sm mt-1">
        Your allocations exceed 100%. Please adjust the values to continue.
      </p>
    </div>
  </div>
</template>

<style scoped>
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}
</style>