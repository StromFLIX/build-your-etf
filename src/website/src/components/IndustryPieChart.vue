<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import * as d3 from 'd3'

interface Props {
  industryData: Record<string, number>
}

const props = defineProps<Props>()
const svgRef = ref<SVGElement>()
const containerRef = ref<HTMLElement>()

const processedData = computed(() => {
  return Object.entries(props.industryData)
    .map(([industry, weight]) => ({ industry, weight }))
    .filter(d => d.weight > 0)
    .sort((a, b) => b.weight - a.weight)
})

onMounted(() => {
  render()
})

watch(() => props.industryData, () => {
  render()
}, { deep: true })

function render() {
  if (!svgRef.value || !containerRef.value) return
  
  const svg = d3.select(svgRef.value)
  svg.selectAll("*").remove()
  
  const containerRect = containerRef.value.getBoundingClientRect()
  const size = Math.min(containerRect.width, containerRect.height) - 40
  const radius = size / 2
  const centerX = containerRect.width / 2
  const centerY = containerRect.height / 2
  
  svg.attr("width", containerRect.width)
     .attr("height", containerRect.height)
  
  const g = svg.append("g")
    .attr("transform", `translate(${centerX}, ${centerY})`)
  
  // Create pie layout
  const pie = d3.pie<any>()
    .value(d => d.weight)
    .sort(null)
  
  const arc = d3.arc<any>()
    .innerRadius(radius * 0.3)
    .outerRadius(radius * 0.9)
  
  const data = processedData.value
  if (data.length === 0) return
  
  // Create arcs
  const arcs = g.selectAll(".arc")
    .data(pie(data))
    .enter()
    .append("g")
    .attr("class", "arc")
  
  // Add slices
  arcs.append("path")
    .attr("d", arc)
    .attr("fill", (d, i) => {
      // Use different shades of white/gray based on allocation
      const maxWeight = Math.max(...data.map(item => item.weight))
      const intensity = d.data.weight / maxWeight
      const opacity = Math.max(0.3 + intensity * 0.7, 0.3)
      return `rgba(255, 255, 255, ${opacity})`
    })
    .attr("stroke", "#000")
    .attr("stroke-width", "1")
  
  // Add labels for significant slices (>= 5%)
  arcs.filter(d => d.data.weight >= 5)
    .append("text")
    .attr("transform", d => `translate(${arc.centroid(d)})`)
    .attr("text-anchor", "middle")
    .attr("font-size", "12px")
    .attr("fill", "#000")
    .attr("font-weight", "500")
    .text(d => `${d.data.weight.toFixed(1)}%`)
  
  // Add legend
  const legend = svg.append("g")
    .attr("class", "legend")
    .attr("transform", `translate(20, 20)`)
  
  const legendItems = legend.selectAll(".legend-item")
    .data(data.slice(0, 8)) // Top 8 industries
    .enter()
    .append("g")
    .attr("class", "legend-item")
    .attr("transform", (d, i) => `translate(0, ${i * 20})`)
  
  legendItems.append("rect")
    .attr("width", 12)
    .attr("height", 12)
    .attr("fill", (d, i) => {
      const maxWeight = Math.max(...data.map(item => item.weight))
      const intensity = d.weight / maxWeight
      const opacity = Math.max(0.3 + intensity * 0.7, 0.3)
      return `rgba(255, 255, 255, ${opacity})`
    })
    .attr("stroke", "#fff")
    .attr("stroke-width", "1")
  
  legendItems.append("text")
    .attr("x", 18)
    .attr("y", 9)
    .attr("font-size", "12px")
    .attr("fill", "#fff")
    .text(d => `${d.industry} (${d.weight.toFixed(1)}%)`)
}
</script>

<template>
  <div ref="containerRef" class="w-full h-full">
    <svg ref="svgRef" class="w-full h-full"></svg>
  </div>
</template>

<style scoped>
</style>