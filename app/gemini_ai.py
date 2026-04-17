import os
import requests
import logging
from database import get_recent_journal, get_trailing_7_days, get_todays_macros

logger = logging.getLogger(__name__)

# Dynamically pull from your new .env variables
LLM_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("LLM_MODEL", "llama3-8b-8192")

def query_llm(system_prompt: str, user_prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500  # Keeps the response fast and concise
    }
    
    try:
        response = requests.post(LLM_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Groq Rejected Payload: {e.response.text}")
        return "AI payload error. Check backend logs."
    except Exception as e:
        logger.error(f"LLM API Error: {e}")
        return "AI is currently offline."

def generate_daily_advice(data_context: str) -> str:
    system = "Act as a data-driven sports scientist for a competitive collegiate club volleyball libero."
    prompt = f"""
    Here is the trailing 7-day health telemetry:
    {data_context}

    Task: Provide a brief health insight report.
    1. Identify 1 major trend from the data.
    2. Provide 2 highly specific, actionable directives for today to improve performance and recovery.
    
    Use exact numbers from the telemetry. Format with bullet points.
    """
    return query_llm(system, prompt)

def generate_workout_plan(data_context: str, soreness: int, energy: int, journal_history: str, modification: str = None) -> str:
    mod_text = f"\nCRITICAL INSTRUCTIONS TO MODIFY EXISTING PLAN:\n{modification}\n" if modification else ""
    
    system = "Act as an elite Strength & Conditioning coach for a collegiate club volleyball Libero."
    prompt = f"""
    Recent 7-day health & strain data:
    {data_context}
    {mod_text}

    Task: Generate a full 7-Day Workout Plan (Monday - Sunday).
    - Include specific exercises, sets, and reps.
    - Format as plain text using markdown.
    """
    return query_llm(system, prompt)

def coach_chat(message: str, history: list) -> str:
    messages = []
    
    recent_data = get_trailing_7_days()
    journal = get_recent_journal()
    todays_macros = get_todays_macros()
    
    system_instruction = f"""
    You are a strength coach for a collegiate club volleyball libero. Keep answers concise.
    Live Data:
    - Macros: {todays_macros}
    - Recent Journal: {journal}
    - 7-Day Strain: {recent_data}
    """
    messages.append({"role": "system", "content": system_instruction})
    
    for h in history[-5:]:
        role = "user" if h.role == "user" else "assistant"
        messages.append({"role": role, "content": h.text})
        
    messages.append({"role": "user", "content": message})
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL_NAME, "messages": messages, "temperature": 0.7, "max_tokens": 250}
    
    try:
        response = requests.post(LLM_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as e:
        logger.error(f"Groq Chat Rejected: {e.response.text}")
        return "Coach encountered a strict API payload error."
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        return "Coach is offline."

# Stubs to prevent FastAPI import crashes
def estimate_macros_from_image(image_bytes): return {}
def estimate_macros_from_text(text): return {}
def generate_next_meal_recommendation(macros): return ""
