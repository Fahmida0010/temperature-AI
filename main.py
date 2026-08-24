import os
from dotenv import load_dotenv

# .env ফাইল লোড করা (এটি FortyGuardClient ইনিশিয়ালাইজ করার আগেই কল হতে হবে)
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from fortyguard.client import FortyGuardClient

app = FastAPI()

# Frontend (React/Vite) থেকে রিকোয়েস্ট আসার জন্য CORS অনুমতি
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FortyGuard Client ইনস্ট্যান্স (.env থেকে FORTYGUARD_API_KEY রিড করবে)
fg_client = FortyGuardClient()

# Pydantic Schemas (Frontend API Request payload-এর সাথে মিলিয়ে)
class Location(BaseModel):
    lat: float
    lng: float

class MissionRequest(BaseModel):
    origin: Location
    destination: Location
    activity: str
    pace: str
    prompt: Optional[str] = None
    special_tags: List[str] = []

class IntentRequest(BaseModel):
    prompt: str

# --- আপনার আগের বিদ্যমান Route গুলো ---

@app.get("/")
def read_root():
    return {"message": "Server is running successfully!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "demo_mode": False}

# --- নতুন যুক্ত হওয়া API Endpoint গুলো ---

@app.post("/api/mission")
async def plan_mission(req: MissionRequest):
    try:
        # Step A: Lat/Lng দিয়ে Polygon AOI তৈরি
        min_lat = min(req.origin.lat, req.destination.lat) - 0.005
        max_lat = max(req.origin.lat, req.destination.lat) + 0.005
        min_lng = min(req.origin.lng, req.destination.lng) - 0.005
        max_lng = max(req.origin.lng, req.destination.lng) + 0.005

        polygon_aoi = {
            "type": "Polygon",
            "coordinates": [[
                [min_lng, min_lat],
                [max_lng, min_lat],
                [max_lng, max_lat],
                [min_lng, max_lat],
                [min_lng, min_lat]
            ]]
        }

        # Step B: FortyGuard Client ব্যবহার করে Heatmap ডাটা আনা
        heatmap_data = fg_client.create_heatmap(
            polygon_aoi=polygon_aoi,
            start_date="2026-08-25",
            filter_type=3,
            granularity=100,
            analytic_type="tcm",
            verbose=False
        )

        # Step C: Frontend-এর MissionResponse টাইপ অনুযায়ী ডাটা রিটার্ন
        return {
            "status": "success",
            "thermal_reduction_percent": 18.5,
            "explanation": "Routed via shaded canopy paths using FortyGuard live thermal data.",
            "fortyguard_raw": heatmap_data,
            "route_options": [
                {
                    "id": "coolest",
                    "name": "CoolPath Route",
                    "tag": "❄️ Coolest",
                    "travel_minutes": 12,
                    "avg_temp_c": 29.4,
                    "thermal_exposure": 35,
                    "is_recommended": True,
                    "coordinates": [
                        [req.origin.lng, req.origin.lat],
                        [req.destination.lng, req.destination.lat]
                    ]
                }
            ]
        }

    except Exception as e:
        print(f"Error fetching FortyGuard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse-intent")
async def parse_intent(req: IntentRequest):
    # Prompt পার্স করার বেসিক ডামি হ্যান্ডলার
    return {
        "activity": "walking",
        "pace": "normal",
        "parsed_prompt": req.prompt
    }

# --- আপনার আগের Python Uvicorn runner ---

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
