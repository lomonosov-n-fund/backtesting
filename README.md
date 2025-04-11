# Backtesting indexing strategy vs buy-n-hold a single coin

## Analyze returns using backtesting

### Usage

`python analyze.py [-h] [--cryptos CRYPTOS [CRYPTOS ...]] [--start-interval START END] [--end-date DATE] [--output FILENAME]`

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
