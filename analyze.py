import argparse
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import os
import sys
from contextlib import redirect_stdout
import math

class CoinGeckoCSVData(bt.feeds.GenericCSVData):
    params = (
        ('dtformat', '%Y-%m-%d'),  # Date format in normalized files
        ('datetime', 0),     # date column
        ('open', 1),        # price
        ('high', 1),        # price (same as open)
        ('low', 1),         # price (same as open)
        ('close', 1),       # price column
        ('volume', 3),      # total_volume column
        ('openinterest', -1),
        ('marketcap', 2),   # market_cap column
    )
    lines = ('marketcap',)

    def __init__(self, **kwargs):
        super(CoinGeckoCSVData, self).__init__(**kwargs)
        self._debug = False

    def _loadline(self, linetokens):
        ret = super(CoinGeckoCSVData, self)._loadline(linetokens)
        if ret and self._debug:
            dt = bt.num2date(self.lines.datetime[0]).date()
            print(f"Date: {dt}, Open: {self.lines.open[0]}, Market Cap: {self.lines.marketcap[0]}")
        return ret

    def load(self):
        num_points = super(CoinGeckoCSVData, self).load()
        if self._debug:
            print(f"\nTotal loaded points: {num_points}")
            if num_points == 0:
                print("\nFirst 3 lines of file:")
                try:
                    with open(self.p.dataname, 'r') as f:
                        for i in range(3):
                            print(f.readline().strip())
                except Exception as e:
                    print(f"Error reading file: {e}")
        return num_points

class IndexComparisonStrategy(bt.Strategy):
    params = (
        ('rebalance_days', 30),
        ('min_allocation', 0.01),
        ('start_date', None),
        ('end_date', None),
        ('output_file', None),
    )
    
    def __init__(self):
        self.day_counter = 0
        self.assets = self.datas  # All data feeds are constituents
        
        # Convert dates to date objects
        if isinstance(self.p.start_date, str):
            self.start_date = date.fromisoformat(self.p.start_date)
        if isinstance(self.p.end_date, str):
            self.end_date = date.fromisoformat(self.p.end_date)
        
        # Track portfolio and individual asset values
        self.portfolio_value = []
        self.asset_values = {data._name: [] for data in self.assets}
        self.dates = []
        self.weights_history = {data._name: [] for data in self.assets}

    # def start(self):
    #     # Record initial portfolio value
    #     self.portfolio_value.append(self.broker.getvalue())

    def next(self):
        current_date = bt.num2date(self.data0.datetime[0]).date()
        
        # Skip if before start date or after end date
        if self.p.start_date and current_date < self.p.start_date:
            return
        if self.p.end_date and current_date > self.p.end_date:
            return
            
        self.day_counter += 1
        if self.day_counter % self.params.rebalance_days == 0:
            self.rebalance_portfolio()
        
        # Record daily values for comparison
        self.dates.append(current_date)
        self.portfolio_value.append(self.broker.getvalue())
        for data in self.assets:
            self.asset_values[data._name].append(data.close[0])

    def rebalance_portfolio(self):
        """Rebalance portfolio based on market cap weights."""
        # Get current date
        current_date = bt.num2date(self.data0.datetime[0]).date()
        
        # Skip if outside the specified date range
        if self.p.start_date and current_date < self.p.start_date:
            return
        if self.p.end_date and current_date > self.p.end_date:
            return

        # Get market caps for assets that exist on the current date
        market_caps = {}
        for data in self.datas:
            name = data._name
            if len(data) > 0 and not math.isnan(data.lines.marketcap[0]) and data.close[0] > 0:
                market_caps[name] = data.lines.marketcap[0]

        if not market_caps:
            return

        # Calculate weights based on market cap
        total_market_cap = sum(market_caps.values())
        weights = {name: cap / total_market_cap for name, cap in market_caps.items()}

        # Print rebalancing info
        print(f"\nRebalanced portfolio on {current_date}:")
        for name, weight in weights.items():
            print(f"  {name}: {weight:.2%}")

        # Record weights for plotting
        self.weights_history[current_date] = [(current_date, weight) for name, weight in weights.items()]

        # Execute trades to match target weights
        for data in self.datas:
            name = data._name
            if name in weights and data.close[0] > 0:  # Only trade if price is non-zero
                self.order_target_percent(data, target=weights[name])

    def stop(self):
        """Calculate and print performance metrics."""
        print("\n=== Performance Comparison ===")
        
        # Calculate index performance
        index_returns = np.diff(self.portfolio_value) / self.portfolio_value[:-1]
        total_return = (self.portfolio_value[-1] - self.portfolio_value[0]) / self.portfolio_value[0] * 100
        sharpe = np.sqrt(365) * index_returns.mean() / index_returns.std() if index_returns.std() > 0 else 0
        max_drawdown = (np.maximum.accumulate(self.portfolio_value) - self.portfolio_value).max() / np.maximum.accumulate(self.portfolio_value).max() * 100
        
        # Calculate constituents performance
        constituent_perf = {}
        for name, values in self.asset_values.items():
            # Skip assets that don't have any non-zero values
            if all(v == 0 for v in values):
                continue
                
            # Find first non-zero value as initial price
            initial_price = next((v for v in values if v > 0), None)
            if initial_price is None:
                continue
                
            # Calculate returns only for non-zero values
            non_zero_values = [v for v in values if v > 0]
            if len(non_zero_values) < 2:
                continue
                
            final_price = non_zero_values[-1]
            total_return_asset = (final_price - initial_price) / initial_price * 100
            
            # Calculate returns array for Sharpe ratio
            returns = np.diff(non_zero_values) / non_zero_values[:-1]
            sharpe_asset = np.sqrt(365) * returns.mean() / returns.std() if returns.std() > 0 else 0
            
            # Calculate max drawdown
            max_drawdown_asset = (np.maximum.accumulate(non_zero_values) - non_zero_values).max() / np.maximum.accumulate(non_zero_values).max() * 100
            
            constituent_perf[name] = {
                'return': total_return_asset,
                'sharpe': sharpe_asset,
                'drawdown': max_drawdown_asset
            }
        
        # Print comparison table
        print(f"{'Asset':<10} {'Return %':>10} {'Sharpe':>10} {'Max DD %':>10}")
        print(f"{'Index':<10} {total_return:>10.2f} {sharpe:>10.2f} {max_drawdown:>10.2f}")
        for name, perf in constituent_perf.items():
            print(f"{name:<10} {perf['return']:>10.2f} {perf['sharpe']:>10.2f} {perf['drawdown']:>10.2f}")

        # Write results to output file
        if self.p.output_file:
            values = [self.p.start_date.isoformat()] + [f"{total_return:.2f}"] + [f"{perf['return']:.2f}" for perf in constituent_perf.values()]
            print(",".join(values), file=self.p.output_file)

