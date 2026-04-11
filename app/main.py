from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging

from models import AppleHealthData, ManualEntryData, MacroData, TextFoodRequest, WorkoutRequest, DailyJournal
from database import write_metric, log_food_to_sqlite, get_food_log_from_sqlite, get_todays_advice, get_trailing_7_days, save_journal, get_recent_journal, save_workout_plan, get_todays_workout_plan
from gemini_ai import estimate_macros_from_image, estimate_macros_from_text, generate_workout_plan
from jobs import ai_coach_job, withings_sync_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Health Dashboard API")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/food-tracker")
def serve_food_tracker():
    return FileResponse("static/index.html")

API_KEY = os.getenv("API_KEY", "testkey")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.on_event("startup")
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(ai_coach_job, 'cron', hour=6, minute=0)
    scheduler.add_job(withings_sync_job, 'cron', hour=5, minute=50)
    scheduler.start()

# --- ROUTES ---

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "System is running"}

@app.post("/api/v1/apple-health", dependencies=[Depends(verify_api_key)])
def ingest_apple_health(data: AppleHealthData):
    write_metric("apple_health", data.dict(exclude={'timestamp'}), timestamp_str=data.timestamp)
    return {"status": "success"}

@app.post("/api/v1/manual-entry", dependencies=[Depends(verify_api_key)])
def ingest_manual_entry(data: ManualEntryData):
    write_metric("manual_entry", data.dict(exclude={'date'}))
    return {"status": "success"}

@app.post("/api/v1/parse-food", dependencies=[Depends(verify_api_key)])
async def parse_food_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    return estimate_macros_from_image(image_bytes)

@app.post("/api/v1/parse-food-text", dependencies=[Depends(verify_api_key)])
def parse_food_text(req: TextFoodRequest):
    return estimate_macros_from_text(req.text)

@app.post("/api/v1/log-macros", dependencies=[Depends(verify_api_key)])
def log_approved_macros(data: MacroData):
    write_metric("macros", data.dict())
    log_food_to_sqlite(data.item_name, data.calories, data.protein, data.carbs, data.fats)
    return {"status": "success"}

@app.get("/api/v1/food-history", dependencies=[Depends(verify_api_key)])
def get_food_history():
    return get_food_log_from_sqlite()

@app.get("/api/v1/daily-advice", dependencies=[Depends(verify_api_key)])
def serve_daily_advice():
    return {"advice": get_todays_advice()}

@app.post("/api/v1/journal", dependencies=[Depends(verify_api_key)])
def ingest_journal(data: DailyJournal):
    save_journal(data.soreness, data.energy, data.vball_hours, data.vball_intensity, data.notes)
    write_metric("daily_feelings", {"soreness": data.soreness, "energy": data.energy})
    return {"status": "success"}

@app.get("/api/v1/workout", dependencies=[Depends(verify_api_key)])
def serve_daily_workout():
    return {"workout_plan": get_todays_workout_plan()}

@app.post("/api/v1/generate-workout", dependencies=[Depends(verify_api_key)])
def build_workout(req: WorkoutRequest):
    data_summary = get_trailing_7_days()
    journal_history = get_recent_journal()
    plan = generate_workout_plan(data_summary, req.soreness, req.energy, journal_history, req.modification)
    save_workout_plan(plan)
    return {"workout_plan": plan}
