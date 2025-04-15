# Backtesting indexing strategy vs buy-n-hold a single coin

## Strategy Overview

The backtesting system implements a market-cap weighted indexing strategy that:
1. Rebalances the portfolio every 30 days
2. Allocates assets based on their market capitalization
3. Implements a minimum allocation threshold of 1% per asset
4. Automatically adjusts weights to maintain market-cap proportions

### Key Features

- **Market-Cap Weighting**: Assets are weighted according to their market capitalization, giving larger cryptocurrencies more influence in the portfolio
- **Regular Rebalancing**: Portfolio is rebalanced every 30 days to maintain target weights
- **Minimum Allocation**: Each asset is guaranteed at least 1% allocation to ensure diversification
- **Dynamic Adjustments**: Weights are automatically adjusted to account for market cap changes
- **Performance Tracking**: System tracks and compares:
  - Total returns
  - Sharpe ratio
  - Maximum drawdown
  - Individual asset performance

## Data Preparation

The backtesting system uses historical cryptocurrency data from CoinGecko. Here's how to prepare the data:

1. **Download Historical Data**:
   - Visit CoinGecko's historical data page for each cryptocurrency (e.g., https://www.coingecko.com/en/coins/bitcoin/historical_data)
   - Download the CSV file

2. **Required Data Format**:
   The CSV file should contain the following columns:
   - `snapped_at`: Timestamp in UTC
   - `price`: Price in USD
   - `market_cap`: Market capitalization in USD
   - `total_volume`: 24-hour trading volume in USD

3. **File Organization**:
   - Place downloaded CSV files in the `data` directory
   - Name files using the cryptocurrency's symbol (e.g., `bitcoin.csv`, `ethereum.csv`)

## Analyze returns using backtesting

### Usage

`python analyze.py [-h] [--cryptos CRYPTO [CRYPTO ...]] [--start-interval START END] [--end-date DATE] [--output FILENAME]`

### Optional arguments

- `-h, --help`  show help message and exit
- `--cryptos CRYPTO [CRYPTO ...]` list of cryptocurrencies to analyze (space-separated)
- `--start-interval START END` date range (default: 2018-01-01 to 2018-12-31)
- `--end-date DATE` single end date (default: 2024-12-31)
- `--output FILENAME` output filename (default: returns.csv)

### Examples

run with default parameters

```sh
python analyze.py
```

## Visualize analysis: plot a Heat Map

### Usage

`python visualize.py [-h] [--input FILENAME]`

### Optional arguments:

- `-h, --help`  show help message and exit
- `--input FILENAME` input CSV filename (default: returns.csv)
- `--output FILENAME`  path to save the output PNG image (show image if undefined)
- `-a, --annotate`  show numerical values in heatmap cells

### Examples

run with default arguments

`python visualize.py`

## Quantify analysis: compute different statistics

### Usage

`python quantify.py [-h] [--input FILENAME]`

### Optional Arguments

- `-h, --help`  show help message and exit
- `--input FILENAME` input CSV filename (default: returns.csv)

### Examples

run with default arguments

```sh
python quantify.py
```
