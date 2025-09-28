"""
Modern async ETF processor that parses iShares ETF data and builds SQLite database.
"""

import asyncio
import aiosqlite
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional, AsyncGenerator
import re
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from .translations import translate_country, translate_industry


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ETFHolding:
    """Represents a single holding in an ETF."""
    symbol: str
    name: str
    sector: str
    country: str
    weight: float
    etf_id: str


@dataclass
class ETFDistribution:
    """Represents aggregated distribution data for an ETF."""
    etf_id: str
    etf_name: str
    distribution_type: str  # 'country' or 'industry'
    category: str  # country name or industry name
    weight: float


class ETFProcessor:
    """Process ETF data files and build SQLite database."""
    
    def __init__(self, data_dir: str = "data/etf", db_path: str = "etf_data.sqlite"):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def initialize_database(self) -> None:
        """Initialize SQLite database with required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS etfs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    inception_date TEXT,
                    total_holdings INTEGER,
                    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS country_distributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    etf_id TEXT NOT NULL,
                    country TEXT NOT NULL,
                    weight REAL NOT NULL,
                    FOREIGN KEY (etf_id) REFERENCES etfs (id),
                    UNIQUE(etf_id, country)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS industry_distributions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    etf_id TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    weight REAL NOT NULL,
                    FOREIGN KEY (etf_id) REFERENCES etfs (id),
                    UNIQUE(etf_id, industry)
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_country_etf_id ON country_distributions(etf_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_industry_etf_id ON industry_distributions(etf_id)
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    def parse_xml_file(self, file_path: Path) -> Tuple[str, str, List[ETFHolding]]:
        """Parse XML file to extract ETF data. Runs in thread pool."""
        try:
            # Clean the XML content (remove BOM and fix encoding issues)
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # Fix common XML issues
            content = content.replace('&', '&amp;')  # Escape unescaped ampersands
            content = re.sub(r'&amp;([a-zA-Z]+;)', r'&\1', content)  # But don't double-escape
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Extract ETF metadata
            etf_id = file_path.stem.split('_')[0]  # Extract ID from filename
            etf_name = "Unknown"
            
            # Find ETF name in the document
            for elem in root.iter():
                if elem.tag.endswith('}Data') and elem.text and 'iShares' in elem.text:
                    if 'UCITS ETF' in elem.text:
                        etf_name = elem.text.strip()
                        break
            
            # Extract holdings data from the "Positionen" worksheet
            holdings = []
            
            # Find the Positionen worksheet
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            worksheets = root.findall('.//ss:Worksheet', ns)
            
            positions_ws = None
            for ws in worksheets:
                if ws.get(f'{{{ns["ss"]}}}Name') == 'Positionen':
                    positions_ws = ws
                    break
            
            if positions_ws is not None:
                # Extract table data
                rows = positions_ws.findall('.//ss:Row', ns)
                
                # Find header row first to determine column positions
                header_row = None
                header_indices = {}
                
                for row in rows:
                    cells = row.findall('.//ss:Cell', ns)
                    row_data = []
                    for cell in cells:
                        data_elem = cell.find('.//ss:Data', ns)
                        if data_elem is not None and data_elem.text:
                            row_data.append(data_elem.text.strip())
                        else:
                            row_data.append("")
                    
                    # Check if this is a header row by looking for specific column names
                    if len(row_data) >= 6:
                        for i, cell_value in enumerate(row_data):
                            cell_lower = cell_value.lower()
                            if 'standort' in cell_lower or 'location' in cell_lower:
                                header_indices['country'] = i
                            elif 'gewichtung' in cell_lower or 'weight' in cell_lower:
                                header_indices['weight'] = i
                            elif cell_value == 'Name' and i > 0:  # Name column (not the first one)
                                header_indices['name'] = i
                            elif 'sektor' in cell_lower or 'sector' in cell_lower:
                                header_indices['sector'] = i
                            elif 'emittententicker' in cell_lower or 'ticker' in cell_lower:
                                header_indices['symbol'] = i
                        
                        # If we found the key columns, this is our header row
                        if 'country' in header_indices and 'weight' in header_indices:
                            header_row = row_data
                            logger.info(f"Found header row with columns: country={header_indices.get('country')}, weight={header_indices.get('weight')}")
                            break
                
                # If we couldn't find proper header, skip this file
                if not header_indices or 'country' not in header_indices or 'weight' not in header_indices:
                    logger.warning(f"Could not identify column structure in {file_path.name}, skipping")
                    return etf_id, etf_name, []
                
                # Process data rows using the discovered column indices
                for row in rows:
                    cells = row.findall('.//ss:Cell', ns)
                    row_data = []
                    for cell in cells:
                        data_elem = cell.find('.//ss:Data', ns)
                        if data_elem is not None and data_elem.text:
                            row_data.append(data_elem.text.strip())
                        else:
                            row_data.append("")
                    
                    # Skip header row and rows with insufficient data
                    if row_data == header_row or len(row_data) <= max(header_indices.values()):
                        continue
                    
                    try:
                        # Extract data using dynamic column positions
                        country = row_data[header_indices['country']] if len(row_data) > header_indices['country'] else ""
                        weight_str = row_data[header_indices['weight']] if len(row_data) > header_indices['weight'] else ""
                        name = row_data[header_indices.get('name', 1)] if len(row_data) > header_indices.get('name', 1) else ""
                        sector = row_data[header_indices.get('sector', 2)] if len(row_data) > header_indices.get('sector', 2) else ""
                        symbol = row_data[header_indices.get('symbol', 0)] if len(row_data) > header_indices.get('symbol', 0) else ""
                        
                        # Validate the data
                        if not country or not weight_str or not name:
                            continue
                        
                        # Check if country looks like a number (indicates wrong column)
                        try:
                            float(country)
                            # If country is a number, skip this row as it's likely wrong column mapping
                            continue
                        except ValueError:
                            pass  # Good, country is not a number
                        
                        # Convert weight to float
                        weight = float(weight_str) * 100  # Convert to percentage
                        if weight <= 0:
                            continue
                        
                        holding = ETFHolding(
                            symbol=symbol or "N/A",
                            name=name,
                            sector=sector or "Unknown",
                            country=country,
                            weight=weight,
                            etf_id=etf_id
                        )
                        holdings.append(holding)
                        
                    except (ValueError, IndexError) as e:
                        continue
            
            logger.info(f"Parsed {file_path.name}: {len(holdings)} holdings")
            return etf_id, etf_name, holdings
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return "", "", []
    
    async def parse_file_async(self, file_path: Path) -> Tuple[str, str, List[ETFHolding]]:
        """Async wrapper for file parsing."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.parse_xml_file, file_path)
    
    def aggregate_distributions(self, holdings: List[ETFHolding]) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Aggregate holdings by country and industry, with German to English translation."""
        country_dist = {}
        industry_dist = {}
        
        for holding in holdings:
            # Aggregate by country (translate to English)
            if holding.country:
                english_country = translate_country(holding.country)
                country_dist[english_country] = country_dist.get(english_country, 0) + holding.weight
            
            # Aggregate by industry/sector (translate to English)
            if holding.sector:
                english_industry = translate_industry(holding.sector)
                industry_dist[english_industry] = industry_dist.get(english_industry, 0) + holding.weight
        
        return country_dist, industry_dist
    
    async def save_etf_data(self, etf_id: str, etf_name: str, 
                           country_dist: Dict[str, float], 
                           industry_dist: Dict[str, float]) -> None:
        """Save ETF data to database."""
        async with aiosqlite.connect(self.db_path) as db:
            # Insert/update ETF record
            await db.execute("""
                INSERT OR REPLACE INTO etfs (id, name, total_holdings)
                VALUES (?, ?, ?)
            """, (etf_id, etf_name, len(country_dist) + len(industry_dist)))
            
            # Clear existing distributions
            await db.execute("DELETE FROM country_distributions WHERE etf_id = ?", (etf_id,))
            await db.execute("DELETE FROM industry_distributions WHERE etf_id = ?", (etf_id,))
            
            # Insert country distributions
            for country, weight in country_dist.items():
                await db.execute("""
                    INSERT INTO country_distributions (etf_id, country, weight)
                    VALUES (?, ?, ?)
                """, (etf_id, country, weight))
            
            # Insert industry distributions
            for industry, weight in industry_dist.items():
                await db.execute("""
                    INSERT INTO industry_distributions (etf_id, industry, weight)
                    VALUES (?, ?, ?)
                """, (etf_id, industry, weight))
            
            await db.commit()
    
    async def get_etf_files(self) -> AsyncGenerator[Path, None]:
        """Async generator for ETF files."""
        if not self.data_dir.exists():
            logger.error(f"Data directory {self.data_dir} does not exist")
            return
        
        for file_path in self.data_dir.glob("*.xls"):
            yield file_path
    
    async def process_single_file(self, file_path: Path) -> None:
        """Process a single ETF file."""
        try:
            etf_id, etf_name, holdings = await self.parse_file_async(file_path)
            
            if not holdings:
                logger.warning(f"No holdings found in {file_path.name}")
                return
            
            # Aggregate distributions
            country_dist, industry_dist = self.aggregate_distributions(holdings)
            
            # Save to database
            await self.save_etf_data(etf_id, etf_name, country_dist, industry_dist)
            
            logger.info(f"Processed {file_path.name}: {len(country_dist)} countries, {len(industry_dist)} industries")
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
    
    async def process_all_files(self, max_concurrent: int = 5) -> None:
        """Process all ETF files with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(file_path: Path):
            async with semaphore:
                await self.process_single_file(file_path)
        
        tasks = []
        async for file_path in self.get_etf_files():
            task = asyncio.create_task(process_with_semaphore(file_path))
            tasks.append(task)
        
        if tasks:
            logger.info(f"Processing {len(tasks)} ETF files...")
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("All files processed")
        else:
            logger.warning("No ETF files found to process")
    
    async def get_stats(self) -> Dict:
        """Get database statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Count ETFs
            cursor = await db.execute("SELECT COUNT(*) FROM etfs")
            stats['total_etfs'] = (await cursor.fetchone())[0]
            
            # Count unique countries
            cursor = await db.execute("SELECT COUNT(DISTINCT country) FROM country_distributions")
            stats['unique_countries'] = (await cursor.fetchone())[0]
            
            # Count unique industries
            cursor = await db.execute("SELECT COUNT(DISTINCT industry) FROM industry_distributions")
            stats['unique_industries'] = (await cursor.fetchone())[0]
            
            # Top countries by total weight
            cursor = await db.execute("""
                SELECT country, SUM(weight) as total_weight 
                FROM country_distributions 
                GROUP BY country 
                ORDER BY total_weight DESC 
                LIMIT 10
            """)
            stats['top_countries'] = await cursor.fetchall()
            
            # Top industries by total weight
            cursor = await db.execute("""
                SELECT industry, SUM(weight) as total_weight 
                FROM industry_distributions 
                GROUP BY industry 
                ORDER BY total_weight DESC 
                LIMIT 10
            """)
            stats['top_industries'] = await cursor.fetchall()
            
            return stats
    
    async def run(self) -> None:
        """Main processing pipeline."""
        logger.info("Starting ETF processing...")
        
        # Initialize database
        await self.initialize_database()
        
        # Process all files
        await self.process_all_files()
        
        # Show statistics
        stats = await self.get_stats()
        logger.info(f"Processing complete!")
        logger.info(f"Statistics: {stats}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)


async def main():
    """Main entry point."""
    import sys
    
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/etf"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "etf_data.sqlite"
    
    async with ETFProcessor(data_dir, db_path) as processor:
        await processor.run()


if __name__ == "__main__":
    asyncio.run(main())