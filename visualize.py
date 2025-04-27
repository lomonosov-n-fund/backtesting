import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from matplotlib.colors import LinearSegmentedColormap

def main():
    # Argument parsing (unchanged)
    parser = argparse.ArgumentParser(description='Compare cryptocurrency returns against an index using a heatmap.')
    parser.add_argument('--input', default="returns.csv", help='Path to the CSV file containing analysis data (default: returns.csv)')
    parser.add_argument('--output', help='Path to save the output image (optional, show image if undefined)')
    parser.add_argument('-a', '--annotate', action='store_true', help='Show numerical values in heatmap cells')
    args = parser.parse_args()

    try:
        data = pd.read_csv(args.input, parse_dates=['market_entry'])
    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)

    data.set_index('market_entry', inplace=True)
    comparison = data.drop(columns=['index']).subtract(data['index'], axis=0)

    # Visualization setup
    cmap = LinearSegmentedColormap.from_list('custom_diverging', ['#d62728', '#ffffff', '#2ca02c'], N=256)
    max_diff = comparison.abs().max().max()
    vmin, vmax = -max_diff, max_diff

    FONT_SIZE = 14
    CELL_HEIGHT_RATIO = 4
    n_cryptos = len(comparison.columns)
    fig_height = (FONT_SIZE * CELL_HEIGHT_RATIO * n_cryptos) / 72

    fig, ax = plt.subplots(figsize=(16, fig_height))
    
    # Create heatmap and pass the ax explicitly
    heatmap = sns.heatmap(
        comparison.T,
        cmap=cmap,
        center=0,
        annot=args.annotate,
        fmt=".1f",
        linewidths=0.5,
        linecolor='face',
        vmin=vmin,
        vmax=vmax,
        # cbar_kws={'label': 'Return Difference (Coin - Index)'},
        xticklabels=False,  # Disable automatic x-tick labels
        yticklabels=True,
        ax=ax  # Use our pre-created axes
    )

    # Set custom x-axis labels
    num_dates = len(comparison.index)
    step = max(1, num_dates // 20)
    xticks_pos = range(0, num_dates, step)
    xticks_labels = [comparison.index[i].strftime('%Y-%m-%d') for i in xticks_pos]
    
    ax.set_xticks([x + 0.5 for x in xticks_pos])  # Add 0.5 to center labels
    ax.set_xticklabels(xticks_labels, rotation=45, ha='right', fontsize=FONT_SIZE)
    
    # Y-axis settings
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=FONT_SIZE)
    
    # ax.set_title(f'Cryptocurrency Returns vs Index, %', fontsize=FONT_SIZE+2)
    ax.set_title(f'Разница в возврате крипто-индекс, %', fontsize=FONT_SIZE+2)
    # ax.set_xlabel('Market Entry Date', fontsize=FONT_SIZE)
    ax.set_xlabel('Дата входа на рынок', fontsize=FONT_SIZE+2)
    # ax.set_ylabel('Cryptocurrency', fontsize=FONT_SIZE)

    # Colorbar settings
    cbar = heatmap.collections[0].colorbar
    cbar.ax.tick_params(labelsize=FONT_SIZE)
    cbar.ax.yaxis.label.set_size(FONT_SIZE)

    plt.tight_layout()
    if args.output:
        output_path = args.output if args.output.endswith('.png') else f"{args.output}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

if __name__ == "__main__":
    main()