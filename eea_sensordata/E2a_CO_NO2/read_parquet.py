# read_parquet_to_csv.py
import pandas as pd
import os

# Path to your Parquet file
parquet_file = "SPO-RO0197A_00020_100.parquet"

# Optional: output CSV file
csv_file = "converted_SPO-RO0197A_00020_100.csv"

# Step 1: Read the Parquet file
try:
    df = pd.read_parquet(parquet_file)
    print("✅ Parquet file loaded successfully!\n")
except Exception as e:
    print("❌ Error reading Parquet file:", e)
    exit()

# Step 2: Inspect schema and first few rows
print("Schema / columns:")
print(df.dtypes)
print("\nFirst 5 rows:")
print(df.head())

# Step 3: Convert to CSV
try:
    df.to_csv(csv_file, index=False)
    print(f"\n✅ CSV file saved as: {os.path.abspath(csv_file)}")
except Exception as e:
    print("❌ Error writing CSV file:", e)