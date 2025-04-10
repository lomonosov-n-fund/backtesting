import csv
from statistics import mean

# Initialize data structures
data = []
headers = []

# Read the CSV file
with open('returns.csv', 'r') as csvfile:
    csvreader = csv.reader(csvfile)
    headers = next(csvreader)  # Get header row
    for row in csvreader:
        data.append(row)

# Prepare results
results = {}

# Process each asset (skip the first column which is the date)
for i in range(1, len(headers)):
    asset = headers[i]
    asset_data = []
    
    # Collect all returns for this asset
    for row in data:
        try:
            return_val = float(row[i])
            asset_data.append((row[0], return_val))  # (date, return)
        except ValueError:
            continue
    
    # (1) Find worst return with corresponding day
    worst_return = min(asset_data, key=lambda x: x[1])
    
    # (2) Calculate average return
    avg_return = mean([x[1] for x in asset_data])
    
    # (4) Calculate probability of negative return
    negative_returns = sum(1 for x in asset_data if x[1] < 0)
    prob_negative = negative_returns / len(asset_data)
    
    # Store results for this asset
    results[asset] = {
        'worst_return': worst_return,
        'average_return': avg_return,
        'prob_negative': prob_negative
    }

# (3) Calculate probability that return of a single coin is smaller than index
index_returns = [float(row[1]) for row in data]  # Index is the second column (after date)
coin_probabilities = {}

for coin in headers[2:]:  # Skip date and index columns
    coin_returns = [float(row[headers.index(coin)]) for row in data]
    count = sum(1 for c, i in zip(coin_returns, index_returns) if c < i)
    probability = count / len(index_returns)
    coin_probabilities[coin] = probability

# Print results
print("(1) Worst returns with corresponding days:")
for asset, res in results.items():
    print(f"{asset}: {res['worst_return'][1]}% on {res['worst_return'][0]}")

print("\n(2) Average returns:")
for asset, res in results.items():
    print(f"{asset}: {res['average_return']:.2f}%")

print("\n(3) Probability that return is smaller than index:")
for coin, prob in coin_probabilities.items():
    print(f"{coin}: {prob:.2%}")

print("\n(4) Probability of losing money (negative return):")
for asset, res in results.items():
    print(f"{asset}: {res['prob_negative']:.2%}")

# Example usage:
# Save the CSV data to a file named 'returns.csv' and run this script