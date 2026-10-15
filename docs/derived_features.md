# Derived Features Specification

This document defines the metrics calculated from multiple raw columns, plus supplementary time dimensions used for analytical slicing.

---

## 1. Trip Duration
- **Formula in words:** Drop-off timestamp minus pick-up timestamp, converted into minutes.
- **Source columns:** `tpep_dropoff_datetime`, `tpep_pickup_datetime`
- **Edge cases:** Negative or zero durations caused by meter errors or out-of-order timestamps. These are caught and filtered out during basic cleaning.
- **Why it matters:** Essential for calculating speed, evaluating traffic delays, and measuring true operational time.

---

## 2. Average Speed
- **Formula in words:** Trip distance divided by trip duration (expressed in hours), yielding miles per hour (MPH).
- **Source columns:** `trip_distance`, Trip Duration
- **Edge cases:** Infinite or NaN values caused by zero-duration trips; unrealistic teleportation speeds (e.g., 150 MPH in city traffic). Controlled via a strict speed ceiling rule.
- **Why it matters:** Highlights congestion hotspots, inefficient routing, and data anomalies.

---

## 3. Tip Percentage
- **Formula in words:** Tip amount divided by base fare amount, multiplied by 100. Using the base fare as the denominator prevents tolls and surcharges from distorting the tipping behavior.
- **Source columns:** `tip_amount`, `fare_amount`, `payment_type`
- **Decision on Cash vs. Card:** Computed **only for credit card payments** (`payment_type = 1`). Because TLC data only records electronic tips, cash tips default to 0. Restricting to card payments prevents cash trips from artificially dragging down averages and looking like non-tippers.
- **Edge cases:** Zero fares (division by zero, handled by base cleaning) and absurd outliers (e.g., a 500% tip). Capped at a maximum threshold defined in cleaning rules.
- **Why it matters:** Reflects rider generosity, service quality, and driver earnings across different hours, boroughs, and trip lengths. The card-only limitation also serves as our primary **unexpected data observation**.

---

## 4. Hour-of-Day Bucket
- **Formula in words:** Extract the hour (0 to 23) from the pick-up timestamp, and optionally map it to named periods (e.g., Morning Rush: 07:00–10:00, Midday: 10:00–16:00, Evening Rush: 16:00–19:00, Late Night: 19:00–07:00).
- **Source columns:** `tpep_pickup_datetime`
- **Decisions:** We store **both** the raw integer hour and the named period label. The raw integer makes charting and numeric filtering straightforward, while labels make executive summaries readable. 
- **Note on Classification:** Unlike the first three features, the hour bucket is built from a single column. It functions as a useful categorical dimension rather than a multi-column derived metric.
- **Why it matters:** It acts as the primary X-axis for almost every demand, pricing, and congestion chart in the pipeline.


## Order of Operations

1. **Clean the  basics:** Drop missing values, remove exact duplicate rows, ensure drop-off is strictly after pick-up, and filter out distances less than or equal to 0.
2. **Derive features:** Calculate trip duration, average speed, tip percentage (restricted to credit card payments), and hour-of-day buckets.
3. **Apply derived-value rules:** Filter out rows violating data bounds (e.g., speed ceilings, maximum duration limits, and the tip percentage cap).
4. **Log exclusions:** Record every excluded row count along with its specific exclusion reason for auditing.

## Derived Feaature Thresholds
- **Tip Percentage Cap:** Restricted to credit card payments (`payment_type = 1`) with a maximum allowable tip percentage of 100% to eliminate extreme keying errors or data anomalies.
- **Speed & Duration Limits:** Trips exceeding realistic urban speed thresholds (e.g., > 80 MPH)