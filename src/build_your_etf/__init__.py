def main() -> None:
    """Main entry point for the build-your-etf CLI."""
    import sys
    import asyncio
    from pathlib import Path
    
    # Check if we should run the processor
    if len(sys.argv) > 1 and sys.argv[1] == "process":
        # Add processor module to path
        processor_path = Path(__file__).parent.parent / "processor"
        if processor_path.exists():
            sys.path.insert(0, str(processor_path.parent))
            from processor import main as processor_main
            # Remove the 'process' argument
            sys.argv.pop(1)
            asyncio.run(processor_main())
        else:
            print("Processor module not found!")
            sys.exit(1)
    else:
        print("Build Your ETF - Portfolio Construction Platform")
        print("Usage:")
        print("  build-your-etf process [data_dir] [db_path]  - Process ETF data")
        print("  build-your-etf --help                       - Show help")