def run_strategy(data_files, start_date=None, end_date=None, output_file=None):
    """Run strategy and write output to file handle or stdout."""
    
    # Determine output destination
    output_dest = output_file if output_file else sys.stdout

    cerebro = bt.Cerebro()
    
    # Convert string dates to date objects if needed
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    
    # Add strategy with date range
    cerebro.addstrategy(
        IndexComparisonStrategy,
        start_date=start_date,
        end_date=end_date,
        output_file=output_dest 
    )
    
    # Load constituent data files
    for file in data_files:
        try:
            # Check if file exists
            if not file.exists():
                raise FileNotFoundError(f"File {file} not found")
                
            data = CoinGeckoCSVData(
                dataname=str(file.absolute()),  # Use absolute path
                timeframe=bt.TimeFrame.Days,
                compression=1
            )
            data._name = file.stem
            cerebro.adddata(data)
        except Exception as e:
            print(f"Failed to load {file}: {str(e)}")
            return
    
    # Set initial capital
    cerebro.broker.set_cash(1000000)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    # Run backtest
    print('\nStarting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Plot
    # cerebro.plot(style='candlestick')

def generate_date_strings(start_date, end_date):
    """Generate date strings between two dates (inclusive)"""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    
    current = start
    date_strings = []
    
    while current <= end:
        date_strings.append(current.isoformat())
        current += timedelta(days=1)
    
    return date_strings

def valid_date(date_string):
    """Validate date format YYYY-MM-DD"""
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_string}'. Expected format: YYYY-MM-DD")

if __name__ == '__main__':
    DEFAULT_START_INTERVAL0 = valid_date("2018-01-01")
    DEFAULT_START_INTERVAL1 = valid_date("2018-12-31")
    DEFAULT_END = valid_date("2024-12-31")
    DEFAULT_OUTPUT = "returns.csv"

    parser = argparse.ArgumentParser(description='Cryptocurrency analysis tool')
    parser.add_argument('--cryptos', nargs='+', default=['bitcoin', 'ethereum', 'cardano'],
                       help='List of cryptocurrencies to analyze (space-separated)')
    parser.add_argument('--start-interval', nargs=2, type=valid_date,
                   default=[DEFAULT_START_INTERVAL0, DEFAULT_START_INTERVAL1],
                   metavar=('START', 'END'),
                   help=f'Date range (default: {DEFAULT_START_INTERVAL0} to {DEFAULT_START_INTERVAL1})')
    parser.add_argument('--end-date', type=valid_date,
                      default=DEFAULT_END,
                      metavar='DATE',
                      help=f'Single end date (default: {DEFAULT_END})')
    parser.add_argument('--output', type=str,
                      default=DEFAULT_OUTPUT,
                      metavar='FILENAME',
                      help=f'Output filename (default: {DEFAULT_OUTPUT})')
    args = parser.parse_args()

    # Validate date ordering
    if args.start_interval and args.start_interval[0] > args.start_interval[1]:
        parser.error("Start date must be before end date")
    if args.start_interval[1] >= args.end_date:
            parser.error(f"start-interval end date ({args.start_interval[1]}) must be before --end-date ({args.end_date})")

    print(f"Analyzing cryptocurrencies: {args.cryptos}")

    data_dir = Path('data/normalized')
    data_files = [(data_dir / name).with_suffix('.csv') for name in args.cryptos]

    # Verify data directory exists
    if not data_dir.exists():
        print(f"\nERROR: Normalized data directory '{data_dir}' not found")
        print("Please run normalize_data.py first to create normalized data files")
        exit(1)
    
    # Generate dates between start and end of interval
    dates = []
    current_date = args.start_interval[0]
    while current_date <= args.start_interval[1]:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    with open(args.output, 'w') as f:
        # Write header
        header = f"market_entry,index,{','.join(args.cryptos)}\n"
        f.write(header)
        
        # Run strategy for each date
        for date in dates:
            run_strategy(data_files, date, args.end_date, f)

