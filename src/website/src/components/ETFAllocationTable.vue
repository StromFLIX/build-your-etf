<script setup lang="ts">
import { computed } from 'vue'

interface ETFAllocation {
  etf_id: string | number
  name: string
  ticker: string
  weight: number
  ter: number
}

interface Props {
  allocations: ETFAllocation[]
}

const props = defineProps<Props>()

// Sort by weight descending and take top 3
const topAllocations = computed(() => {
  return [...props.allocations]
    .sort((a, b) => b.weight - a.weight)
})
</script>

<template>
  <div class="w-full">
    <div class="space-y-2">
      <div 
        v-for="etf in topAllocations" 
        :key="etf.etf_id"
        class="flex items-center justify-between px-4 py-3 border border-gray-800 hover:border-gray-700 transition-colors"
      >
        <div class="flex-1 mr-4">
          <div class="text-sm font-medium">{{ etf.ticker }}</div>
          <div class="text-xs text-gray-500">{{ etf.name }}</div>
        </div>
        
        <div class="text-right">
          <div class="text-lg font-light">{{ (etf.weight * 100).toFixed(1) }}%</div>
        </div>
      </div>
    </div>
  </div>
</template>
