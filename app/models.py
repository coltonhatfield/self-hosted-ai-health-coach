from pydantic import BaseModel
from typing import Optional

class AppleHealthData(BaseModel):
    timestamp: Optional[str] = None
    date: Optional[str] = None # Added because iOS Shortcuts usually prefer 'date'
    
    # Standard Health Metrics
    sleep_hours: Optional[float] = None
    steps: Optional[int] = None
    active_energy_kcal: Optional[float] = None
    resting_energy_kcal: Optional[float] = None
    weight_lbs: Optional[float] = None
    height_in: Optional[float] = None
    
    # Boilerbites Dietary Sync Fields
    dietary_energy_kcal: Optional[float] = None
    protein_g: Optional[float] = None
    carbohydrates_g: Optional[float] = None
    fat_total_g: Optional[float] = None

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

from typing import List

class FoodEditRequest(BaseModel):
    id: int
    calories: int
    protein: int
    carbs: int
    fats: int

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
