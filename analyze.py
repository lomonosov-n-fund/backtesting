import argparse
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
from contextlib import redirect_stdout
import math

class CoinGeckoCSVData(bt.feeds.GenericCSVData):
    params = (
        ('dtformat', '%Y-%m-%d %H:%M:%S UTC'),
        ('datetime', 0),     # snapped_at column
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
        self._loaded_lines = 0

    def _loadline(self, linetokens):
        ret = super(CoinGeckoCSVData, self)._loadline(linetokens)
        if ret:
            self._loaded_lines += 1
            if self._debug and self._loaded_lines <= 5:
                dt = bt.num2date(self.lines.datetime[0])
                print(f"\nLine {self._loaded_lines}:")
                print(f"  Date: {dt}")
                print(f"  Open: {self.lines.open[0]}")
                print(f"  Market Cap: {self.lines.marketcap[0]}")
        return ret

    def load(self):
        self._loaded_lines = 0
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
        
        # Convert dates to datetime objects
        if isinstance(self.p.start_date, str):
            self.start_date = datetime.strptime(self.p.start_date, '%Y-%m-%d')
        if isinstance(self.p.end_date, str):
            self.end_date = datetime.strptime(self.p.end_date, '%Y-%m-%d')
        
        # Track portfolio and individual asset values
        self.portfolio_value = []
        self.asset_values = {data._name: [] for data in self.assets}
        self.dates = []
        self.weights_history = {data._name: [] for data in self.assets}

    # def start(self):
    #     # Record initial portfolio value
    #     self.portfolio_value.append(self.broker.getvalue())

    def next(self):
        current_dt = bt.num2date(self.data0.datetime[0])
        
        # Skip if before start date or after end date
        if self.p.start_date and current_dt < self.p.start_date:
            return
        if self.p.end_date and current_dt > self.p.end_date:
            return
            
        self.day_counter += 1
        if self.day_counter % self.params.rebalance_days == 0:
            self.rebalance_portfolio()
        
        # Record daily values for comparison
        self.dates.append(current_dt)
        self.portfolio_value.append(self.broker.getvalue())
        for data in self.assets:
            self.asset_values[data._name].append(data.close[0])

    def rebalance_portfolio(self):
        """Rebalance portfolio based on market cap weights."""
        # Get current date
        current_date = self.data.datetime.date(0)
        
        # Skip if outside the specified date range
        if self.p.start_date and current_date < self.p.start_date.date():
            return
        if self.p.end_date and current_date > self.p.end_date.date():
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
            values = [self.p.start_date.strftime('%Y-%m-%d')] + [f"{total_return:.2f}"] + [f"{perf['return']:.2f}" for perf in constituent_perf.values()]
            print(",".join(values), file=self.p.output_file)

    def plot_comparison(self):
        plt.style.use('ggplot')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Normalize all prices to starting value of 100
        norm_index = [100 * x / self.portfolio_value[0] for x in self.portfolio_value]
        ax1.plot(self.dates, norm_index, label='Index', linewidth=2.5)
        
        # Plot constituents
        for name, values in self.asset_values.items():
            norm_values = [100 * x / values[0] for x in values]
            ax1.plot(self.dates, norm_values, label=name, alpha=0.7)
        
        ax1.set_title('Performance Comparison: Index vs Constituents')
        ax1.set_ylabel('Normalized Value (Start=100)')
        ax1.legend()
        ax1.grid(True)
        
        # Plot weights evolution
        for name, weights in self.weights_history.items():
            dates = [x[0] for x in weights]
            values = [x[1]*100 for x in weights]
            ax2.plot(dates, values, label=name, alpha=0.7)
        
        ax2.set_title('Asset Weights Evolution')
        ax2.set_ylabel('Weight (%)')
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()

def run_strategy(data_files, start_date=None, end_date=None, output_file=None):
    """Run strategy and write output to file handle or stdout."""
    
    # Determine output destination
    output_dest = output_file if output_file else sys.stdout

    cerebro = bt.Cerebro()
    
    # Convert string dates to datetime objects
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
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
            # print(f"Added data feed for {data._name} from {file}")
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
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    current = start
    date_strings = []
    
    while current <= end:
        date_strings.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return date_strings

def valid_date(date_string):
    """Validate date format YYYY-MM-DD"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
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
    
    # Set dates (YYYY-MM-DD format)
    start0_date = args.start_interval[0].strftime('%Y-%m-%d')
    start1_date = args.start_interval[1].strftime('%Y-%m-%d')
    end_date = args.end_date.strftime('%Y-%m-%d')
    
    dates = generate_date_strings(start0_date, start1_date)
    with open(args.output, 'w') as f:
        # Write header
        header = f"market_entry,index,{','.join(args.cryptos)}\n"
        f.write(header)
        
        # Run strategy for each date
        for date in dates:
            run_strategy(data_files, date, end_date, f)

