## Dimension Tables
1. **Zones**: Stores geographic metadata from `taxi_zone_lookup.csv`.
   - `location_id` (Primary Key, Integer)
   - `borough` (Text)
   - `zone` (Text)
   - `service_zone` (Text)

2. **rate_codes**: Stores TLC rate code descriptions.
   - `rate_code_id` (Primary Key, Integer)
   - `description` (Text: Credit card, Cash, No charge, Dispute, Unknown, Voided)

3.  **payment_types**: Stores TLC oayment method codes.
   - `payment_type_id` (Primary Key, integer)
   - `description` (Text: Credit card, Cash, No charge, Dispute, Unknown, Voided)


## Fact Table: `trips`
Stores individual cleansed trip records, foreign keys to dimensions, and computed metrics.
- `trip_id`: Primary Key, auto-incrementing integer.
- `pickup_datetime` & `dropoff_datetime`: Timestamps (NOT NULL).
- `pickup_location_id` & `dropff_location_id`: Foreign keys referencing `zones(location_id)`.
- `rate_code_id` & `payment_type_id`: Foreign keys for referencing their respective dimension tables.
- `rate_code_id` & `payment_type_id`: Foreign keys referencing their respective dimension tables.
- `passenger_count`, `trip_distance`, `fare_amount`, `tip_amount`, `total_amount`: Cleaned numerical fields (NOT NULL).
- **Derived Features:** `duration_minutes`, `average_speed_mph`, `tip_percentage`, and `pickup_hour`.