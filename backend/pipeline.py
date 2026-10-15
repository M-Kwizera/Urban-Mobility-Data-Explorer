import os
import sqlite3
import pandas as pd
import numpy as np

# ==========================================
# 0. CONFIGURATION & CONSTANTS
# ==========================================
PARQUET_PATH = "data/trip_sample.parquet"  # Switch to full month parquet when ready
LOOKUP_PATH = "data/taxi_zone_lookup.csv"
DB_PATH = "db/taxi.db"
SCHEMA_PATH = "db/schema.sql"
LOG_PATH = "logs/excluded_records.csv"

# Cleaning Thresholds (per cleaning_rules.md)
MAX_SPEED_MPH = 80.0
MAX_DURATION_MINUTES = 300.0  # 5 hours max normal urban trip limit
MAX_TIP_PERCENTAGE = 100.0  # 100% tip ceiling


def init_database():
  """Rebuilds the SQLite database from schema.sql to ensure re-runnability."""
  print("Initializing database from schema.sql...")
  os.makedirs("db", exist_ok=True)
  os.makedirs("logs", exist_ok=True)

  if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

  conn = sqlite3.connect(DB_PATH)
  # Enable foreign keys explicitly for SQLite connection
  conn.execute("PRAGMA foreign_keys = ON;")

  with open("db/schema.sql", "r", encoding="utf-8") as f:
    schema_sql = f.read()

  conn.executescript(schema_sql)
  conn.close()
  print("Database initialized successfully.")


# ==========================================
# 1. STAGE 1: LOAD DIMENSION TABLES
# ==========================================
def load_dimensions(conn):
  print("\n--- Stage 1: Loading Dimension Tables ---")

  # 1. Zones lookup
  if os.path.exists(LOOKUP_PATH):
    zones_df = pd.read_csv(LOOKUP_PATH)
    # Rename columns to match schema if necessary
    zones_df.columns = [c.strip().lower() for c in zones_df.columns]
    # Expected columns: locationid, borough, zone, service_zone
    zones_df.to_sql("zones", conn, if_exists="append", index=False)
    print(f"Loaded {len(zones_df)} zones into 'zones'.")
  else:
    print(f"Warning: Zone lookup file not found at {LOOKUP_PATH}")

  # 2. Rate Codes (TLC Data Dictionary reference values)
  rate_codes_data = [
      (1, "Standard rate"),
      (2, "JFK"),
      (3, "Newark"),
      (4, "Nassau or Westchester"),
      (5, "Negotiated fare"),
      (6, "Group ride"),
  ]
  conn.executemany(
      "INSERT OR IGNORE INTO rate_codes (rate_code_id, description) VALUES"
      " (?, ?)",
      rate_codes_data,
  )
  print(f"Loaded {len(rate_codes_data)} rate codes.")

  # 3. Payment Types (TLC Data Dictionary reference values)
  payment_types_data = [
      (1, "Credit card"),
      (2, "Cash"),
      (3, "No charge"),
      (4, "Dispute"),
      (5, "Unknown"),
      (6, "Voided"),
  ]
  conn.executemany(
      "INSERT OR IGNORE INTO payment_types (payment_type_id, description)"
      " VALUES (?, ?)",
      payment_types_data,
  )
  print(f"Loaded {len(payment_types_data)} payment types.")
  conn.commit()


