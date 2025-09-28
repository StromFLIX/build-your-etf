"""Database operations for ETF builder."""

import json
import sqlite3
from typing import List, Optional, Dict, Tuple
import aiosqlite
from pathlib import Path

from .models import ETFInfo, ETFWithDistributions, CountryDistribution, IndustryDistribution


class ETFDatabase:
    """Database handler for ETF data."""

    def __init__(self, db_path: str, etf_json_path: str):
        self.db_path = db_path
        self.etf_json_path = etf_json_path
        self._etf_metadata_cache = None

    async def _load_etf_metadata(self) -> Dict[str, dict]:
        """Load ETF metadata from JSON file."""
        if self._etf_metadata_cache is None:
            with open(self.etf_json_path, 'r', encoding='utf-8') as f:
                etfs_list = json.load(f)
            
            self._etf_metadata_cache = {}
            
            for etf in etfs_list:
                # Extract ETF ID from the link (numeric part)
                link = etf.get('link', '')
                etf_id = None
                if '/produkte/' in link:
                    try:
                        etf_id = link.split('/produkte/')[1].split('/')[0]
                    except:
                        pass
                
                if not etf_id:
                    continue
                    
                # Parse numeric fields safely
                ter = 0.0
                if etf.get('ter') and etf['ter'] != '-':
                    try:
                        ter = float(etf['ter'])
                    except ValueError:
                        pass
                
                fund_size_millions = None
                if etf.get('fundSizeMillions') and etf['fundSizeMillions'] != '-':
                    try:
                        fund_size_millions = float(etf['fundSizeMillions'])
                    except ValueError:
                        pass
                
                dist_yield = None
                if etf.get('distYield') and etf['distYield'] != '-':
                    try:
                        dist_yield = float(etf['distYield'])
                    except ValueError:
                        pass
                
                self._etf_metadata_cache[etf_id] = {
                    'id': etf_id,
                    'name': etf.get('name', ''),
                    'ticker': etf.get('ticker', ''),
                    'currency': etf.get('currency', ''),
                    'ter': ter,
                    'fund_size_millions': fund_size_millions,
                    'domicile': etf.get('domicile', ''),
                    'dist_yield': dist_yield,
                }
                
        return self._etf_metadata_cache

    async def get_etfs(
        self,
        sort_by: str = "ter",
        sort_order: str = "asc",
        limit: int = 100,
        offset: int = 0,
        min_fund_size: Optional[float] = None,
        max_ter: Optional[float] = None,
        currency: Optional[str] = None
    ) -> List[ETFWithDistributions]:
        """Get list of ETFs with filtering and sorting."""
        etf_metadata = await self._load_etf_metadata()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get ETF IDs from database
            query = """
                SELECT DISTINCT e.id, e.name, e.total_holdings
                FROM etfs e
            """
            params = []
            
            etfs_data = await db.execute(query)
            db_etfs = await etfs_data.fetchall()
            
            # Combine database and JSON metadata
            result_etfs = []
            
            for db_etf in db_etfs:
                etf_id, db_name, total_holdings = db_etf
                
                # Find matching metadata by ETF ID
                metadata = etf_metadata.get(etf_id)
                
                if not metadata:
                    # Create minimal metadata if not found
                    metadata = {
                        'id': etf_id,
                        'name': db_name,
                        'ticker': etf_id,
                        'currency': 'USD',
                        'ter': 0.0,
                        'fund_size_millions': None,
                        'domicile': '',
                        'dist_yield': None,
                    }
                
                # Apply filters
                if min_fund_size and (not metadata['fund_size_millions'] or metadata['fund_size_millions'] < min_fund_size):
                    continue
                if max_ter and metadata['ter'] > max_ter:
                    continue
                if currency and metadata['currency'].upper() != currency.upper():
                    continue
                
                # Get distributions
                country_dists = await self._get_country_distributions(db, etf_id)
                industry_dists = await self._get_industry_distributions(db, etf_id)
                
                etf = ETFWithDistributions(
                    id=etf_id,
                    name=metadata['name'] or db_name,
                    ticker=metadata['ticker'] or etf_id,
                    currency=metadata['currency'] or 'USD',
                    ter=metadata['ter'] or 0.0,
                    fund_size_millions=metadata['fund_size_millions'],
                    domicile=metadata['domicile'] or '',
                    dist_yield=metadata['dist_yield'],
                    total_holdings=total_holdings,
                    country_distributions=country_dists,
                    industry_distributions=industry_dists
                )
                result_etfs.append(etf)
            
            # Sort results
            sort_key = lambda x: getattr(x, sort_by, 0) or 0
            result_etfs.sort(key=sort_key, reverse=(sort_order.lower() == 'desc'))
            
            # Apply pagination
            return result_etfs[offset:offset + limit]

    async def _get_country_distributions(self, db: aiosqlite.Connection, etf_id: str) -> List[CountryDistribution]:
        """Get country distributions for an ETF."""
        query = """
            SELECT country, weight
            FROM country_distributions
            WHERE etf_id = ?
            ORDER BY weight DESC
        """
        cursor = await db.execute(query, (etf_id,))
        rows = await cursor.fetchall()
        
        # Convert from basis points to percentages and normalize if needed
        distributions = []
        total_weight = sum(row[1] for row in rows)
        
        for row in rows:
            # Convert from basis points to percentage 
            weight_pct = row[1] / 100.0
            
            # For leveraged ETFs, normalize to 100% total
            if total_weight > 12000:  # > 120% suggests leveraged/swap ETF
                weight_pct = (row[1] / total_weight) * 100.0
            
            distributions.append(CountryDistribution(country=row[0], weight=weight_pct))
            
        return distributions

    async def _get_industry_distributions(self, db: aiosqlite.Connection, etf_id: str) -> List[IndustryDistribution]:
        """Get industry distributions for an ETF."""
        query = """
            SELECT industry, weight
            FROM industry_distributions
            WHERE etf_id = ?
            AND industry != 'Sonstige'  -- Exclude the catch-all category
            ORDER BY weight DESC
        """
        cursor = await db.execute(query, (etf_id,))
        rows = await cursor.fetchall()
        
        # Convert from basis points to percentages and map German terms
        distributions = []
        total_weight = sum(row[1] for row in rows)
        
        # If we have distributions, normalize them
        if total_weight > 0:
            for row in rows:
                industry = self._map_industry_name(row[0])
                # Convert from basis points to percentage
                weight_pct = row[1] / 100.0
                
                # Normalize to 100% if this is a leveraged ETF
                if total_weight > 12000:  # > 120% suggests leveraged/swap ETF  
                    weight_pct = (row[1] / total_weight) * 100.0
                
                distributions.append(IndustryDistribution(industry=industry, weight=weight_pct))
        
        # If no meaningful distributions found, check if there's a 'Sonstige' entry
        if not distributions:
            cursor = await db.execute(
                "SELECT industry, weight FROM industry_distributions WHERE etf_id = ? AND industry = 'Sonstige'", 
                (etf_id,)
            )
            sonstige_row = await cursor.fetchone()
            if sonstige_row:
                distributions.append(IndustryDistribution(industry="Diversified", weight=100.0))
        
        return distributions

    def _map_industry_name(self, industry: str) -> str:
        """Map German and other industry names to English."""
        industry_mapping = {
            'Sonstige': 'Other',
            'Information Technology': 'Information Technology',
            'Consumer Discretionary': 'Consumer Discretionary',
            'Communication Services': 'Communication Services',
            'Healthcare': 'Healthcare',
            'Financials': 'Financials',
            'Industrials': 'Industrials',
            'Consumer Staples': 'Consumer Staples',
            'Energy': 'Energy',
            'Real Estate': 'Real Estate',
            'Materials': 'Materials',
            'Utilities': 'Utilities',
            'Bonds': 'Bonds',
            'Cash and/or Derivatives': 'Cash and Derivatives',
            # Add more mappings as needed
            'Versicherung': 'Insurance',
            'Produktionsmittel': 'Capital Goods',
            'Viehbestand': 'Livestock',
            'Stranded Cost Utility': 'Utilities',
            'Schatzbriefe': 'Bonds',
            'Gedeckt': 'Covered Bonds',
            'Verbrieft': 'Securitized',
        }
        
        return industry_mapping.get(industry, industry)

    async def get_etf_by_id(self, etf_id: str) -> Optional[ETFWithDistributions]:
        """Get a specific ETF by ID."""
        etfs = await self.get_etfs(limit=1000)  # Get all to find the specific one
        for etf in etfs:
            if etf.id == etf_id:
                return etf
        return None

    async def get_all_countries(self) -> List[str]:
        """Get all unique countries from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT country FROM country_distributions ORDER BY country")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_industries(self) -> List[str]:
        """Get all unique industries from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT industry FROM industry_distributions ORDER BY industry")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]