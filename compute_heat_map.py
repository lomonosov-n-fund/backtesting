import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import sys
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Compare cryptocurrency returns against an index using a heatmap.')
    parser.add_argument('csv_file', help='Path to the CSV file containing market entry data')
    parser.add_argument('-a', '--annotate', action='store_true', 
                       help='Show numerical values in heatmap cells')
    args = parser.parse_args()

    try:
        data = pd.read_csv(args.csv_file, parse_dates=['market_entry'])
    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)

    data.set_index('market_entry', inplace=True)
    comparison = data.drop(columns=['index']).subtract(data['index'], axis=0)

    # Create colormap
    cmap = LinearSegmentedColormap.from_list(
        'custom_diverging',
        ['#d62728', '#ffffff', '#2ca02c'],
        N=256
    )

    # Calculate symmetric color bounds
    max_diff = comparison.abs().max().max()
    vmin, vmax = -max_diff, max_diff

    # Create figure
    plt.figure(figsize=(16, 8))
    
    # Plot heatmap with edgecolor matching fill color
    heatmap = sns.heatmap(
        comparison.T,
        cmap=cmap,
        center=0,
        annot=args.annotate,
        fmt=".1f",
        linewidths=0.5,
        linecolor='face',  # Critical change: edges match cell color
        vmin=vmin,
        vmax=vmax,
        cbar_kws={'label': 'Return Difference (Coin - Index)'},
        xticklabels=False
    )

    # Set optimal date labels
    num_dates = len(comparison.index)
    step = max(1, num_dates // 20)
    xticks_pos = range(0, num_dates, step)
    xticks_labels = [comparison.index[i].strftime('%Y-%m-%d') for i in xticks_pos]
    
    heatmap.set_xticks(xticks_pos)
    heatmap.set_xticklabels(xticks_labels, rotation=45, ha='right')

    plt.title(f'Cryptocurrency Returns vs Index{" (Values Shown)" if args.annotate else ""}')
    plt.xlabel('Market Entry Date')
    plt.ylabel('Cryptocurrency')
    plt.tight_layout()
    #plt.show()
    # Save to PNG file
    plt.savefig('crypto_returns_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()  # Important: close the figure to free memory

if __name__ == "__main__":
    main()
    