# ==========================================
# 2 & 3. STAGES 2 & 3: CLEAN & DERIVE TRIPS
# ==========================================
def clean_and_derive_trips(df):
  print("\n--- Stages 2 & 3: Cleaning & Deriving Features ---")
  initial_count = len(df)
  print(f"Initial raw rows: {initial_count:,}")

  # Track exclusion reasons mutually exclusively
  exclusion_records = []

  def tag_dropped(subset_indices, rule_name, sample_val_col=None):
    if len(subset_indices) > 0:
      for idx in subset_indices:
        val = df.loc[idx, sample_val_col] if sample_val_col else None
        exclusion_records.append({
            "original_index": idx,
            "rule": rule_name,
            "offending_value": str(val),
        })

  # Work on a copy
  work_df = df.copy()

  # Create tracking column for remaining valid rows
  work_df["is_valid"] = True

  # Rule 1: Missing values in core columns
  core_cols = [
      "tpep_pickup_datetime",
      "tpep_dropoff_datetime",
      "trip_distance",
      "fare_amount",
      "passenger_count",
  ]
  null_mask = work_df[core_cols].isnull().any(axis=1) & work_df["is_valid"]
  null_indices = work_df[null_mask].index
  tag_dropped(null_indices, "Missing Core Values")
  work_df.loc[null_indices, "is_valid"] = False

  # Rule 2: Duplicates
  dup_mask = work_df.duplicated() & work_df["is_valid"]
  dup_indices = work_df[dup_mask].index
  tag_dropped(dup_indices, "Duplicate Row")
  work_df.loc[dup_indices, "is_valid"] = False

  # Rule 3: Time order (dropoff must be after pickup)
  time_mask = (
      (
          work_df["tpep_dropoff_datetime"]
          <= work_df["tpep_pickup_datetime"]
      )
      & work_df["is_valid"]
  )
  time_indices = work_df[time_mask].index
  tag_dropped(time_indices, "Invalid Time Order", "tpep_dropoff_datetime")
  work_df.loc[time_indices, "is_valid"] = False

  # Rule 4: Distance <= 0
  dist_mask = (work_df["trip_distance"] <= 0) & work_df["is_valid"]
  dist_indices = work_df[dist_mask].index
  tag_dropped(dist_indices, "Distance <= 0", "trip_distance")
  work_df.loc[dist_indices, "is_valid"] = False

  # --- DERIVE FEATURES FOR SURVIVING ROWS ---
  valid_idx = work_df["is_valid"]

  # Timestamps & Hour
  work_df.loc[valid_idx, "pickup_datetime"] = pd.to_datetime(
      work_df.loc[valid_idx, "tpep_pickup_datetime"]
  )
  work_df.loc[valid_idx, "dropoff_datetime"] = pd.to_datetime(
      work_df.loc[valid_idx, "tpep_dropoff_datetime"]
  )
  work_df.loc[valid_idx, "pickup_hour"] = work_df.loc[
      valid_idx, "pickup_datetime"
  ].dt.hour

  # Duration in minutes
  work_df.loc[valid_idx, "duration_minutes"] = (
      work_df.loc[valid_idx, "dropoff_datetime"]
      - work_df.loc[valid_idx, "pickup_datetime"]
  ).dt.total_seconds() / 60.0

  # Average Speed in MPH
  # Avoid division by zero by ensuring duration > 0 first
  duration_hours = work_df.loc[valid_idx, "duration_minutes"] / 60.0
  work_df.loc[valid_idx, "average_speed_mph"] = np.where(
      duration_hours > 0,
      work_df.loc[valid_idx, "trip_distance"] / duration_hours,
      0.0,
  )

  # Tip Percentage (Computed ONLY for credit card payments: payment_type == 1)
  # Tip amount / fare amount * 100
  work_df.loc[valid_idx, "tip_percentage"] = np.where(
      (work_df.loc[valid_idx, "payment_type"] == 1)
      & (work_df.loc[valid_idx, "fare_amount"] > 0),
      (
          work_df.loc[valid_idx, "tip_amount"]
          / work_df.loc[valid_idx, "fare_amount"]
      )
      * 100.0,
      0.0,
  )

  # --- RULES DEPENDING ON DERIVED VALUES ---

  # Rule 5: Invalid Duration (<= 0 or > MAX_DURATION_MINUTES)
  dur_mask = (
      (
          (work_df["duration_minutes"] <= 0)
          | (work_df["duration_minutes"] > MAX_DURATION_MINUTES)
      )
      & work_df["is_valid"]
  )
  dur_indices = work_df[dur_mask].index
  tag_dropped(dur_indices, "Invalid Duration", "duration_minutes")
  work_df.loc[dur_indices, "is_valid"] = False

  # Rule 6: Speed Ceiling Exceeded
  speed_mask = (
      (work_df["average_speed_mph"] > MAX_SPEED_MPH) & work_df["is_valid"]
  )
  speed_indices = work_df[speed_mask].index
  tag_dropped(speed_indices, "Speed Ceiling Exceeded", "average_speed_mph")
  work_df.loc[speed_indices, "is_valid"] = False

  # Rule 7: Tip Percentage Cap Exceeded
  tip_mask = (
      (work_df["tip_percentage"] > MAX_TIP_PERCENTAGE) & work_df["is_valid"]
  )
  tip_indices = work_df[tip_mask].index
  tag_dropped(tip_indices, "Tip Percentage Exceeded Cap", "tip_percentage")
  work_df.loc[tip_indices, "is_valid"] = False

  # Filter final cleaned DataFrame
  cleaned_df = work_df[work_df["is_valid"]].copy()

  # Create exclusion log DataFrame
  exclusion_log_df = pd.DataFrame(exclusion_records)

  return cleaned_df, exclusion_log_df, initial_count


