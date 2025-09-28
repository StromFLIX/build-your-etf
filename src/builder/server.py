#!/usr/bin/env python3
"""
Start the ETF Builder FastAPI server.

This script can be used to run the server locally or in production.
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add src directory to Python path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    # Check if database exists
    db_path = BASE_DIR / ".." / "etf_data.sqlite"  # Go up one more level
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        print("Please ensure the ETF data has been processed and the database exists.")
        sys.exit(1)
    
    # Check if ETF JSON exists
    json_path = BASE_DIR / ".." / "data" / "etfs.json"  # Go up one more level
    if not json_path.exists():
        print(f"Error: ETF JSON file not found at {json_path}")
        print("Please ensure the ETF data has been scraped and processed.")
        sys.exit(1)
    
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    print(f"Starting ETF Builder API server on {host}:{port}")
    print(f"Database: {db_path}")
    print(f"ETF Data: {json_path}")
    
    if workers > 1 and reload:
        print("Warning: Using multiple workers with reload=True, disabling reload")
        reload = False
    
    uvicorn.run(
        "src.builder.main:app",
        host=host,
        port=port,
        workers=workers if workers > 1 else None,
        reload=reload,
        log_level="info",
        app_dir=str(BASE_DIR.parent)  # Set the app directory to the project root
    )