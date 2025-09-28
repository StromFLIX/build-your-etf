#!/usr/bin/env python3
"""
Example usage of the ETF Builder API.

This script demonstrates how to use the API endpoints to:
1. List available ETFs
2. Get country and industry lists
3. Optimize a portfolio
4. Retrieve specific ETF details
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"  # Change this to your deployed URL

def pretty_print(data: Dict[Any, Any], title: str = ""):
    """Pretty print JSON data."""
    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print('='*60)
    print(json.dumps(data, indent=2))

def test_api_endpoints():
    """Test all API endpoints with example requests."""
    
    print("🚀 ETF Builder API Example Usage")
    print("="*60)
    
    try:
        # Test root endpoint
        response = requests.get(f"{BASE_URL}/")
        response.raise_for_status()
        pretty_print(response.json(), "API Information")
        
        # Test health check
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        pretty_print(response.json(), "Health Check")
        
        # Get list of countries
        response = requests.get(f"{BASE_URL}/countries")
        response.raise_for_status()
        countries = response.json()
        print(f"\n📍 Available Countries: {len(countries)}")
        print("First 10 countries:", countries[:10])
        
        # Get list of industries  
        response = requests.get(f"{BASE_URL}/industries")
        response.raise_for_status()
        industries = response.json()
        print(f"\n🏭 Available Industries: {len(industries)}")
        print("First 10 industries:", industries[:10])
        
        # List ETFs with filtering
        print(f"\n📊 Listing ETFs (low cost, large funds)")
        response = requests.get(f"{BASE_URL}/etfs", params={
            "max_ter": 0.5,  # Max 0.5% TER
            "min_fund_size": 1000,  # Min 1B fund size
            "limit": 5,
            "sort_by": "ter",
            "sort_order": "asc"
        })
        response.raise_for_status()
        etfs = response.json()
        
        print(f"Found {len(etfs)} ETFs:")
        for etf in etfs:
            print(f"  • {etf['name']} ({etf['ticker']}) - TER: {etf['ter']}% - Size: ${etf['fund_size_millions']:.0f}M")
        
        # Get specific ETF details
        if etfs:
            etf_id = etfs[0]['id']
            response = requests.get(f"{BASE_URL}/etfs/{etf_id}")
            response.raise_for_status()
            etf_details = response.json()
            pretty_print({
                "id": etf_details['id'],
                "name": etf_details['name'],
                "ticker": etf_details['ticker'],
                "country_distributions": etf_details['country_distributions'][:5],
                "industry_distributions": etf_details['industry_distributions'][:5]
            }, f"ETF Details: {etf_details['name']}")
        
        # Optimize portfolio
        print(f"\n🎯 Portfolio Optimization Example")
        optimization_request = {
            "countries": {
                "United States": 40.0,
                "Germany": 10.0,
                "Japan": 8.0,
                "United Kingdom": 7.0
            },
            "industries": {
                "Information Technology": 20.0,
                "Healthcare": 10.0,
                "Financials": 8.0
            },
            "unallocated": 17.0,  # Remaining 17%
            "config": {
                "max_etfs": 6,
                "max_ter": 0.8,
                "min_fund_size": 500
            }
        }
        
        response = requests.post(f"{BASE_URL}/optimize", json=optimization_request)
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✅ Optimization Results:")
        print(f"Selected ETFs: {len(result['etf_allocations'])}")
        print(f"Total TER: {result['total_ter']:.3f}%")
        print(f"Optimization Score: {result['optimization_score']:.3f} (1.0 = perfect match)")
        
        print(f"\n📋 ETF Allocations:")
        for allocation in result['etf_allocations']:
            print(f"  • {allocation['weight']:.1%} - {allocation['ticker']} ({allocation['name'][:40]}...)")
            print(f"    TER: {allocation['ter']}%")
        
        print(f"\n🌍 Achieved Country Allocations:")
        for country, weight in result['achieved_countries'].items():
            if weight > 1.0:  # Only show significant allocations
                print(f"  • {country}: {weight:.1f}%")
        
        print(f"\n🏭 Achieved Industry Allocations:")
        for industry, weight in result['achieved_industries'].items():
            if weight > 2.0:  # Only show significant allocations
                print(f"  • {industry}: {weight:.1f}%")
        
        print(f"\n🎉 API test completed successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def example_portfolio_scenarios():
    """Show different portfolio optimization scenarios."""
    
    scenarios = [
        {
            "name": "Conservative Portfolio",
            "request": {
                "countries": {"United States": 30.0, "Germany": 20.0, "United Kingdom": 15.0},
                "industries": {"Bonds": 40.0, "Utilities": 10.0, "Consumer Staples": 10.0},
                "unallocated": 25.0,
                "config": {"max_etfs": 4, "max_ter": 0.5}
            }
        },
        {
            "name": "Tech-Heavy Growth Portfolio", 
            "request": {
                "countries": {"United States": 60.0, "South Korea": 5.0, "Taiwan": 5.0},
                "industries": {"Information Technology": 50.0, "Communication Services": 15.0},
                "unallocated": 30.0,
                "config": {"max_etfs": 5, "max_ter": 1.0}
            }
        },
        {
            "name": "European Focus",
            "request": {
                "countries": {"Germany": 25.0, "France": 20.0, "Netherlands": 10.0, "Italy": 10.0},
                "industries": {"Industrials": 20.0, "Financials": 15.0},
                "unallocated": 35.0,
                "config": {"max_etfs": 6, "max_ter": 0.8, "min_fund_size": 300}
            }
        }
    ]
    
    print(f"\n🌟 Example Portfolio Scenarios")
    print("="*60)
    
    for scenario in scenarios:
        print(f"\n📈 {scenario['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(f"{BASE_URL}/optimize", json=scenario['request'])
            response.raise_for_status()
            result = response.json()
            
            print(f"ETFs selected: {len(result['etf_allocations'])}")
            print(f"Total TER: {result['total_ter']:.3f}%")
            print(f"Score: {result['optimization_score']:.3f}")
            
            # Show top 3 ETFs
            for i, alloc in enumerate(result['etf_allocations'][:3]):
                print(f"  {i+1}. {alloc['weight']:.1%} - {alloc['ticker']}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Optimization failed: {e}")

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            raise requests.exceptions.RequestException("Server not healthy")
    except:
        print(f"❌ Cannot connect to API server at {BASE_URL}")
        print("Please make sure the server is running with:")
        print("  uv run python src/builder/server.py")
        sys.exit(1)
    
    # Run tests
    if test_api_endpoints():
        example_portfolio_scenarios()
    else:
        sys.exit(1)