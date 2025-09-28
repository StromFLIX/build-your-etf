#!/usr/bin/env python3
"""
Integration test for ETF processor
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from processor import ETFProcessor


async def test_processor():
    """Test the ETF processor with sample data."""
    print("🧪 Running ETF Processor Integration Test")
    
    # Create temporary directory for test database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_etf.sqlite"
        
        # Test with existing data
        data_dir = Path(__file__).parent.parent.parent / "data" / "etf"
        
        if not data_dir.exists():
            print("❌ No test data found at", data_dir)
            return False
        
        print(f"📁 Using data directory: {data_dir}")
        print(f"🗄️ Using database: {db_path}")
        
        try:
            # Initialize processor
            async with ETFProcessor(str(data_dir), str(db_path)) as processor:
                print("✅ Processor initialized")
                
                # Run processing
                await processor.run()
                print("✅ Processing completed")
                
                # Get statistics
                stats = await processor.get_stats()
                print(f"✅ Statistics retrieved: {stats['total_etfs']} ETFs processed")
                
                # Validate results
                assert stats['total_etfs'] > 0, "No ETFs were processed"
                assert stats['unique_countries'] > 0, "No countries found"
                assert stats['unique_industries'] > 0, "No industries found"
                
                print("✅ All assertions passed")
                
                # Show sample results
                print(f"\n📊 Results:")
                print(f"   Total ETFs: {stats['total_etfs']}")
                print(f"   Unique Countries: {stats['unique_countries']}")
                print(f"   Unique Industries: {stats['unique_industries']}")
                
                print(f"\n🌍 Top Countries:")
                for country, weight in stats['top_countries'][:5]:
                    print(f"   {country}: {weight:.2f}%")
                
                print(f"\n🏭 Top Industries:")
                for industry, weight in stats['top_industries'][:5]:
                    print(f"   {industry}: {weight:.2f}%")
                
                return True
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False


async def main():
    """Run the integration test."""
    success = await test_processor()
    
    if success:
        print("\n🎉 Integration test PASSED")
        return 0
    else:
        print("\n💥 Integration test FAILED")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))