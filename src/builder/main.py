"""FastAPI application for ETF Builder backend."""

import os
from typing import List, Dict
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .database import ETFDatabase
from .optimizer import ETFOptimizer
from .models import (
    ETFWithDistributions, 
    OptimizationRequest, 
    OptimizationResult,
    ETFListQuery
)

# Initialize FastAPI app
app = FastAPI(
    title="ETF Builder API",
    description="Build your perfect ETF portfolio by specifying desired country and industry allocations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and optimizer
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "etf_data.sqlite"
ETF_JSON_PATH = BASE_DIR / "data" / "etfs.json"

db = ETFDatabase(str(DB_PATH), str(ETF_JSON_PATH))
optimizer = ETFOptimizer(db)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ETF Builder API",
        "version": "1.0.0",
        "description": "Build your perfect ETF portfolio",
        "endpoints": {
            "/etfs": "List available ETFs with filtering and sorting",
            "/etfs/{etf_id}": "Get specific ETF details",
            "/optimize": "Optimize ETF portfolio based on desired allocations",
            "/countries": "Get list of all available countries",
            "/industries": "Get list of all available industries"
        }
    }


@app.get("/etfs", response_model=List[ETFWithDistributions])
async def list_etfs(
    sort_by: str = Query(default="ter", description="Field to sort by (ter, fund_size_millions, name)"),
    sort_order: str = Query(default="asc", description="Sort order: asc or desc"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    min_fund_size: float = Query(default=None, description="Minimum fund size in millions"),
    max_ter: float = Query(default=None, description="Maximum TER (e.g., 1.0 for 1%)"),
    currency: str = Query(default=None, description="Filter by currency (USD, EUR, GBP, etc.)")
):
    """
    Get list of available ETFs with their country and industry distributions.
    
    This endpoint provides a rich list of ETFs that can be filtered and sorted
    by various criteria including TER, fund size, and currency.
    """
    try:
        etfs = await db.get_etfs(
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
            min_fund_size=min_fund_size,
            max_ter=max_ter,
            currency=currency
        )
        return etfs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ETFs: {str(e)}")


@app.get("/etfs/{etf_id}", response_model=ETFWithDistributions)
async def get_etf(etf_id: str):
    """Get detailed information about a specific ETF."""
    try:
        etf = await db.get_etf_by_id(etf_id)
        if not etf:
            raise HTTPException(status_code=404, detail=f"ETF with ID {etf_id} not found")
        return etf
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ETF: {str(e)}")


@app.post("/optimize", response_model=OptimizationResult)
async def optimize_portfolio(request: OptimizationRequest):
    """
    Optimize ETF portfolio based on desired country and industry allocations.
    
    This endpoint uses mathematical optimization to find the best combination
    of ETFs that match your desired geographic and sector allocations while
    minimizing costs (TER).
    
    Example request:
    ```json
    {
        "countries": {"United States": 60.0, "Germany": 20.0, "Japan": 10.0},
        "industries": {"Information Technology": 30.0, "Healthcare": 20.0},
        "config": {
            "max_etfs": 5,
            "max_ter": 1.0,
            "min_fund_size": 500,
            "excluded_etfs": []
        }
    }
    ```
    
    Note: Unallocated percentages are automatically calculated:
    - Countries: Remaining percentage becomes "Unallocated" 
    - Industries: Remaining percentage becomes "Unallocated"
    """
    try:
        # Validate that allocations don't exceed 100%
        total_countries = sum(request.countries.values())
        total_industries = sum(request.industries.values())
        
        if total_countries > 100:
            raise HTTPException(
                status_code=400, 
                detail=f"Total country allocations exceed 100%: {total_countries}%"
            )
        
        if total_industries > 100:
            raise HTTPException(
                status_code=400, 
                detail=f"Total industry allocations exceed 100%: {total_industries}%"
            )
        
        result = await optimizer.optimize_portfolio(request)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization error: {str(e)}")


@app.get("/countries", response_model=List[str])
async def list_countries():
    """Get list of all available countries for allocation."""
    try:
        countries = await db.get_all_countries()
        return sorted(countries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving countries: {str(e)}")


@app.get("/industries", response_model=List[str])
async def list_industries():
    """Get list of all available industries for allocation."""
    try:
        industries = await db.get_all_industries()
        return sorted(industries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving industries: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": str(DB_PATH.exists())}


if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "src.builder.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )