<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getCountryColor } from '@/utils/hexMapData'
import { HEX_WORLD_MAP_SVG } from '@/utils/generatedHexMapFixed'

interface Props {
  countryData: Record<string, number>
}

const props = defineProps<Props>()
const svgRef = ref<SVGElement>()

onMounted(() => {
  if (svgRef.value) {
    // Load the precomputed SVG
    svgRef.value.innerHTML = HEX_WORLD_MAP_SVG.replace('<svg viewBox="0 0 800 550" xmlns="http://www.w3.org/2000/svg" class="hex-world-map">', '').replace('</svg>', '')
    updateColors()
  }
})

watch(() => props.countryData, () => {
  updateColors()
}, { deep: true })

function updateColors() {
  if (!svgRef.value) return
  
  const hexElements = svgRef.value.querySelectorAll('.hex')
  hexElements.forEach((hex) => {
    const countryName = hex.getAttribute('data-country')
    if (countryName) {
      const color = getCountryColor(countryName, props.countryData)
      hex.setAttribute('fill', color)
    }
  })
}
</script>

<template>
  <div class="relative w-full h-full flex items-center justify-center">
    <!-- SVG Container with rounded borders -->
    <div class="relative w-full h-full max-w-full max-h-full rounded-2xl overflow-hidden bg-black flex items-center justify-center">
      <svg 
        ref="svgRef" 
        viewBox="0 0 800 550"
        class="w-full h-full max-w-full max-h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <!-- Precomputed hex world map SVG will be loaded here -->
      </svg>
    </div>
  </div>
</template>

<style scoped>
svg {
  display: block;
}

:deep(.hex) {
  transition: fill 0.3s ease;
}
</style>