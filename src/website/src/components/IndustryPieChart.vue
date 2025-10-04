<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  industryData: Record<string, number>
  labelsOpacity?: number
}

const props = withDefaults(defineProps<Props>(), {
  labelsOpacity: 1
})

const processedData = computed(() => {
  return Object.entries(props.industryData)
    .map(([industry, weight]) => ({ industry, weight }))
    .filter(d => d.weight > 0)
    .sort((a, b) => b.weight - a.weight)
})

// Top industries to display (8)
const topIndustries = computed(() => {
  return processedData.value.slice(0, 8)
})

// Calculate "Rest" percentage
const restPercentage = computed(() => {
  const topTotal = topIndustries.value.reduce((sum, item) => sum + item.weight, 0)
  const total = processedData.value.reduce((sum, item) => sum + item.weight, 0)
  return Math.max(0, total - topTotal)
})

// Data for bar chart (top 8 + rest)
const barChartData = computed(() => {
  const data = [...topIndustries.value]
  if (restPercentage.value > 0) {
    data.push({ industry: 'Rest', weight: restPercentage.value })
  }
  return data
})

// Data for legend (top 8 + rest if exists)
const legendData = computed(() => {
  const data = [...topIndustries.value]
  if (restPercentage.value > 0) {
    data.push({ industry: 'Rest', weight: restPercentage.value })
  }
  return data
})

const maxWeight = computed(() => {
  if (processedData.value.length === 0) return 100
  return Math.max(...processedData.value.map(item => item.weight))
})

function getOpacity(weight: number): number {
  const intensity = weight / maxWeight.value
  return Math.max(0.3 + intensity * 0.7, 0.3)
}
</script>

<template>
  <div class="w-full h-full flex flex-col items-center justify-center p-4 gap-6 ">
    <div class="w-full max-w-6xl space-y-3">
      <!-- Horizontal bar chart -->
      <div class="flex h-12 overflow-hidden relative border  rounded-lg">
        <div
          v-for="item in barChartData"
          :key="item.industry"
          :style="{ 
            width: `${item.weight}%`,
            backgroundColor: item.industry === 'Rest' ? 'transparent' : `rgba(255, 255, 255, ${getOpacity(item.weight)})`
          }"
          :class="item.industry === 'Rest' ? 'diagonal-stripes' : ''"
          class="relative group transition-all duration-200 hover:brightness-110 cursor-pointer"
        >
          <!-- Tooltip on hover -->
          <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-white text-black text-xs rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-20">
            <div class="font-semibold">{{ item.industry }}</div>
            <div class="text-gray-600">{{ item.weight.toFixed(1) }}%</div>
            <!-- Arrow pointing down -->
            <div class="absolute top-full left-1/2 transform -translate-x-1/2 -mt-px">
              <div class="border-4 border-transparent border-t-white"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Legend below - showing top industries + rest -->
      <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400 justify-center transition-opacity duration-300" :style="{ opacity: props.labelsOpacity }">
        <div
          v-for="item in legendData"
          :key="item.industry"
          class="flex items-center gap-1.5"
        >
          <div 
            v-if="item.industry === 'Rest'"
            class="w-3 h-3 rounded-sm diagonal-stripes-legend"
          ></div>
          <div 
            v-else
            class="w-3 h-3 rounded-sm"
            :style="{ backgroundColor: `rgba(255, 255, 255, ${getOpacity(item.weight)})` }"
          ></div>
          <span>{{ item.industry }} <span class="text-gray-500">({{ item.weight.toFixed(1) }}%)</span></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Diagonal stripes for "Rest" bar */
.diagonal-stripes {
  background-image: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.3),
    rgba(255, 255, 255, 0.3) 4px,
    rgba(255, 255, 255, 0.1) 4px,
    rgba(255, 255, 255, 0.1) 8px
  );
}

/* Diagonal stripes for legend square */
.diagonal-stripes-legend {
  background-image: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.5),
    rgba(255, 255, 255, 0.5) 2px,
    rgba(255, 255, 255, 0.2) 2px,
    rgba(255, 255, 255, 0.2) 4px
  );
}
</style>