from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
import os
import logging
from database import write_metric, log_food_to_sqlite, get_food_log_from_sqlite, get_todays_advice, get_trailing_7_days, save_journal, get_recent_journal, save_workout_plan, get_todays_workout_plan, get_todays_macros, update_food_in_sqlite, save_ai_advice
from gemini_ai import estimate_macros_from_image, estimate_macros_from_text, generate_workout_plan, generate_next_meal_recommendation, coach_chat, generate_daily_advice

# FIX 1: Added FoodEditRequest and ChatRequest to the imports
from models import AppleHealthData, ManualEntryData, MacroData, TextFoodRequest, WorkoutRequest, DailyJournal, FoodEditRequest, ChatRequest
from database import write_metric, log_food_to_sqlite, get_food_log_from_sqlite, get_todays_advice, get_trailing_7_days, save_journal, get_recent_journal, save_workout_plan, get_todays_workout_plan, get_todays_macros, update_food_in_sqlite
from gemini_ai import estimate_macros_from_image, estimate_macros_from_text, generate_workout_plan, generate_next_meal_recommendation, coach_chat
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
def ingest_apple_health(payload: dict):
    parsed_data = {}
    
    metrics = payload.get("data", {}).get("metrics", [])
    
    if not metrics:
        return {"status": "ignored", "message": "No valid metrics found in payload"}
        
    for metric in metrics:
        name = metric.get("name", "")
        data_points = metric.get("data", [])
        
        if not data_points:
            continue
            
        # Sum up all the data points for the day
        total_qty = sum(point.get("qty", 0) for point in data_points if isinstance(point.get("qty"), (int, float)))
        # For body metrics, grab the most recent measurement
        last_qty = data_points[-1].get("qty") if data_points else None
        
        # --- BULLETPROOF MAPPING ---
        if name == "step_count":
            parsed_data["steps"] = total_qty
        elif name in ["active_energy", "active_energy_kcal"]:
            parsed_data["active_energy_kcal"] = total_qty
        elif name in ["basal_energy_burned", "resting_energy", "resting_energy_kcal"]:
            parsed_data["resting_energy_kcal"] = total_qty
        elif name in ["dietary_energy", "energy", "calories"]:
            parsed_data["dietary_energy_kcal"] = total_qty
        elif name in ["dietary_protein", "protein"]:
            parsed_data["protein_g"] = total_qty
        elif name in ["dietary_carbohydrates", "carbohydrates", "carbs"]:
            parsed_data["carbohydrates_g"] = total_qty
        elif name in ["dietary_fat_total", "fat_total", "fat"]:
            parsed_data["fat_total_g"] = total_qty
        elif name in ["dietary_sugar", "sugar"]:
            parsed_data["sugar_g"] = total_qty
        elif name in ["dietary_fiber", "fiber"]:
            parsed_data["fiber_g"] = total_qty
        elif name in ["body_mass", "weight"]:
            parsed_data["weight_lbs"] = last_qty
        elif name in ["body_fat_percentage", "body_fat"]:
            parsed_data["body_fat_percent"] = last_qty
        elif name in ["body_mass_index", "bmi"]:
            parsed_data["bmi"] = last_qty
        elif name in ["height"]:
            parsed_data["height_in"] = last_qty
        elif name in ["sleep_analysis", "sleep"]:
            parsed_data["sleep_hours"] = total_qty
        else:
            print(f"⚠️ Unmapped metric received from phone: {name}")
            
    if not parsed_data:
        return {"status": "ignored", "message": "Payload received, but no mapped metrics were found"}

    record_time = None
    try:
        record_time = metrics[0]["data"][0].get("date")
    except (IndexError, KeyError):
        pass

    write_metric("apple_health", parsed_data, timestamp_str=record_time)
    
    return {"status": "success", "metrics_written": list(parsed_data.keys())}

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

    # Generate the next meal recommendation
    todays_macros = get_todays_macros()
    recommendation = generate_next_meal_recommendation(todays_macros)

    return {"status": "success", "next_meal_recommendation": recommendation}

# FIX 2: Added the missing '@' symbol here
@app.get("/api/v1/food-history", dependencies=[Depends(verify_api_key)])
def get_food_history(page: int = 1, limit: int = 10):
    return get_food_log_from_sqlite(page, limit)

@app.get("/api/v1/daily-advice", dependencies=[Depends(verify_api_key)])
def serve_daily_advice():
    return {"advice": get_todays_advice()}

@app.post("/api/v1/force-advice", dependencies=[Depends(verify_api_key)])
def generate_fresh_advice():
    # 1. Grab the latest data from InfluxDB
    data_summary = get_trailing_7_days()
    
    if not data_summary:
        return {"advice": "No data found for the last 7 days. Sync Apple Health first!"}
    
    # 2. Force the AI to generate a new analysis
    advice = generate_daily_advice(data_summary)
    
    # 3. Overwrite the old cached error in SQLite with the new advice
    save_ai_advice(advice)
    
    return {"advice": advice}

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

@app.put("/api/v1/food-history", dependencies=[Depends(verify_api_key)])
def edit_food_history(req: FoodEditRequest):
    update_food_in_sqlite(req.id, req.calories, req.protein, req.carbs, req.fats)
    return {"status": "success"}

@app.post("/api/v1/coach-chat", dependencies=[Depends(verify_api_key)])
def chat_with_coach(req: ChatRequest):
    reply = coach_chat(req.message, req.history)
    return {"reply": reply}

class ManualWorkoutSave(BaseModel):
    plan: str

@app.post("/api/v1/save-manual-workout", dependencies=[Depends(verify_api_key)])
def save_manual_workout(req: ManualWorkoutSave):
    # Reuses your existing database function to save the text
    save_workout_plan(req.plan)
    return {"status": "success"}
