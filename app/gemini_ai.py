import os
import json
import logging
import google.generativeai as genai
from database import get_recent_journal

logger = logging.getLogger(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MACRO_PROMPT = """
Estimate the total calories, protein (g), carbohydrates (g), and fats (g). 
Also provide a short, 2-4 word description of the food as 'item_name'.
Return ONLY a raw JSON object with this exact format (no markdown or backticks):
{"item_name": "Food Name", "calories": 0, "protein": 0, "carbs": 0, "fats": 0}
"""

def clean_json(text: str) -> dict:
    clean_text = text.replace('```json', '').replace('```', '').strip()
    try:
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"JSON Clean Error: {e}")
        return {"item_name": "Unknown", "calories": 0, "protein": 0, "carbs": 0, "fats": 0}

def estimate_macros_from_image(image_bytes: bytes) -> dict:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content([{'mime_type': 'image/jpeg', 'data': image_bytes}, f"Analyze this food image. {MACRO_PROMPT}"])
        return clean_json(response.text)
    except Exception as e:
        logger.error(f"Gemini Vision Error: {e}")
        return {"item_name": "Image Error", "calories": 0, "protein": 0, "carbs": 0, "fats": 0}

def estimate_macros_from_text(text: str) -> dict:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(f"Analyze this food text: '{text}'. {MACRO_PROMPT}")
        return clean_json(response.text)
    except Exception as e:
        logger.error(f"Gemini Text Error: {e}")
        return {"item_name": "Text Error", "calories": 0, "protein": 0, "carbs": 0, "fats": 0}

def generate_daily_advice(data_context: str) -> str:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Act as a data-driven sports science and health coach for a 19-year-old male college student who plays competitive club volleyball as a libero.
        Goals: optimize recovery from high-impact sports, manage daily athletic strain, maintain ideal body composition.

        Here is the trailing 7-day data summary:
        {data_context}

        CRITICAL CONTEXT: The most recent date in this data is TODAY. Because the day is currently ongoing, today's data is INCOMPLETE. Do NOT sound the alarm over low calories, missing sleep, or low steps for today. Base your primary analysis on YESTERDAY'S completed data and the 7-day trend.

        Task: Analyze trends. Output a brief, 2-3 sentence analysis of current recovery status and dietary adherence, followed by two highly specific, actionable recommendations for today. Format neatly.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Coach Error: {e}")
        return "AI Coach unavailable today. Focus on standard recovery and hydration."

def generate_workout_plan(data_context: str, soreness: int, energy: int, journal_history: str, modification: str = None) -> str:
    mod_text = f"\nCRITICAL INSTRUCTION FROM ATHLETE FOR THIS SPECIFIC WORKOUT: '{modification}'. You MUST alter your generation to accommodate this request.\n" if modification else ""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Act as an elite Strength & Conditioning coach for a competitive collegiate club volleyball Libero.
        Goal: Explosiveness, lateral quickness, injury prevention, and general strength.

        Athlete's Current State for Today:
        - Soreness Level: {soreness}/10
        - Energy Level: {energy}/10
        
        Athlete's Recent Journal & Feedback:
        {journal_history}
        
        Recent 7-day health & strain data:
        {data_context}
        {mod_text}
        
        Task: Generate a specific, single-day workout plan for today that respects their current soreness, recent volleyball volume, text feedback, and any critical modifications listed above. 
        Format strictly as:
        **Warmup**
        - (Quick list)
        **Main Block**
        - (3-4 Exercises with SetsxReps)
        **Cool Down**
        - (Quick mobility)
        
        Keep it under 150 words. Do not include introductory fluff or warnings.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Workout Error: {e}")
        return "Unable to generate workout today. Focus on light mobility and active recovery."
