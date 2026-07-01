"""
Ground Hazard Tracker - FastAPI Backend (Updated Prototype)
Python 3.11+, FastAPI, SQLModel, local SQLite.
"""
import os
import math
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select

# ---------------------------------------------------------------------------
# Config / paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "hazards.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------
class HazardReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reporter_name: str = Field(default="Anonymous")
    issue_type: str = Field(index=True)
    description: str
    latitude: float
    longitude: float
    image_path: str
    is_solved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HazardReply(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hazard_id: int = Field(index=True)
    username: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Helpers (Distance & Compass Bearing)
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    d_lon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    y = math.sin(d_lon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon)
    bearing = math.degrees(math.atan2(y, x))
    bearing = (bearing + 360) % 360
    cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((bearing + 22.5) / 45) % 8
    return cardinals[idx]


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Ground Hazard Tracker")


@app.on_event("startup")
def on_startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    create_db_and_tables()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/report")
async def create_report(
    reporter_name: str = Form(...),
    issue_type: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image_file: UploadFile = File(...),
):
    ext = os.path.splitext(image_file.filename or "")[1] or ".jpg"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"{timestamp}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as out_file:
        shutil.copyfileobj(image_file.file, out_file)

    image_path = f"/static/uploads/{safe_name}"

    with Session(engine) as session:
        report = HazardReport(
            reporter_name=reporter_name,
            issue_type=issue_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            image_path=image_path,
            is_solved=False
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        report_id = report.id

    return {"success": True, "id": report_id, "image_path": image_path}


@app.get("/api/feed")
def get_feed(
    user_lat: float = Query(...),
    user_lon: float = Query(...),
    radius_km: float = Query(5.0),
):
    with Session(engine) as session:
        reports = session.exec(select(HazardReport)).all()
        
    payload: List[dict] = []
    for r in reports:
        dist = haversine_km(user_lat, user_lon, r.latitude, r.longitude)
        compass_dir = calculate_bearing(user_lat, user_lon, r.latitude, r.longitude)
        
        with Session(engine) as session:
            replies = session.exec(
                select(HazardReply).where(HazardReply.hazard_id == r.id).order_by(HazardReply.created_at.asc())
            ).all()

        reply_list = [
            {
                "id": rep.id,
                "username": rep.username,
                "message": rep.message,
                "created_at": rep.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for rep in replies
        ]

        payload.append(
            {
                "id": r.id,
                "reporter_name": r.reporter_name,
                "issue_type": r.issue_type,
                "description": r.description,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "image_path": r.image_path,
                "is_solved": r.is_solved,
                "distance_km": round(dist, 2),
                "compass_direction": compass_dir,
                "is_near": (dist <= radius_km) and (not r.is_solved),
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
                "replies": reply_list
            }
        )

    payload.sort(key=lambda x: x["distance_km"])
    return payload


@app.post("/api/hazard/{hazard_id}/solve")
def mark_solved(hazard_id: int):
    with Session(engine) as session:
        report = session.get(HazardReport, hazard_id)
        if not report:
            raise HTTPException(status_code=404, detail="Hazard not found")
        report.is_solved = True
        session.add(report)
        session.commit()
    return {"success": True}


@app.post("/api/hazard/{hazard_id}/reply")
def post_reply(hazard_id: int, username: str = Form(...), message: str = Form(...)):
    with Session(engine) as session:
        report = session.get(HazardReport, hazard_id)
        if not report:
            raise HTTPException(status_code=404, detail="Hazard not found")
        
        reply = HazardReply(hazard_id=hazard_id, username=username, message=message)
        session.add(reply)
        session.commit()
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)