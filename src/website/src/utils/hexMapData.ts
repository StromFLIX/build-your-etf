// Pre-generated hex world map SVG - this avoids expensive computation on every render
export const HEX_WORLD_MAP_SVG = `<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <!-- This is a placeholder - will be replaced with actual generated SVG -->
  <rect width="800" height="600" fill="#000000"/>
  <text x="400" y="300" text-anchor="middle" fill="white" font-size="24">Hex World Map Loading...</text>
</svg>`

// Country name mappings for consistency
export const COUNTRY_NAME_MAPPINGS: Record<string, string> = {
  'United States of America': 'United States',
  'United Kingdom': 'United Kingdom', 
  'South Korea': 'South Korea',
  'Taiwan': 'Taiwan',
  'Russian Federation': 'Russia',
  'China': 'China'
}

export function getCountryColor(countryName: string, countryData: Record<string, number>): string {
  if (!countryName) return '#1f2937' // gray-800
  
  // Map some common country name variations
  const mappedName = COUNTRY_NAME_MAPPINGS[countryName] || countryName
  const allocation = countryData[mappedName]
  
  if (!allocation || allocation === 0) {
    return '#1f2937' // gray-800 for unallocated
  }
  
  // Calculate intensity based on allocation percentage
  const maxAllocation = Math.max(...Object.values(countryData))
  const intensity = Math.min(allocation / maxAllocation, 1)
  
  // Use a white color with opacity based on intensity
  const opacity = Math.max(0.2 + intensity * 0.8, 0.2)
  return `rgba(255, 255, 255, ${opacity})`
}