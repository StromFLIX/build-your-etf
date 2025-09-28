<script setup lang="ts">
import { computed } from 'vue'
import type { OptimizationResult } from '@/services/etfService'

interface Props {
  result: OptimizationResult
}

const props = defineProps<Props>()

const totalWeight = computed(() => {
  return props.result.etf_allocations.reduce((sum, etf) => sum + etf.weight, 0)
})

const optimizationGrade = computed(() => {
  const score = props.result.optimization_score
  if (score >= 0.9) return { grade: 'A', color: 'text-green-400' }
  if (score >= 0.8) return { grade: 'B', color: 'text-yellow-400' }
  if (score >= 0.7) return { grade: 'C', color: 'text-orange-400' }
  return { grade: 'D', color: 'text-red-400' }
})

function exportToCSV() {
  const csvContent = [
    ['ETF Name', 'Ticker', 'Weight (%)', 'TER (%)'].join(','),
    ...props.result.etf_allocations.map(etf => [
      `"${etf.name}"`,
      etf.ticker,
      (etf.weight * 100).toFixed(2),
      (etf.ter * 100).toFixed(4)
    ].join(','))
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'etf-portfolio.csv'
  a.click()
  window.URL.revokeObjectURL(url)
}

function copyToClipboard() {
  const text = props.result.etf_allocations
    .map(etf => `${etf.ticker}: ${(etf.weight * 100).toFixed(1)}%`)
    .join('\n')
  
  navigator.clipboard.writeText(text).then(() => {
    // Could add a toast notification here
    console.log('Copied to clipboard')
  })
}
</script>

<template>
  <div class="space-y-8">
    <!-- Summary -->
    <div class="grid grid-cols-3 gap-8 mb-8">
      <div class="text-center">
        <div class="text-3xl font-light">{{ result.etf_allocations.length }}</div>
        <div class="text-gray-400">ETFs Selected</div>
      </div>
      <div class="text-center">
        <div class="text-3xl font-light">{{ (result.total_ter * 100).toFixed(2) }}%</div>
        <div class="text-gray-400">Total TER</div>
      </div>
      <div class="text-center">
        <div class="text-3xl font-light" :class="optimizationGrade.color">
          {{ optimizationGrade.grade }}
        </div>
        <div class="text-gray-400">Optimization Grade</div>
      </div>
    </div>

    <!-- ETF Allocations -->
    <div class="space-y-4">
      <h3 class="text-xl font-medium">ETF Composition</h3>
      
      <div class="space-y-2">
        <div 
          v-for="etf in result.etf_allocations" 
          :key="etf.etf_id"
          class="flex items-center justify-between p-4 border border-gray-800"
        >
          <div class="flex-1">
            <div class="font-medium">{{ etf.name }}</div>
            <div class="text-sm text-gray-400">{{ etf.ticker }} • TER: {{ (etf.ter * 100).toFixed(2) }}%</div>
          </div>
          
          <div class="text-right">
            <div class="text-lg">{{ (etf.weight * 100).toFixed(1) }}%</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Achievement Analysis -->
    <div class="grid grid-cols-2 gap-16">
      <!-- Country Achievement -->
      <div class="space-y-4">
        <h3 class="text-xl font-medium">Country Allocation Achievement</h3>
        <div class="space-y-2">
          <div 
            v-for="[country, percentage] in Object.entries(result.achieved_countries)" 
            :key="country"
            class="flex justify-between p-2 border border-gray-800"
          >
            <span>{{ country }}</span>
            <span>{{ percentage.toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <!-- Industry Achievement -->
      <div class="space-y-4">
        <h3 class="text-xl font-medium">Industry Allocation Achievement</h3>
        <div class="space-y-2">
          <div 
            v-for="[industry, percentage] in Object.entries(result.achieved_industries)" 
            :key="industry"
            class="flex justify-between p-2 border border-gray-800"
          >
            <span>{{ industry }}</span>
            <span>{{ percentage.toFixed(1) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Export/Actions -->
    <div class="pt-8 border-t border-gray-800">
      <div class="flex gap-4">
        <button 
          @click="exportToCSV"
          class="px-6 py-3 border border-white hover:bg-white hover:text-black transition-colors"
        >
          Export to CSV
        </button>
        
        <button 
          @click="copyToClipboard"
          class="px-6 py-3 border border-gray-600 hover:border-white transition-colors"
        >
          Copy Allocation
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>