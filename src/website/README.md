# Build Your ETF - Website

A modern, clean web application for building custom ETF portfolios using Vue 3 and Tailwind CSS.

## Features

### 🎯 **Interactive Portfolio Builder**
- Start with MSCI World index as baseline
- Clean, modern black and white design
- Flow-based scrollable interface

### 🌍 **Geographic Visualization**
- Hex tile world map showing country allocations
- Softly glowing tiles indicate investment concentration
- Real-time updates based on your selections

### 📊 **Industry Analysis** 
- Pie chart visualization of sector distributions
- Clear breakdown of industry allocations
- Legend with percentage details

### ⚙️ **Allocation Controls**
- Intuitive country and industry selection
- Percentage-based allocation system
- Unallocated tracker (sticky field showing remaining allocation)
- Popular countries and industries for quick selection
- Real-time validation with visual feedback

### 📈 **Portfolio Output**
- Optimized ETF selection using advanced algorithms
- Cost optimization (TER minimization)  
- Detailed portfolio composition
- Performance metrics and optimization score
- Export options (CSV, copy to clipboard)

### 🚀 **Technical Features**
- Vue 3 with Composition API
- Tailwind CSS for styling
- D3.js for advanced visualizations
- TypeScript for type safety
- Real-time API integration with deployed backend
- Responsive design

## Architecture

### Frontend Stack
- **Vue 3**: Modern reactive framework
- **Tailwind CSS**: Utility-first styling
- **TypeScript**: Type safety and better DX
- **D3.js**: Data visualizations
- **Vite**: Fast build tool

### Backend Integration
- **API Endpoint**: https://build-your-etf.onrender.com
- **ETF Optimization**: Google OR-Tools CP-SAT solver
- **Data Source**: 5000+ iShares ETFs with distributions
- **Real-time**: Live portfolio optimization

## Design Philosophy

- **Minimalist**: No gradients, shadows, or visual clutter
- **Clear Borders**: Clean lines and defined sections
- **Black & White**: High contrast for clarity
- **Flow-based**: Scrollable sections guide user journey
- **Responsive**: Works on all screen sizes

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## User Journey

1. **Hero Section**: Introduction with floating hex world map
2. **Portfolio Builder**: Interactive allocation controls
3. **Visualization**: Real-time geographic and sector charts  
4. **Results**: Optimized ETF portfolio with detailed metrics
5. **Export**: Download or copy portfolio composition

## Key Components

- **HexWorldMap**: D3-powered geographic visualization
- **IndustryPieChart**: Sector allocation pie chart
- **AllocationControls**: Interactive percentage inputs
- **PortfolioOutput**: Results display with export options

The application provides a complete ETF building experience from initial exploration to final portfolio composition, all wrapped in a clean, modern interface.

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
