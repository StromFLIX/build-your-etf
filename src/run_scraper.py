#!/usr/bin/env python3
"""
CLI script for running the iShares ETF scraper.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from scraper.ishares_scraper import ISharesScraper


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Scrape ETF data from iShares")
    parser.add_argument(
        "--limit", 
        type=int, 
        help="Limit the number of ETFs to process (for testing)"
    )
    parser.add_argument(
        "--data-dir", 
        default="data/etf",
        help="Directory to store downloaded files (default: data/etf)"
    )
    parser.add_argument(
        "--max-concurrent", 
        type=int, 
        default=10,
        help="Maximum number of concurrent downloads (default: 10)"
    )
    parser.add_argument(
        "--etfs-json", 
        default="data/etfs.json",
        help="Path to JSON file containing ETFs list (default: data/etfs.json)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting iShares ETF scraper...")
    print(f"Data directory: {args.data_dir}")
    print(f"ETFs JSON file: {args.etfs_json}")
    print(f"Max concurrent downloads: {args.max_concurrent}")
    if args.limit:
        print(f"Limited to first {args.limit} ETFs")
    else:
        print("Processing ALL ETFs from the JSON file")
    
    scraper = ISharesScraper(
        data_dir=args.data_dir,
        max_concurrent=args.max_concurrent,
        etfs_json_path=args.etfs_json
    )
    
    try:
        async with scraper:
            successful, total = await scraper.scrape_all(limit=args.limit)
            print(f"\n✅ Scraping completed!")
            print(f"📊 Downloaded {successful} out of {total} ETFs")
            
            if successful < total:
                print(f"⚠️  {total - successful} downloads failed")
                
    except KeyboardInterrupt:
        print("\n🛑 Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())