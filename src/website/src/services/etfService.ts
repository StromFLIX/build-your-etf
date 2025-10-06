// Detect environment - use localhost in development, production URL otherwise
const API_BASE = import.meta.env.DEV 
  ? 'http://localhost:8000' 
  : 'https://build-your-etf.backend.stromflix.com'

// Default MSCI World ETF allocation (100% in a single global ETF)
export function getDefaultETFAllocation() {
  return [
    {
      etf_id: 'default-msci-world',
      name: 'iShares Core MSCI World UCITS ETF USD (Acc)',
      ticker: 'EUNL',
      weight: 1.0,
      ter: 0.0020
    }
  ]
}

// Default MSCI World data (approximate allocations)
export function getDefaultMSCIWorldData() {
  return {
    countries: {
      'United States': 69.8,
      'Japan': 5.8,
      'United Kingdom': 3.6,
      'France': 3.1,
      'Canada': 3.0,
      'Switzerland': 2.5,
      'Taiwan': 1.8,
      'Netherlands': 1.4,
      'Germany': 1.3,
      'Australia': 1.2,
      'South Korea': 1.1,
      'Italy': 0.8,
      'India': 0.8,
      'Denmark': 0.7,
      'Hong Kong': 0.6,
      'Sweden': 0.6,
      'Spain': 0.5,
      'Belgium': 0.4,
      'Finland': 0.3,
      'Israel': 0.3
    },
    industries: {
      'Information Technology': 24.8,
      'Financials': 13.2,
      'Healthcare': 12.1,
      'Consumer Discretionary': 10.4,
      'Communication Services': 8.9,
      'Industrials': 8.7,
      'Consumer Staples': 6.8,
      'Energy': 4.3,
      'Materials': 4.2,
      'Real Estate': 2.4,
      'Utilities': 2.2,
    }
  }
}

export interface OptimizationResult {
  etf_allocations: {
    etf_id: string
    name: string
    ticker: string
    weight: number
    ter: number
  }[]
  total_ter: number
  achieved_countries: Record<string, number>
  achieved_industries: Record<string, number>
  optimization_score: number
  country_unallocated: number
  industry_unallocated: number
}

export async function optimizePortfolio(
  countries: Record<string, number>, 
  industries: Record<string, number>,
  categories?: string[],
  maxEtfs: number = 3
): Promise<OptimizationResult> {
  const response = await fetch(`${API_BASE}/optimize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      countries,
      industries,
      config: {
        max_etfs: maxEtfs,
        max_ter: 1.0,
        min_fund_size: 100,
        excluded_etfs: [],
        categories: categories || undefined
      }
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Optimization failed: ${error}`)
  }

  return response.json()
}

export async function getAvailableCountries(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/countries`)
  if (!response.ok) {
    throw new Error('Failed to fetch countries')
  }
  return response.json()
}

export async function getAvailableIndustries(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/industries`)
  if (!response.ok) {
    throw new Error('Failed to fetch industries')
  }
  return response.json()
}

export async function getETFs(limit: number = 50) {
  const response = await fetch(`${API_BASE}/etfs?limit=${limit}`)
  if (!response.ok) {
    throw new Error('Failed to fetch ETFs')
  }
  return response.json()
}

export async function getAvailableCategories(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/categories`)
  if (!response.ok) {
    throw new Error('Failed to fetch categories')
  }
  return response.json()
}