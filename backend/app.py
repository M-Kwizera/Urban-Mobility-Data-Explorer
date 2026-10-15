from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_db_connection
from algorithms import compute_top_n_zones

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Allow-list for secure sorting to prevent SQL injection
VALID_SORT_COLUMNS = {
    "pickup_datetime": "pickup_datetime",
    "trip_distance": "trip_distance",
    "fare_amount": "fare_amount",
    "total_amount": "total_amount",
    "duration_minutes": "duration_minutes",
    "average_speed_mph": "average_speed_mph",
}


@app.route("/api/health", methods=["GET"])
def health_check():
  return jsonify({"status": "ok"})


@app.route("/api/trips", methods=["GET"])
def get_trips():
  try:
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)  # Cap at 100
  except ValueError:
    return jsonify({"error": "Invalid pagination parameters"}), 400

  sort_by = request.args.get("sort_by", "pickup_datetime")
  sort_dir = request.args.get("sort_dir", "DESC").upper()

  if sort_by not in VALID_SORT_COLUMNS:
    return jsonify({"error": "Invalid sort column"}), 400
  if sort_dir not in ["ASC", "DESC"]:
    sort_dir = "DESC"

  query = """
        SELECT t.*, 
               pz.zone AS pickup_zone_name, pz.borough AS pickup_borough,
               dz.zone AS dropoff_zone_name, dz.borough AS dropoff_borough
        FROM trips t
        LEFT JOIN zones pz ON t.pickup_location_id = pz.location_id
        LEFT JOIN zones dz ON t.dropoff_location_id = dz.location_id
        WHERE 1=1
    """
  params = []

  # Filters
  if request.args.get("hour"):
    try:
      query += " AND t.pickup_hour = ?"
      params.append(int(request.args.get("hour")))
    except ValueError:
      return jsonify({"error": "Invalid hour parameter"}), 400

  if request.args.get("min_distance"):
    try:
      query += " AND t.trip_distance >= ?"
      params.append(float(request.args.get("min_distance")))
    except ValueError:
      return jsonify({"error": "Invalid min_distance parameter"}), 400

  if request.args.get("borough"):
    query += " AND pz.borough = ?"
    params.append(request.args.get("borough"))

  # Sorting & Pagination
  query += (
      f" ORDER BY t.{VALID_SORT_COLUMNS[sort_by]} {sort_dir} LIMIT ? OFFSET ?"
  )
  offset = (page - 1) * page_size
  params.extend([page_size, offset])

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(query, params)
  rows = cursor.fetchall()
  trips = [dict(row) for row in rows]
  conn.close()

  return jsonify({"page": page, "page_size": page_size, "trips": trips})


@app.route("/api/stats", methods=["GET"])
def get_stats():
  query = """
        SELECT COUNT(*) AS total_trips,
               AVG(fare_amount) AS avg_fare,
               AVG(trip_distance) AS avg_distance,
               AVG(average_speed_mph) AS avg_speed,
               AVG(duration_minutes) AS avg_duration
        FROM trips t
    """
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(query)
  row = cursor.fetchone()
  conn.close()

  return jsonify(dict(row) if row else {})


@app.route("/api/trips-by-hour", methods=["GET"])
def get_trips_by_hour():
  query = """
        SELECT pickup_hour, 
               COUNT(*) AS trip_count, 
               AVG(average_speed_mph) AS avg_speed,
               AVG(tip_percentage) AS avg_tip_percentage
        FROM trips
        GROUP BY pickup_hour
        ORDER BY pickup_hour ASC
    """
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(query)
  rows = [dict(row) for row in cursor.fetchall()]
  conn.close()

  return jsonify(rows)


@app.route("/api/zones", methods=["GET"])
def get_zones():
  query = """
        SELECT z.location_id, z.borough, z.zone, z.service_zone,
               COUNT(t.trip_id) AS trip_count
        FROM zones z
        LEFT JOIN trips t ON z.location_id = t.pickup_location_id
        GROUP BY z.location_id, z.borough, z.zone, z.service_zone
        ORDER BY trip_count DESC
    """
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(query)
  rows = [dict(row) for row in cursor.fetchall()]
  conn.close()

  return jsonify(rows)


@app.route("/api/top-zones", methods=["GET"])
def get_top_zones():
  try:
    n = int(request.args.get("n", 5))
  except ValueError:
    n = 5

  query = """
        SELECT z.zone, z.borough, COUNT(t.trip_id) AS trip_count
        FROM zones z
        JOIN trips t ON z.location_id = t.pickup_location_id
        GROUP BY z.location_id, z.zone, z.borough
    """
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(query)
  zones_data = [dict(row) for row in cursor.fetchall()]
  conn.close()

  # Run custom min-heap algorithm
  top_zones = compute_top_n_zones(zones_data, n=n)

  return jsonify(top_zones)


if __name__ == "__main__":
  app.run(debug=True, port=5000)