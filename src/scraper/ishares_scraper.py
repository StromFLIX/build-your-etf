"""
iShares ETF Scraper

This module scrapes ETF data from the iShares website, including:
- Listing all available ETFs
- Downloading Excel files with fund holdings
- Extracting product information and distributions
"""

import asyncio
import re
import urllib.parse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ISharesScraper:
    """Scrapes ETF data from iShares Switzerland website."""
    
    BASE_URL = "https://www.ishares.com"
    API_BASE_URL = "https://www.blackrock.com/api-gateway"
    PRODUCTS_URL = "https://www.ishares.com/ch/privatkunden/de/produkte/etf-investments#/?productView=etf&pageNumber={}&sortColumn=totalFundSizeInMillions&sortDirection=desc&dataView=keyFacts&showAll=true"
    
    # Try the screener API endpoint
    SCREENER_API = "https://www.ishares.com/ch/privatkunden/de/products/etf-screener/api/fund-search"
    
    def __init__(self, data_dir: str = "data/etf", max_concurrent: int = 10, etfs_json_path: str = "data/etfs.json"):
        """
        Initialize the scraper.
        
        Args:
            data_dir: Directory to store downloaded files
            max_concurrent: Maximum number of concurrent requests
            etfs_json_path: Path to the JSON file containing all ETFs
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self.etfs_json_path = Path(etfs_json_path)
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit=20)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def load_etfs_from_json(self) -> List[Dict[str, str]]:
        """
        Load ETF list from the provided JSON file.
        
        Returns:
            List of dictionaries containing ETF information
        """
        try:
            if not self.etfs_json_path.exists():
                raise FileNotFoundError(f"ETFs JSON file not found: {self.etfs_json_path}")
            
            with open(self.etfs_json_path, 'r', encoding='utf-8') as f:
                etfs_data = json.load(f)
            
            etfs = []
            for etf in etfs_data:
                # Extract product ID from the link URL
                link = etf.get('link', '')
                product_id_match = re.search(r'/(\d+)/', link)
                if product_id_match:
                    product_id = product_id_match.group(1)
                else:
                    # Fallback: try to extract from end of URL
                    product_id_match = re.search(r'/(\d+)(?:[/?]|$)', link)
                    if product_id_match:
                        product_id = product_id_match.group(1)
                    else:
                        logger.warning(f"Could not extract product ID from URL: {link}")
                        continue
                
                # Clean name for filename
                name = etf.get('name', f"ETF_{product_id}")
                clean_name = re.sub(r'[^\w\s-]', '', name).strip()
                clean_name = re.sub(r'\s+', '-', clean_name)
                
                etf_info = {
                    'product_id': product_id,
                    'name': name,
                    'clean_name': clean_name,
                    'ticker': etf.get('ticker', ''),
                    'url': link,
                    'currency': etf.get('currency', ''),
                    'ter': etf.get('ter', ''),
                    'fund_size': etf.get('fundSizeMillions', ''),
                }
                etfs.append(etf_info)
            
            logger.info(f"Loaded {len(etfs)} ETFs from JSON file")
            return etfs
            
        except Exception as e:
            logger.error(f"Error loading ETFs from JSON file: {e}")
            raise

    async def get_etf_list(self) -> List[Dict[str, str]]:
        """
        Get list of all ETFs from the JSON file.
        
        Returns:
            List of dictionaries containing ETF information
        """
        return self.load_etfs_from_json()




    
    async def get_download_url(self, product_id: str, product_url: str) -> Optional[str]:
        """
        Get the Excel download URL for a specific ETF.
        
        Args:
            product_id: The product ID
            product_url: The product page URL
            
        Returns:
            Download URL for Excel file or None if not found
        """
        try:
            async with self.session.get(product_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get product page for {product_id}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Strategy 1: Look for direct download links with 'ajax' and 'xls'
                download_links = soup.find_all('a', href=re.compile(r'ajax.*fileType=xls', re.I))
                
                if download_links:
                    download_url = download_links[0].get('href')
                else:
                    # Strategy 2: Look for any link containing 'xls' or 'excel'
                    download_links = soup.find_all('a', href=re.compile(r'(\.xls|excel)', re.I))
                    if download_links:
                        download_url = download_links[0].get('href')
                    else:
                        # Strategy 3: Construct the download URL based on common iShares patterns
                        # Look for the fund name in the page to construct the URL
                        h1_elem = soup.find('h1')
                        if h1_elem:
                            fund_name = h1_elem.get_text(strip=True)
                            # Clean the name for URL construction
                            clean_fund_name = re.sub(r'[^\w\s-]', '', fund_name)
                            clean_fund_name = re.sub(r'\s+', '-', clean_fund_name)
                            
                            # Try common iShares download URL patterns
                            patterns = [
                                f"{product_url.rstrip('/')}/1535604580403.ajax?fileType=xls&fileName={clean_fund_name}_fund&dataType=fund",
                                f"{product_url.rstrip('/')}/fund-holdings.xls",
                                f"{self.BASE_URL}/ch/privatkunden/de/produkte/{product_id}/fund-holdings.xls",
                            ]
                            
                            for pattern in patterns:
                                # Test if this URL exists
                                try:
                                    async with self.session.head(pattern) as test_response:
                                        if test_response.status == 200:
                                            download_url = pattern
                                            break
                                except:
                                    continue
                            else:
                                logger.warning(f"Could not find download URL for product {product_id}")
                                return None
                        else:
                            logger.warning(f"Could not find fund name for product {product_id}")
                            return None
                
                # Make URL absolute
                if download_url.startswith('/'):
                    download_url = self.BASE_URL + download_url
                elif not download_url.startswith('http'):
                    # Relative to product page
                    download_url = urllib.parse.urljoin(product_url, download_url)
                
                return download_url
                
        except Exception as e:
            logger.error(f"Error getting download URL for {product_id}: {e}")
            return None
    
    async def download_etf_data(self, etf_info: Dict[str, str]) -> bool:
        """
        Download Excel file for a specific ETF.
        
        Args:
            etf_info: Dictionary containing ETF information
            
        Returns:
            True if download was successful, False otherwise
        """
        async with self.semaphore:
            try:
                product_id = etf_info['product_id']
                clean_name = etf_info['clean_name']
                
                # Check if file already exists
                filename = f"{product_id}_{clean_name}.xls"
                filepath = self.data_dir / filename
                
                if filepath.exists():
                    logger.info(f"File already exists: {filename}")
                    return True
                
                logger.info(f"Processing ETF {product_id}: {etf_info['name']}")
                
                # Get download URL
                download_url = await self.get_download_url(product_id, etf_info['url'])
                if not download_url:
                    logger.warning(f"Could not find download URL for {product_id}")
                    return False
                
                logger.info(f"Downloading from: {download_url}")
                
                # Download the file
                async with self.session.get(download_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to download {product_id}, status: {response.status}")
                        return False
                    
                    # Save to file
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                
                logger.info(f"Successfully downloaded: {filename}")
                return True
                
            except Exception as e:
                logger.error(f"Error downloading ETF data for {etf_info['product_id']}: {e}")
                return False
    
    async def scrape_all(self, limit: Optional[int] = None) -> Tuple[int, int]:
        """
        Scrape all ETFs from iShares.
        
        Args:
            limit: Optional limit on number of ETFs to process
            
        Returns:
            Tuple of (successful_downloads, total_etfs)
        """
        logger.info("Starting ETF scraping process")
        
        # Get list of all ETFs
        etfs = await self.get_etf_list()
        
        if limit:
            etfs = etfs[:limit]
            logger.info(f"Limited to first {limit} ETFs")
        
        # Download all ETF data concurrently
        download_tasks = [self.download_etf_data(etf) for etf in etfs]
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        successful = sum(1 for result in results if result is True)
        
        logger.info(f"Scraping completed: {successful}/{len(etfs)} successful downloads")
        return successful, len(etfs)


async def main():
    """Main entry point for running the scraper."""
    scraper = ISharesScraper(etfs_json_path="data/etfs.json")
    
    async with scraper:
        # For testing, limit to first 10 ETFs
        successful, total = await scraper.scrape_all(limit=10)
        print(f"Downloaded {successful} out of {total} ETFs")


if __name__ == "__main__":
    asyncio.run(main())