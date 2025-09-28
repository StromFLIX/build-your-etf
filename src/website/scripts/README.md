# Hex Map Generation Script

## Usage

To regenerate the hex world map SVG:

```bash
npm run generate-hex-map
```

Or run directly:

```bash
node scripts/generateHexMap.js
```

## What it does

1. **Downloads** world topology data (110m resolution) from Natural Earth
2. **Filters** out Antarctica and extreme polar regions 
3. **Removes** longitude duplicates (Alaska, Russia, New Zealand)
4. **Generates** hex grid with 2016 points covering the world
5. **Creates** both SVG file and TypeScript constant

## Output Files

- `public/hex-world-map-fixed.svg` - Standalone SVG file (~498KB)
- `src/utils/generatedHexMapFixed.ts` - TypeScript constant for bundling

## Configuration

You can modify these constants in the script:

```javascript
const HEX_RADIUS = 4           // Size of individual hexagons
const WIDTH = 800              // SVG viewport width  
const HEIGHT = 600             // SVG viewport height
const MIN_LATITUDE = -65       // Southern boundary (excludes Antarctica)
const MAX_LATITUDE = 80        // Northern boundary (minimal Arctic filtering)
```

## Dependencies

The script requires:
- `d3` - Geographic projections and path generation
- `topojson-client` - World topology processing  
- `node-fetch` - Download world data
- `d3-geo-projection` - Natural Earth projection

These are already included in package.json.