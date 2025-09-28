#!/usr/bin/env python3
"""
ETF Data Processor - Command Line Interface

This script processes ETF data files and builds a SQLite database 
with country and industry distributions.

Usage:
    python -m processor [data_dir] [db_path]
    
Examples:
    python -m processor
    python -m processor data/etf
    python -m processor data/etf custom_etf.sqlite
"""

import asyncio
import argparse
import logging
from pathlib import Path
from processor import ETFProcessor


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


async def query_database(db_path: str, query_type: str = "stats"):
    """Query the database for information."""
    import aiosqlite
    
    async with aiosqlite.connect(db_path) as db:
        if query_type == "stats":
            # Get basic statistics
            cursor = await db.execute("SELECT COUNT(*) FROM etfs")
            etf_count = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(DISTINCT country) FROM country_distributions")
            country_count = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(DISTINCT industry) FROM industry_distributions")
            industry_count = (await cursor.fetchone())[0]
            
            print(f"\nDatabase Statistics:")
            print(f"  Total ETFs: {etf_count}")
            print(f"  Unique Countries: {country_count}")
            print(f"  Unique Industries: {industry_count}")
            
        elif query_type == "etfs":
            cursor = await db.execute("SELECT id, name FROM etfs ORDER BY name")
            etfs = await cursor.fetchall()
            
            print(f"\nAvailable ETFs ({len(etfs)}):")
            for etf_id, name in etfs:
                print(f"  {etf_id}: {name}")
                
        elif query_type == "countries":
            cursor = await db.execute("""
                SELECT country, COUNT(*) as etf_count, AVG(weight) as avg_weight
                FROM country_distributions 
                GROUP BY country 
                ORDER BY etf_count DESC, avg_weight DESC
                LIMIT 20
            """)
            countries = await cursor.fetchall()
            
            print(f"\nTop Countries by ETF Coverage:")
            print(f"{'Country':<20} {'ETFs':<8} {'Avg Weight %':<12}")
            print("-" * 42)
            for country, etf_count, avg_weight in countries:
                print(f"{country:<20} {etf_count:<8} {avg_weight:<12.2f}")
                
        elif query_type == "industries":
            cursor = await db.execute("""
                SELECT industry, COUNT(*) as etf_count, AVG(weight) as avg_weight
                FROM industry_distributions 
                GROUP BY industry 
                ORDER BY etf_count DESC, avg_weight DESC
                LIMIT 20
            """)
            industries = await cursor.fetchall()
            
            print(f"\nTop Industries by ETF Coverage:")
            print(f"{'Industry':<25} {'ETFs':<8} {'Avg Weight %':<12}")
            print("-" * 47)
            for industry, etf_count, avg_weight in industries:
                print(f"{industry:<25} {etf_count:<8} {avg_weight:<12.2f}")


def main():
    """Main command line interface."""
    parser = argparse.ArgumentParser(
        description="Process ETF data and build SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "data_dir", 
        nargs="?", 
        default="data/etf",
        help="Directory containing ETF .xls files (default: data/etf)"
    )
    
    parser.add_argument(
        "db_path",
        nargs="?", 
        default="etf_data.sqlite",
        help="Output SQLite database path (default: etf_data.sqlite)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--query", "-q",
        choices=["stats", "etfs", "countries", "industries"],
        help="Query existing database instead of processing"
    )
    
    parser.add_argument(
        "--max-concurrent", "-c",
        type=int,
        default=5,
        help="Maximum concurrent file processing (default: 5)"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.query:
        # Query mode
        if not Path(args.db_path).exists():
            print(f"Database {args.db_path} does not exist. Run processing first.")
            return 1
            
        asyncio.run(query_database(args.db_path, args.query))
        return 0
    
    # Processing mode
    if not Path(args.data_dir).exists():
        print(f"Error: Data directory '{args.data_dir}' does not exist")
        return 1
    
    async def run_processor():
        async with ETFProcessor(args.data_dir, args.db_path) as processor:
            await processor.run()
    
    try:
        asyncio.run(run_processor())
        print(f"\nProcessing complete! Database saved to: {args.db_path}")
        
        # Show quick stats
        asyncio.run(query_database(args.db_path, "stats"))
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())