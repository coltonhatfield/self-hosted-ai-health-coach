import logging
from database import get_trailing_7_days, save_ai_advice, write_metric
from gemini_ai import generate_daily_advice
import requests

logger = logging.getLogger(__name__)

def ai_coach_job():
    logger.info("Running Daily AI Coach Job...")
    data = get_trailing_7_days()
    
    if not data:
        logger.warning("No data found! Send push notification to user here to open Health Auto Export.")
        # Optional: requests.post("https://api.pushover.net/1/messages.json", data={"token": "x", "user": "y", "message": "Open Health Auto Export!"})
        return

    advice = generate_daily_advice(data)
    save_ai_advice(advice)
    logger.info("AI Coach Job Complete.")

def withings_sync_job():
    logger.info("Running Withings Sync Job...")
    # NOTE: Withings requires OAuth2 implementation. 
    # For a complete system, you must implement the refresh_token flow.
    # To prevent breaking your app right now, this is mocked to show where the data goes.
    try:
        # fetch data from withings API...
        mock_weight = 75.5 
        mock_fat = 15.2
        write_metric("withings", {"weight_kg": mock_weight, "fat_percent": mock_fat})
    except Exception as e:
        logger.error(f"Withings Sync Error: {e}")
