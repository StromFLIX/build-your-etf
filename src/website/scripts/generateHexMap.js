import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { geoNaturalEarth1, geoPath, geoContains, geoMercator } from 'd3-geo'
import { writeFileSync } from 'fs'
import fetch from 'node-fetch'

// Configuration
const HEX_RADIUS = 2
const WIDTH = 600
const HEIGHT = 600

// Only filter out the most extreme polar regions
const MIN_LATITUDE = -90  // Less aggressive - only remove far Antarctica
const MAX_LATITUDE = 90   // Less aggressive - allow more northern regions

// Countries to exclude (only Antarctica)
const EXCLUDED_COUNTRIES = ['Antarctica']

async function generateFixedHexWorldMapSVG() {
  console.log('Loading world topology data...')
  
  const world = await fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
    .then(r => r.json())
  
  const land = topojson.feature(world, world.objects.land)
  const allCountriesFeature = topojson.feature(world, world.objects.countries)
  const countries = allCountriesFeature.features.filter(f => {
    const name = f.properties?.name
    return name && !EXCLUDED_COUNTRIES.includes(name)
  })

  console.log(`Loaded ${countries.length} countries (excluded only Antarctica)`)

  const projection = geoMercator()
  projection.fitSize([WIDTH, HEIGHT], land)
  const geoPathFunc = geoPath(projection)

  console.log('Generating hex grid...')
  const hexData = generateHexGrid(projection, land, countries)
  console.log(`Generated ${hexData.length} hex points`)
  
  let svgContent = `<svg viewBox="0 0 ${WIDTH} ${HEIGHT}" xmlns="http://www.w3.org/2000/svg" class="hex-world-map">
  <defs>
    <style>
      .hex { transition: fill 0.3s ease; }
    </style>
  </defs>
  <rect width="${WIDTH}" height="${HEIGHT}" fill="#000000"/>
`
  
  const seenRegions = new Map()
  
  hexData.forEach((hex) => {
    const countryName = hex.country?.properties?.name || 'Unknown'
    
    const pathD = hexPath(hex.x, hex.y, hex.r)
    svgContent += `  <path d="${pathD}" class="hex" data-country="${countryName}" stroke="rgba(255,255,255,0.06)" stroke-width="0.4" fill="#1f2937" />
`
  })
  
  if (countries.length > 0) {
    const fakeTopology = {
      objects: {
        countries: {
          type: "GeometryCollection",
          geometries: countries.map(c => ({ ...c, properties: c.properties }))
        }
      }
    }
    
    const mesh = topojson.mesh(fakeTopology, fakeTopology.objects.countries, (a, b) => a !== b)
    const borderPath = geoPathFunc(mesh)
    if (borderPath) {
      svgContent += `  <path d="${borderPath}" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="0.5" pointer-events="none" class="borders"/>
`
    }
  }
  
  svgContent += '</svg>'
  return svgContent
}

function generateHexGrid(projection, land, countries) {
  const r = HEX_RADIUS
  const SQRT3 = Math.sqrt(3)
  const w = SQRT3 * r
  const v = 1.5 * r
  const cols = Math.ceil(WIDTH / w) + 2
  const rows = Math.ceil(HEIGHT / v) + 2
  const hexData = []

  for (let row = -1; row < rows; row++) {
    const y = row * v
    const xOffset = (row % 2 === 0) ? 0 : w / 2
    for (let col = -1; col < cols; col++) {
      const x = col * w + xOffset

      if (x < -r || x > WIDTH + r || y < -r || y > HEIGHT + r) continue

      const lonlat = projection.invert([x, y])
      if (!lonlat) continue

      const [lon, lat] = lonlat
      if (lat < MIN_LATITUDE || lat > MAX_LATITUDE) continue

      if (!geoContains(land, lonlat)) continue

      const country = getCountryAt(lonlat, countries)
      if (!country) continue

      hexData.push({ x, y, r, country, lonlat, id: `hex-${row}-${col}` })
    }
  }

  return hexData
}

function getCountryAt(lonlat, countries) {
  for (const country of countries) {
    if (geoContains(country, lonlat)) return country
  }
  return null
}

function hexPath(cx, cy, r) {
  const pts = []
  for (let i = 0; i < 6; i++) {
    const a = (60 * i - 30) * Math.PI / 180
    pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)])
  }
  return "M" + pts.map(p => p.join(",")).join("L") + "Z"
}

async function main() {
  try {
    console.log('Starting surgical hex world map generation...')
    const svgContent = await generateFixedHexWorldMapSVG()
    
    writeFileSync('public/hex-world-map-fixed.svg', svgContent)
    console.log(`✅ Generated at: public/hex-world-map-fixed.svg (${Math.round(svgContent.length / 1024)}KB)`)
    
    const tsContent = `// Auto-generated hex world map SVG (surgically fixed)
// Generated on ${new Date().toISOString()}
export const HEX_WORLD_MAP_SVG = \`${svgContent}\`
`
    
    writeFileSync('src/utils/generatedHexMapFixed.ts', tsContent)
    console.log('✅ Generated TypeScript constant: src/utils/generatedHexMapFixed.ts')
    
  } catch (error) {
    console.error('❌ Error:', error)
    process.exit(1)
  }
}

main()
