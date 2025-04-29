#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import sys
import shutil

def valid_date(date_string):
    """Validate date format YYYY-MM-DD"""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_string}'. Expected format: YYYY-MM-DD")

def setup_directories(data_dir):
    """Create normalized directory if it doesn't exist."""
    data_dir = Path(data_dir)
    raw_dir = data_dir / 'raw'
    normalized_dir = data_dir / 'normalized'
    
    # Verify raw directory exists
    if not raw_dir.exists():
        print(f"Error: Raw directory '{raw_dir}' not found")
        sys.exit(1)
    
    # Create normalized directory if it doesn't exist
    normalized_dir.mkdir(exist_ok=True)
    
    return raw_dir, normalized_dir

def normalize_data(raw_dir, normalized_dir, start_date):
    """Create normalized versions of CSV files, adding zero values when needed."""
    for csv_file in raw_dir.glob("*.csv"):
        print(f"\nProcessing {csv_file.name}...")
        
        # Read the first line to get the first date
        with open(csv_file, 'r') as f:
            header = f.readline()
            first_data_line = f.readline()
            if not first_data_line:
                print(f"  Warning: File {csv_file.name} is empty")
                continue
                
            first_date_str = first_data_line.split(',')[0]
            first_date = datetime.strptime(first_date_str, "%Y-%m-%d %H:%M:%S UTC").date()
            
            if first_date <= start_date:
                # If file starts before or at start_date, just copy it
                output_file = normalized_dir / csv_file.name
                shutil.copy2(csv_file, output_file)
                print(f"  Copied file as is (first date {first_date} is before or at start date {start_date})")
                continue
            
            # Generate dates between start_date and first_date
            dates = []
            current_date = start_date
            while current_date < first_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
            
            if not dates:
                print("  No dates to add")
                continue
            
            # Create DataFrame with zero values
            zero_data = pd.DataFrame({
                'snapped_at': [f"{date} 00:00:00 UTC" for date in dates],
                'price': [0.0] * len(dates),
                'market_cap': [0.0] * len(dates),
                'total_volume': [0.0] * len(dates)
            })
            
            # Read existing data
            existing_data = pd.read_csv(csv_file)
            
            # Combine and write to normalized directory
            combined_data = pd.concat([zero_data, existing_data], ignore_index=True)
            output_file = normalized_dir / csv_file.name
            combined_data.to_csv(output_file, index=False)
            
            print(f"  Created normalized version with {len(dates)} days of zero values from {start_date} to {first_date - timedelta(days=1)}")

def main():
    parser = argparse.ArgumentParser(description='Normalize historical data by adding zero values for dates before first recorded data point.')
    parser.add_argument('--start-date', type=valid_date, required=True,
                      help='Start date in YYYY-MM-DD format')
    parser.add_argument('--data-dir', type=str, default='data',
                      help='Directory containing raw and normalized subdirectories (default: data)')
    
    args = parser.parse_args()
    
    # Setup directories
    raw_dir, normalized_dir = setup_directories(args.data_dir)
    
    # Create normalized versions
    normalize_data(raw_dir, normalized_dir, args.start_date)

if __name__ == '__main__':
    main() 