# ==========================================
# 4. STAGE 4: WRITE EXCLUSION LOG & SUMMARY
# ==========================================
def save_exclusion_log(exclusion_log_df, initial_count, final_count):
  print("\n--- Stage 4: Exclusion Log & Summary ---")
  os.makedirs("logs", exist_ok=True)
  exclusion_log_df.to_csv(LOG_PATH, index=False)
  print(f"Exclusion log saved to {LOG_PATH} ({len(exclusion_log_df):,} rows).")

  print("\nCleaning Summary Report:")
  print("=" * 40)
  print(f"Rows Before Cleaning:   {initial_count:,}")

  if not exclusion_log_df.empty:
    summary_counts = exclusion_log_df["rule"].value_counts()
    for rule, count in summary_counts.items():
      print(f"- Removed ({rule}): {count:,}")
  else:
    print("No records excluded.")

  total_removed = len(exclusion_log_df)
  print(f"Total Rows Removed:     {total_removed:,}")
  print(f"Rows After Cleaning:    {final_count:,}")
  print("=" * 40)


# ==========================================
# 5. STAGE 5: BATCH LOAD INTO SQLITE
# ==========================================
def load_trips_to_db(cleaned_df):
  print("\n--- Stage 5: Loading Cleaned Trips into SQLite ---")
  conn = sqlite3.connect(DB_PATH)
  conn.execute("PRAGMA foreign_keys = ON;")

  # Map DataFrame columns to schema columns
  # Adjust column names according to dataset naming conventions (e.g. PULocationID -> pickup_location_id)
  column_mapping = {
      "tpep_pickup_datetime": "pickup_datetime",
      "tpep_dropoff_datetime": "dropoff_datetime",
      "PULocationID": "pickup_location_id",
      "DOLocationID": "dropoff_location_id",
      "RatecodeID": "rate_code_id",
      "payment_type": "payment_type_id",
      "passenger_count": "passenger_count",
      "trip_distance": "trip_distance",
      "fare_amount": "fare_amount",
      "tip_amount": "tip_amount",
      "total_amount": "total_amount",
      "duration_minutes": "duration_minutes",
      "average_speed_mph": "average_speed_mph",
      "tip_percentage": "tip_percentage",
      "pickup_hour": "pickup_hour",
  }

  # Select and rename columns present in cleaned_df
  load_cols = {
      k: v for k, v in column_mapping.items() if k in cleaned_df.columns
  }
  db_df = cleaned_df[list(load_cols.keys())].rename(columns=load_cols)

  # Insert in batches using transactions
  batch_size = 50_000
  total_rows = len(db_df)
  print(f"Inserting {total_rows:,} rows in batches of {batch_size:,}...")

  cursor = conn.cursor()
  cursor.execute("BEGIN TRANSACTION;")

  try:
    for start_idx in range(0, total_rows, batch_size):
      batch = db_df.iloc[start_idx : start_idx + batch_size]
      batch.to_sql("trips", conn, if_exists="append", index=False)
      print(
          f"Loaded batch {start_idx // batch_size + 1}: rows"
          f" {start_idx:,} to {min(start_idx + batch_size, total_rows):,}"
      )
    conn.commit()
    print("All trips successfully loaded into database.")
  except Exception as e:
    conn.rollback()
    print(f"Error during batch load, transaction rolled back: {e}")
    raise e
  finally:
    conn.close()


# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
  # 0. Initialize DB Schema
  init_database()

  # Connect to load dimensions
  conn = sqlite3.connect(DB_PATH)
  conn.execute("PRAGMA foreign_keys = ON;")
  load_dimensions(conn)
  conn.close()

  # Load raw parquet sample
  if not os.path.exists(PARQUET_PATH):
    print(f"Error: Parquet file not found at {PARQUET_PATH}")
    return

  print(f"\nReading parquet file from {PARQUET_PATH}...")
  df = pd.read_parquet(PARQUET_PATH)

  # Run cleaning & feature derivation
  cleaned_df, exclusion_log_df, initial_count = clean_and_derive_trips(df)

  # Save logs and print summary report
  save_exclusion_log(exclusion_log_df, initial_count, len(cleaned_df))

  # Load into database fact table
  load_trips_to_db(cleaned_df)


if __name__ == "__main__":
  main()