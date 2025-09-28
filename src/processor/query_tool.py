#!/usr/bin/env python3
"""
ETF Database Query Utility

Interactive utility to explore the processed ETF database.
"""

import asyncio
import aiosqlite
import sys
from typing import List, Tuple


class ETFQueryTool:
    """Interactive ETF database query tool."""
    
    def __init__(self, db_path: str = "etf_data.sqlite"):
        self.db_path = db_path
    
    async def get_etf_distribution(self, etf_id: str) -> Tuple[List[Tuple], List[Tuple]]:
        """Get country and industry distribution for a specific ETF."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get country distribution
            cursor = await db.execute("""
                SELECT country, weight 
                FROM country_distributions 
                WHERE etf_id = ? 
                ORDER BY weight DESC
            """, (etf_id,))
            countries = await cursor.fetchall()
            
            # Get industry distribution
            cursor = await db.execute("""
                SELECT industry, weight 
                FROM industry_distributions 
                WHERE etf_id = ? 
                ORDER BY weight DESC
            """, (etf_id,))
            industries = await cursor.fetchall()
            
            return countries, industries
    
    async def find_etfs_by_country(self, country: str, min_weight: float = 1.0) -> List[Tuple]:
        """Find ETFs with significant allocation to a specific country."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT e.name, cd.weight, e.id
                FROM country_distributions cd
                JOIN etfs e ON cd.etf_id = e.id
                WHERE cd.country LIKE ? AND cd.weight >= ?
                ORDER BY cd.weight DESC
            """, (f"%{country}%", min_weight))
            return await cursor.fetchall()
    
    async def find_etfs_by_industry(self, industry: str, min_weight: float = 1.0) -> List[Tuple]:
        """Find ETFs with significant allocation to a specific industry."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT e.name, id.weight, e.id
                FROM industry_distributions id
                JOIN etfs e ON id.etf_id = e.id
                WHERE id.industry LIKE ? AND id.weight >= ?
                ORDER BY id.weight DESC
            """, (f"%{industry}%", min_weight))
            return await cursor.fetchall()
    
    async def compare_etfs(self, etf_id1: str, etf_id2: str) -> None:
        """Compare two ETFs side by side."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get ETF names
            cursor = await db.execute("SELECT name FROM etfs WHERE id = ?", (etf_id1,))
            name1 = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT name FROM etfs WHERE id = ?", (etf_id2,))
            name2 = (await cursor.fetchone())[0]
            
            print(f"\nComparing ETFs:")
            print(f"  {etf_id1}: {name1}")
            print(f"  {etf_id2}: {name2}")
            
            # Compare countries
            cursor = await db.execute("""
                SELECT 
                    COALESCE(c1.country, c2.country) as country,
                    COALESCE(c1.weight, 0) as weight1,
                    COALESCE(c2.weight, 0) as weight2
                FROM 
                    (SELECT country, weight FROM country_distributions WHERE etf_id = ?) c1
                FULL OUTER JOIN 
                    (SELECT country, weight FROM country_distributions WHERE etf_id = ?) c2
                    ON c1.country = c2.country
                WHERE COALESCE(c1.weight, 0) + COALESCE(c2.weight, 0) > 1
                ORDER BY COALESCE(c1.weight, 0) + COALESCE(c2.weight, 0) DESC
                LIMIT 15
            """, (etf_id1, etf_id2))
            
            countries = await cursor.fetchall()
            
            print(f"\nTop Country Allocations:")
            print(f"{'Country':<20} {etf_id1:<10} {etf_id2:<10} {'Diff':<10}")
            print("-" * 60)
            for country, w1, w2 in countries:
                diff = w1 - w2
                print(f"{country:<20} {w1:<10.2f} {w2:<10.2f} {diff:+10.2f}")
    
    async def get_coverage_matrix(self) -> None:
        """Show which countries/industries are covered by which ETFs."""
        async with aiosqlite.connect(self.db_path) as db:
            # Country coverage
            cursor = await db.execute("""
                SELECT 
                    country,
                    GROUP_CONCAT(etf_id) as etf_ids,
                    COUNT(*) as etf_count,
                    AVG(weight) as avg_weight
                FROM country_distributions
                WHERE weight > 1.0
                GROUP BY country
                ORDER BY etf_count DESC, avg_weight DESC
                LIMIT 20
            """)
            countries = await cursor.fetchall()
            
            print(f"\nCountry Coverage (weight > 1%):")
            print(f"{'Country':<20} {'ETFs':<15} {'Count':<8} {'Avg Weight':<12}")
            print("-" * 60)
            for country, etf_ids, count, avg_weight in countries:
                print(f"{country:<20} {etf_ids:<15} {count:<8} {avg_weight:<12.2f}")


async def interactive_mode():
    """Run interactive query mode."""
    tool = ETFQueryTool()
    
    print("ETF Database Query Tool")
    print("======================")
    print("Commands:")
    print("  list - List all ETFs")
    print("  show <etf_id> - Show ETF distribution")
    print("  country <name> - Find ETFs by country")
    print("  industry <name> - Find ETFs by industry")
    print("  compare <etf1> <etf2> - Compare two ETFs")
    print("  coverage - Show coverage matrix")
    print("  quit - Exit")
    
    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue
                
            cmd = command[0].lower()
            
            if cmd == "quit":
                break
            elif cmd == "list":
                async with aiosqlite.connect(tool.db_path) as db:
                    cursor = await db.execute("SELECT id, name FROM etfs ORDER BY name")
                    etfs = await cursor.fetchall()
                    print(f"\nAvailable ETFs:")
                    for etf_id, name in etfs:
                        print(f"  {etf_id}: {name}")
            
            elif cmd == "show" and len(command) > 1:
                etf_id = command[1]
                countries, industries = await tool.get_etf_distribution(etf_id)
                
                print(f"\nETF {etf_id} Distribution:")
                print(f"\nTop Countries:")
                for country, weight in countries[:10]:
                    print(f"  {country:<25} {weight:>8.2f}%")
                
                print(f"\nTop Industries:")
                for industry, weight in industries[:10]:
                    print(f"  {industry:<25} {weight:>8.2f}%")
            
            elif cmd == "country" and len(command) > 1:
                country = " ".join(command[1:])
                etfs = await tool.find_etfs_by_country(country)
                print(f"\nETFs with {country} exposure:")
                for name, weight, etf_id in etfs:
                    print(f"  {etf_id}: {name:<40} {weight:>8.2f}%")
            
            elif cmd == "industry" and len(command) > 1:
                industry = " ".join(command[1:])
                etfs = await tool.find_etfs_by_industry(industry)
                print(f"\nETFs with {industry} exposure:")
                for name, weight, etf_id in etfs:
                    print(f"  {etf_id}: {name:<40} {weight:>8.2f}%")
            
            elif cmd == "compare" and len(command) > 2:
                await tool.compare_etfs(command[1], command[2])
            
            elif cmd == "coverage":
                await tool.get_coverage_matrix()
            
            else:
                print("Unknown command or missing parameters")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_mode())
    else:
        print("Usage: python query_tool.py interactive")
        print("This will start an interactive ETF database query session.")