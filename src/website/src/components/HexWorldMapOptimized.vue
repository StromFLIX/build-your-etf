<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getCountryColor } from '@/utils/hexMapData'
import { HEX_WORLD_MAP_SVG } from '@/utils/generatedHexMapFixed'

interface Props {
  countryData: Record<string, number>
  highlightStage?: number | null
}

const props = defineProps<Props>()
const svgRef = ref<SVGElement>()

// Countries to highlight in each stage
const STAGE_HIGHLIGHTS = {
  0: ['United States of America'], // Stage 1: US bias
  1: ['Germany', 'France', 'United Kingdom', 'Japan', 'China', 'India', 'Brazil', 'Australia', 'Canada', 'South Korea', 'Italy', 'Spain'], // Stage 2: Global diversity
}

onMounted(() => {
  if (svgRef.value) {
    // Load the precomputed SVG
    svgRef.value.innerHTML = HEX_WORLD_MAP_SVG.replace('<svg viewBox="0 0 800 550" xmlns="http://www.w3.org/2000/svg" class="hex-world-map">', '').replace('</svg>', '')
    updateColors()
    updateHighlights()
  }
})

watch(() => props.countryData, () => {
  updateColors()
}, { deep: true })

watch(() => props.highlightStage, () => {
  updateHighlights()
})

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

function updateHighlights() {
  if (!svgRef.value) return
  
  const hexElements = svgRef.value.querySelectorAll('.hex')
  
  // Remove all existing highlight classes
  hexElements.forEach((hex) => {
    hex.classList.remove('highlight-pulse', 'highlight-pulse-delayed')
    hex.removeAttribute('style')
  })
  
  // Apply highlights based on stage
  if (props.highlightStage === 0 || props.highlightStage === 1) {
    const highlightCountries = STAGE_HIGHLIGHTS[props.highlightStage as 0 | 1]
    
    // Batch DOM updates
    const fragment = document.createDocumentFragment()
    
    hexElements.forEach((hex) => {
      const countryName = hex.getAttribute('data-country')
      if (countryName && highlightCountries.includes(countryName)) {
        // For stage 1, add staggered delays to different countries
        if (props.highlightStage === 1) {
          const index = highlightCountries.indexOf(countryName)
          hex.classList.add('highlight-pulse-delayed')
          // Use CSS variable for delay instead of inline style
          ;(hex as HTMLElement).style.setProperty('--anim-delay', `${index * 0.2}s`)
        } else {
          hex.classList.add('highlight-pulse')
        }
      }
    })
  }
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
  /* Use will-change sparingly for performance */
}

/* Pulsing highlight for Stage 1 (US) - More performant version */
:deep(.hex.highlight-pulse) {
  fill: rgba(59, 130, 246, 0.9) !important;
  opacity: 1;
  animation: pulse-simple 2s ease-in-out infinite;
  transform-origin: center;
}

/* Pulsing highlight for Stage 2 (Multiple countries with delays) */
:deep(.hex.highlight-pulse-delayed) {
  fill: rgba(34, 197, 94, 0.8) !important;
  opacity: 1;
  animation: pulse-simple 2s ease-in-out infinite;
  animation-delay: var(--anim-delay, 0s);
  transform-origin: center;
}

/* Simpler animation that uses only opacity - much more performant */
@keyframes pulse-simple {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}
</style>