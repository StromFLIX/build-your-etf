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
    svgRef.value.innerHTML = HEX_WORLD_MAP_SVG.replace('<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg" class="hex-world-map">', '').replace('</svg>', '')
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
    <!-- SVG Container with rounded borders and fade effect -->
    <div class="relative w-full h-full max-w-full max-h-full rounded-2xl overflow-hidden bg-black flex items-center justify-center">
      <svg 
        ref="svgRef" 
        viewBox="0 0 800 600"
        class="w-full h-full max-w-full max-h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <!-- Precomputed hex world map SVG will be loaded here -->
      </svg>
      
      <!-- Subtle fade-out gradient overlay -->
      <div class="absolute inset-0 pointer-events-none">
        <!-- Gentle radial fade to focus on center content -->
        <div class="absolute inset-0 hex-map-fade"></div>
      </div>
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

/* Elegant radial fade effect */
.hex-map-fade {
  background: radial-gradient(
    ellipse 80% 60% at center, 
    transparent 30%, 
    rgba(0,0,0,0.1) 60%, 
    rgba(0,0,0,0.4) 80%, 
    rgba(0,0,0,0.8) 95%, 
    black 100%
  );
}
</style>