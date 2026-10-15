import os
import pandas as pd

# ==========================================
# 0. SETUP
# ==========================================
PARQUET_PATH = "data/taxi_zones (1).json"
LOOKUP_PATH = "data/taxi_zone_lookup.csv"


def main():
  # ==========================================
  # 1. LOAD
  # ==========================================
  print("=" * 40)
  print("1. LOADING DATA")
  print("=" * 40)

  df = pd.read_parquet(PARQUET_PATH)
  print(f"Dataset Shape: {df.shape[0]:,} rows, {df.shape[1]} columns")
  print("\nFirst few rows:")
  display_cols = [
      c
      for c in [
          "tpep_pickup_datetime",
          "tpep_dropoff_datetime",
          "trip_distance",
          "fare_amount",
          "total_amount",
      ]
      if c in df.columns
  ]
  print(df[display_cols].head())

  # ==========================================
  # 2. STRUCTURE AND MISSING DATA
  # ==========================================
  print("\n" + "=" * 40)
  print("2. STRUCTURE AND MISSING DATA")
  print("=" * 40)

  print("Column Types:")
  print(df.dtypes)

  print("\nNull Counts per Column:")
  null_counts = df.isnull().sum()
  print(null_counts[null_counts > 0])
  if null_counts.sum() == 0:
    print("No missing values found.")

  duplicates = df.duplicated().sum()
  print(f"\nNumber of duplicate rows: {duplicates:,}")

  # ==========================================
  # 3. NUMERIC RANGES
  # ==========================================
  print("\n" + "=" * 40)
  print("3. NUMERIC RANGES")
  print("=" * 40)

  numeric_cols = [
      "trip_distance",
      "fare_amount",
      "tip_amount",
      "total_amount",
      "passenger_count",
  ]
  existing_numeric = [c for c in numeric_cols if c in df.columns]

  print("Summary Statistics:")
  print(df[existing_numeric].describe())

  # Suspicious row counts
  susp_dist = (
      (df["trip_distance"] <= 0).sum() if "trip_distance" in df.columns else 0
  )
  susp_fare = (
      (df["fare_amount"] <= 0).sum() if "fare_amount" in df.columns else 0
  )
  susp_pass = (
      (df["passenger_count"] == 0).sum() if "passenger_count" in df.columns else 0
  )

  print(f"\nSuspicious Rows:")
  print(f"- Distance <= 0: {susp_dist:,}")
  print(f"- Fare <= 0: {susp_fare:,}")
  print(f"- Passenger count == 0: {susp_pass:,}")

  if "trip_distance" in df.columns:
    print(f"\nLargest distance: {df['trip_distance'].max():,.2f}")
  if "total_amount" in df.columns:
    print(f"Largest total amount: ${df['total_amount'].max():,.2f}")

  # ==========================================
  # 4. TIME CHECKS
  # ==========================================
  print("\n" + "=" * 40)
  print("4. TIME CHECKS")
  print("=" * 40)

  pickup_col = "tpep_pickup_datetime"
  dropoff_col = "tpep_dropoff_datetime"

  if pickup_col in df.columns and dropoff_col in df.columns:
    print(f"Earliest Pickup: {df[pickup_col].min()}")
    print(f"Latest Pickup:   {df[pickup_col].max()}")
    print(f"Earliest Dropoff: {df[dropoff_col].min()}")
    print(f"Latest Dropoff:   {df[dropoff_col].max()}")

    invalid_times = (df[dropoff_col] <= df[pickup_col]).sum()
    print(f"\nRows where dropoff is not after pickup: {invalid_times:,}")

    # Determine expected month from the most frequent month in pickups
    expected_month = df[pickup_col].dt.month.mode()[0]
    outside_month = (df[pickup_col].dt.month != expected_month).sum()
    print(
        f"Rows with pickups outside expected month ({expected_month}):"
        f" {outside_month:,}"
    )

    # Temporary trip duration in minutes
    trip_duration = (
        df[dropoff_col] - df[pickup_col]
    ).dt.total_seconds() / 60.0
    print("\nTemporary Trip Duration Summary Stats (minutes):")
    print(trip_duration.describe())
  else:
    print("Pickup/Dropoff datetime columns not found.")

  # ==========================================
  # 5. CATEGORIES AND ZONES
  # ==========================================
  print("\n" + "=" * 40)
  print("5. CATEGORIES AND ZONES")
  print("=" * 40)

  cat_cols = ["RatecodeID", "payment_type", "VendorID", "store_and_fwd_flag"]
  for col in cat_cols:
    if col in df.columns:
      print(f"\nValue Counts for {col}:")
      print(df[col].value_counts(dropna=False))

  if os.path.exists(LOOKUP_PATH) and "PULocationID" in df.columns:
    lookup_df = pd.read_csv(LOOKUP_PATH)
    zone_ids = set(lookup_df["LocationID"])

    missing_pu = ~df["PULocationID"].isin(zone_ids)
    missing_do = (
        ~df["DOLocationID"].isin(zone_ids)
        if "DOLocationID" in df.columns
        else pd.Series(False, index=df.index)
    )
    invalid_zones = (missing_pu | missing_do).sum()
    print(
        "\nTrips whose pickup or dropoff zone ID is missing from lookup:"
        f" {invalid_zones:,}"
    )
  else:
    print(
        "\nLookup CSV not found or location columns missing; skipping zone check."
    )

  # ==========================================
  # 6. SAMPLE
  # ==========================================
  print("\n" + "=" * 40)
  print("6. SAMPLE GENERATION")
  print("=" * 40)

  os.makedirs("data", exist_ok=True)
  sample_size = min(200_000, len(df))
  sample_df = df.sample(n=sample_size, random_state=42)

  sample_output_path = "data/trip_sample.parquet"
  sample_df.to_parquet(sample_output_path)
  print(
      f"Successfully saved random sample of {sample_size:,} rows to"
      f" {sample_output_path}"
  )

if __name__ == "__main__":
  main()