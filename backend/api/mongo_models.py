"""
LiveStock IQ — MongoDB Document Schemas (via PyMongo)

Collections:
  sensor_readings   → High-frequency time-series data per cattle
  herd_snapshots    → Hourly farm-level aggregated snapshots
  event_log         → Raw sensor events & anomalies

MongoDB is used for time-series data because:
  - High write throughput (sensor every 10 sec = 8640 docs/day per cow)
  - Flexible schema for different sensor types
  - Efficient range queries on timestamps
  - TTL indexes for automatic old-data purging
"""

from datetime import datetime, timedelta
from django.conf import settings
import pymongo


# ===================== CONNECTION =====================
def get_mongo_db():
    """Return a MongoDB database connection."""
    client = pymongo.MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME]


def get_collection(name: str):
    """Return a named MongoDB collection."""
    return get_mongo_db()[name]


# ===================== INDEXES & SETUP =====================
def setup_mongodb_indexes():
    """
    Create all required indexes. Call once on startup.
    Safe to call repeatedly (idempotent).
    """
    db = get_mongo_db()

    # --- sensor_readings ---
    sr = db['sensor_readings']
    sr.create_index([('cattle_id', pymongo.ASCENDING), ('timestamp', pymongo.DESCENDING)])
    sr.create_index([('timestamp', pymongo.ASCENDING)],
                    expireAfterSeconds=60 * 60 * 24 * 90)   # Auto-purge after 90 days

    # --- herd_snapshots ---
    hs = db['herd_snapshots']
    hs.create_index([('farm_id', pymongo.ASCENDING), ('hour', pymongo.DESCENDING)])
    hs.create_index([('hour', pymongo.ASCENDING)],
                    expireAfterSeconds=60 * 60 * 24 * 365)  # Keep 1 year

    # --- event_log ---
    el = db['event_log']
    el.create_index([('cattle_id', pymongo.ASCENDING), ('timestamp', pymongo.DESCENDING)])
    el.create_index([('event_type', pymongo.ASCENDING)])

    print("✅ MongoDB indexes created successfully.")


# ===================== SENSOR READING SCHEMA =====================
def build_sensor_reading(cattle_id: str, temperature: float,
                         activity: int, feeding: int,
                         battery_pct: int = 100, signal: int = 85,
                         anomaly: str = None) -> dict:
    """
    Schema for a single sensor reading document.

    Collection: sensor_readings
    {
        cattle_id      : "C001"
        timestamp      : ISODate("2026-03-27T16:45:00Z")
        temperature    : 38.5         # Celsius
        activity       : 72           # 0-100
        feeding        : 80           # 0-100
        battery_pct    : 95
        signal_strength: 85
        anomaly        : null | "fever" | "low_activity" | "estrus" | "poor_feeding"
        metadata       : { firmware: "2.4.1" }
    }
    """
    return {
        'cattle_id':       cattle_id,
        'timestamp':       datetime.utcnow(),
        'temperature':     round(temperature, 2),
        'activity':        int(activity),
        'feeding':         int(feeding),
        'battery_pct':     int(battery_pct),
        'signal_strength': int(signal),
        'anomaly':         anomaly,
        'metadata':        {'firmware': '2.4.1'},
    }


# ===================== HERD SNAPSHOT SCHEMA =====================
def build_herd_snapshot(farm_id: int, hour: datetime,
                        avg_temp: float, avg_activity: float,
                        avg_feeding: float, healthy: int,
                        sick: int, fever: int, estrus: int,
                        total: int) -> dict:
    """
    Hourly aggregated farm snapshot.

    Collection: herd_snapshots
    {
        farm_id        : 1
        hour           : ISODate("2026-03-27T16:00:00Z")
        avg_temp       : 38.6
        avg_activity   : 71
        avg_feeding    : 78
        counts         : { healthy: 18, sick: 2, fever: 1, estrus: 2, total: 23 }
    }
    """
    return {
        'farm_id':      farm_id,
        'hour':         hour.replace(minute=0, second=0, microsecond=0),
        'avg_temp':     round(avg_temp, 2),
        'avg_activity': round(avg_activity, 1),
        'avg_feeding':  round(avg_feeding, 1),
        'counts': {
            'healthy': healthy,
            'sick':    sick,
            'fever':   fever,
            'estrus':  estrus,
            'total':   total,
        },
    }


# ===================== EVENT LOG SCHEMA =====================
def build_event(cattle_id: str, event_type: str,
                description: str, value=None) -> dict:
    """
    Raw event log (anomaly detection, status changes).

    Collection: event_log
    {
        cattle_id   : "C001"
        event_type  : "fever_detected" | "estrus_detected" | "low_feeding" | "sensor_reconnect"
        description : "Temperature crossed 39.5°C threshold"
        value       : 40.1
        timestamp   : ISODate(...)
    }
    """
    return {
        'cattle_id':   cattle_id,
        'event_type':  event_type,
        'description': description,
        'value':       value,
        'timestamp':   datetime.utcnow(),
    }


# ===================== QUERY HELPERS =====================
def get_readings_for_cattle(cattle_id: str, hours: int = 24) -> list:
    """Return last N hours of sensor readings for a cattle."""
    col = get_collection('sensor_readings')
    since = datetime.utcnow() - timedelta(hours=hours)
    cursor = col.find(
        {'cattle_id': cattle_id, 'timestamp': {'$gte': since}},
        {'_id': 0}
    ).sort('timestamp', pymongo.ASCENDING)
    return list(cursor)


def get_herd_snapshots(farm_id: int, hours: int = 24) -> list:
    """Return last N hourly snapshots for a farm."""
    col = get_collection('herd_snapshots')
    since = datetime.utcnow() - timedelta(hours=hours)
    cursor = col.find(
        {'farm_id': farm_id, 'hour': {'$gte': since}},
        {'_id': 0}
    ).sort('hour', pymongo.ASCENDING)
    return list(cursor)


def get_events_for_cattle(cattle_id: str, limit: int = 20) -> list:
    """Return recent events for a cattle."""
    col = get_collection('event_log')
    cursor = col.find(
        {'cattle_id': cattle_id},
        {'_id': 0}
    ).sort('timestamp', pymongo.DESCENDING).limit(limit)
    return list(cursor)


def insert_sensor_reading(doc: dict) -> str:
    """Insert a single sensor reading. Returns the inserted id string."""
    col = get_collection('sensor_readings')
    result = col.insert_one(doc)
    return str(result.inserted_id)


def insert_herd_snapshot(doc: dict) -> str:
    col = get_collection('herd_snapshots')
    result = col.insert_one(doc)
    return str(result.inserted_id)


def insert_event(doc: dict) -> str:
    col = get_collection('event_log')
    result = col.insert_one(doc)
    return str(result.inserted_id)


def get_mongo_stats(farm_id: int) -> dict:
    """Aggregation: count total readings & events stored in MongoDB."""
    db = get_mongo_db()
    reading_count = db['sensor_readings'].count_documents({})
    event_count   = db['event_log'].count_documents({})
    snapshot_count = db['herd_snapshots'].count_documents({'farm_id': farm_id})
    return {
        'total_sensor_readings': reading_count,
        'total_events':          event_count,
        'herd_snapshots':        snapshot_count,
        'database':              settings.MONGODB_DB_NAME,
    }
