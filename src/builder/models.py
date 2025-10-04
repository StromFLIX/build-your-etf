"""Pydantic models for ETF builder API."""

from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field


class ETFInfo(BaseModel):
    """Basic ETF information from the JSON file."""
    id: str
    name: str
    ticker: str = ""
    currency: str = "USD"
    ter: float = 0.0
    fund_size_millions: Optional[float] = None
    domicile: str = ""
    dist_yield: Optional[float] = None
    total_holdings: Optional[int] = None
    category: Optional[str] = None


class CountryDistribution(BaseModel):
    """Country distribution for an ETF."""
    country: str
    weight: float


class IndustryDistribution(BaseModel):
    """Industry distribution for an ETF."""
    industry: str
    weight: float


class ETFWithDistributions(ETFInfo):
    """ETF with its country and industry distributions."""
    country_distributions: List[CountryDistribution] = []
    industry_distributions: List[IndustryDistribution] = []


class OptimizationRequest(BaseModel):
    """Request model for ETF optimization."""
    model_config = {"extra": "forbid"}  # Don't allow extra fields like 'unallocated'
    
    countries: Dict[str, float] = Field(
        default_factory=dict,
        description="Desired country allocations as percentages (0-100). Remaining will be 'Unallocated'"
    )
    industries: Dict[str, float] = Field(
        default_factory=dict,
        description="Desired industry allocations as percentages (0-100). Remaining will be 'Unallocated'"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration options like max_etfs, excluded_etfs, etc."
    )

    def get_unallocated_countries(self) -> float:
        """Calculate unallocated country percentage."""
        allocated = sum(self.countries.values())
        return max(0.0, 100.0 - allocated)
    
    def get_unallocated_industries(self) -> float:
        """Calculate unallocated industry percentage."""  
        allocated = sum(self.industries.values())
        return max(0.0, 100.0 - allocated)

    def get_countries_with_unallocated(self) -> Dict[str, float]:
        """Get countries dict with unallocated added."""
        result = dict(self.countries)
        unallocated = self.get_unallocated_countries()
        if unallocated > 0:
            result["Unallocated"] = unallocated
        return result
    
    def get_industries_with_unallocated(self) -> Dict[str, float]:
        """Get industries dict with unallocated added."""
        result = dict(self.industries)
        unallocated = self.get_unallocated_industries()
        if unallocated > 0:
            result["Unallocated"] = unallocated
        return result


class ETFAllocation(BaseModel):
    """ETF allocation in the optimized portfolio."""
    etf_id: str
    name: str
    ticker: str
    weight: float
    ter: float


class OptimizationResult(BaseModel):
    """Result of ETF optimization."""
    etf_allocations: List[ETFAllocation]
    total_ter: float
    achieved_countries: Dict[str, float]
    achieved_industries: Dict[str, float]
    optimization_score: float
    country_unallocated: float = 0.0
    industry_unallocated: float = 0.0


class ETFListQuery(BaseModel):
    """Query parameters for ETF listing."""
    sort_by: str = Field(default="ter", description="Field to sort by")
    sort_order: str = Field(default="asc", description="Sort order: asc or desc")
    limit: int = Field(default=100, description="Number of results to return")
    offset: int = Field(default=0, description="Offset for pagination")
    min_fund_size: Optional[float] = Field(default=None, description="Minimum fund size in millions")
    max_ter: Optional[float] = Field(default=None, description="Maximum TER")
    currency: Optional[str] = Field(default=None, description="Filter by currency")