from pydantic import BaseModel
from typing import Optional

class AppleHealthData(BaseModel):
    timestamp: str  
    sleep_hours: float
    steps: int
    active_energy_kcal: float
    resting_energy_kcal: float

class ManualEntryData(BaseModel):
    date: str
    soreness: int
    mood: int
    energy: int

class MacroData(BaseModel):
    item_name: str
    calories: int
    protein: int
    carbs: int
    fats: int

class TextFoodRequest(BaseModel):
    text: str

class WorkoutRequest(BaseModel):
    soreness: int
    energy: int
    modification: Optional[str] = None

class DailyJournal(BaseModel):
    soreness: int
    energy: int
    vball_hours: float
    vball_intensity: int 
    notes: str
