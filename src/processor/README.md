# ETF Data Processor

A modern, async Python processor for iShares ETF data that builds a SQLite database with country and industry distributions.

## Features

- **Async Processing**: Uses asyncio and aiosqlite for efficient concurrent processing
- **XML Parsing**: Handles iShares Excel XML format files (.xls)
- **Country & Industry Distributions**: Extracts and aggregates holdings by geographic and sector allocation
- **SQLite Database**: Stores processed data in a structured, queryable format
- **Query Tools**: Interactive tools for exploring the data

## Database Schema

### Tables

- **etfs**: Basic ETF information (id, name, inception_date, etc.)
- **country_distributions**: Country-wise allocation percentages for each ETF
- **industry_distributions**: Industry/sector allocation percentages for each ETF

## Usage

### Process ETF Files

```bash
# Process all ETF files in data/etf directory
uv run python -m src.processor

# Process files from custom directory
uv run python -m src.processor /path/to/etf/files

# Process with custom database path
uv run python -m src.processor data/etf custom_database.sqlite

# Verbose processing
uv run python -m src.processor --verbose
```

### Query Existing Database

```bash
# Show database statistics
uv run python -m src.processor --query stats

# List all processed ETFs
uv run python -m src.processor --query etfs

# Show top countries
uv run python -m src.processor --query countries

# Show top industries
uv run python -m src.processor --query industries
```

### Interactive Query Tool

```bash
uv run python src/processor/query_tool.py interactive
```

Interactive commands:
- `list` - List all ETFs
- `show <etf_id>` - Show distribution for specific ETF
- `country <name>` - Find ETFs with exposure to country
- `industry <name>` - Find ETFs with exposure to industry
- `compare <etf1> <etf2>` - Compare two ETFs
- `coverage` - Show coverage matrix
- `quit` - Exit

## Example Output

```
Processing complete! Database saved to: etf_data.sqlite

Database Statistics:
  Total ETFs: 4
  Unique Countries: 49
  Unique Industries: 12

MSCI World ETF (251882) - Top 10 Countries:
  Vereinigte Staaten         72.46%
  Japan                       5.50%
  Vereinigtes Königreich      3.57%
  Kanada                      3.28%
  Frankreich                  2.63%
```

## File Format

The processor expects iShares ETF data files in Excel XML format (.xls), typically containing:
- **Positionen** worksheet with holdings data
- Columns for: Symbol, Company Name, Sector, Asset Type, Market Value, Weight, Country, etc.

## Architecture

- **ETFProcessor**: Main async processor class
- **ETFHolding**: Data class for individual holdings
- **ETFDistribution**: Data class for aggregated distributions
- **ThreadPoolExecutor**: For CPU-intensive XML parsing
- **aiosqlite**: For async database operations

## Dependencies

- aiosqlite: Async SQLite operations
- pandas: Data processing (optional, for enhanced querying)
- xml.etree.ElementTree: XML parsing
- asyncio: Async processing
- aiofiles: Async file operations

## Error Handling

The processor handles common issues:
- Malformed XML (unescaped ampersands, etc.)
- Missing worksheets or data
- Invalid numeric values
- File encoding issues (BOM handling)

## Performance

- Concurrent processing of multiple ETF files
- Efficient memory usage with streaming
- Optimized database operations with proper indexing
- Thread pool for CPU-intensive XML parsing

## Future Enhancements

- Support for additional ETF providers
- Real-time data updates
- Advanced querying and filtering
- Data visualization integration
- RESTful API for web access