import os
import sqlite3
import uuid
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import logging

logger = logging.getLogger(__name__)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

os.makedirs("/app/data", exist_ok=True)
conn = sqlite3.connect('/app/data/ai_coach.db', check_same_thread=False)

# Initialize tables using direct connection execution (thread-safe)
with conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS daily_advice (date TEXT PRIMARY KEY, advice TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS food_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, item_name TEXT,
                  calories INTEGER, protein INTEGER, carbs INTEGER, fats INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS journal 
                 (date TEXT PRIMARY KEY, soreness INTEGER, energy INTEGER, vball_hours REAL, vball_intensity INTEGER, notes TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS daily_workout 
                 (date TEXT PRIMARY KEY, plan TEXT)''')

def write_metric(measurement: str, fields: dict, timestamp_str: str = None):
    try:
        point = Point(measurement)
        if timestamp_str:
            point.time(timestamp_str)
        else:
            point.time(datetime.utcnow())

        if measurement != "apple_health":
            point.tag("entry_id", str(uuid.uuid4()))

        for key, value in fields.items():
            if isinstance(value, str):
                point.field(key, value)
            else:
                point.field(key, float(value))

        write_api.write(bucket=INFLUX_BUCKET, record=point)
        logger.info(f"Successfully wrote {measurement} to InfluxDB")
    except Exception as e:
        logger.error(f"InfluxDB Write Error: {e}")

def log_food_to_sqlite(item_name: str, calories: int, protein: int, carbs: int, fats: int):
    now = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO food_log (timestamp, item_name, calories, protein, carbs, fats) VALUES (?, ?, ?, ?, ?, ?)",
              (now, item_name, calories, protein, carbs, fats))
    conn.commit()

def get_food_log_from_sqlite(page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    cursor = conn.cursor()
    # Added 'id' to the SELECT statement and added LIMIT/OFFSET
    cursor.execute("SELECT id, timestamp, item_name, calories, protein, carbs, fats FROM food_log ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    return [{"id": r[0], "timestamp": r[1], "item_name": r[2], "calories": r[3], "protein": r[4], "carbs": r[5], "fats": r[6]} for r in rows]

def update_food_in_sqlite(entry_id: int, calories: int, protein: int, carbs: int, fats: int):
    conn.execute("UPDATE food_log SET calories=?, protein=?, carbs=?, fats=? WHERE id=?", 
                 (calories, protein, carbs, fats, entry_id))
    conn.commit()

def get_todays_macros() -> dict:
    today = datetime.utcnow().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fats) FROM food_log WHERE timestamp LIKE ?", (f"{today}%",))
    row = cursor.fetchone()
    return {
        "calories": row[0] or 0, 
        "protein": row[1] or 0, 
        "carbs": row[2] or 0, 
        "fats": row[3] or 0
    }

def get_trailing_7_days() -> str:
    data_summary = []
    
    query_macros = f'''
    from(bucket:"{INFLUX_BUCKET}")
    |> range(start: -7d)
    |> filter(fn: (r) => r._measurement == "macros")
    |> filter(fn: (r) => r._field != "item_name")
    |> group(columns: ["_field"])
    |> aggregateWindow(every: 1d, fn: sum, createEmpty: false)
    '''
    try:
        res = query_api.query(org=INFLUX_ORG, query=query_macros)
        for table in res:
            for record in table.records:
                data_summary.append(f"{record.get_time().strftime('%Y-%m-%d')} - macros_{record.get_field()}: {record.get_value():.1f}")
    except Exception as e:
        logger.error(f"Macro Query Error: {e}")

    query_health = f'''
    from(bucket:"{INFLUX_BUCKET}")
    |> range(start: -7d)
    |> filter(fn: (r) => r._measurement == "apple_health" or r._measurement == "manual_entry")
    |> aggregateWindow(every: 1d, fn: last, createEmpty: false)
    '''
    try:
        res = query_api.query(org=INFLUX_ORG, query=query_health)
        for table in res:
            for record in table.records:
                data_summary.append(f"{record.get_time().strftime('%Y-%m-%d')} - {record.get_measurement()}_{record.get_field()}: {record.get_value():.1f}")
    except Exception as e:
        logger.error(f"Health Query Error: {e}")

    return "\n".join(data_summary)

def save_ai_advice(advice: str):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    conn.execute("INSERT OR REPLACE INTO daily_advice (date, advice) VALUES (?, ?)", (today, advice))
    conn.commit()

def get_todays_advice() -> str:
    today = datetime.utcnow().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute("SELECT advice FROM daily_advice WHERE date=?", (today,))
    row = cursor.fetchone()
    return row[0] if row else "Your AI Coach is analyzing your data. Check back tomorrow morning."

def save_journal(soreness: int, energy: int, vball_hours: float, vball_intensity: int, notes: str):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    conn.execute("INSERT OR REPLACE INTO journal (date, soreness, energy, vball_hours, vball_intensity, notes) VALUES (?, ?, ?, ?, ?, ?)",
              (today, soreness, energy, vball_hours, vball_intensity, notes))
    conn.commit()

def get_recent_journal() -> str:
    cursor = conn.cursor()
    cursor.execute("SELECT date, soreness, energy, vball_hours, vball_intensity, notes FROM journal ORDER BY date DESC LIMIT 3")
    rows = cursor.fetchall()
    if not rows: return "No recent journal entries."
    
    log = []
    for r in rows:
        log.append(f"Date: {r[0]} | Soreness: {r[1]}/10 | Energy: {r[2]}/10 | Volleyball: {r[3]} hours (Intensity {r[4]}/10) | Athlete Notes: '{r[5]}'")
    return "\n".join(log)

def save_workout_plan(plan: str):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    conn.execute("INSERT OR REPLACE INTO daily_workout (date, plan) VALUES (?, ?)", (today, plan))
    conn.commit()

def get_todays_workout_plan() -> str:
    today = datetime.utcnow().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute("SELECT plan FROM daily_workout WHERE date=?", (today,))
    row = cursor.fetchone()
    return row[0] if row else ""
