"""
Ground Hazard Tracker - FastAPI Backend (Prototype)
Python 3.11+, FastAPI, SQLModel, local SQLite.
"""
import os
import math
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, Query
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
# Database model
# ---------------------------------------------------------------------------
class HazardReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    issue_type: str = Field(index=True)
    description: str
    latitude: float
    longitude: float
    image_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Haversine distance helper (returns kilometers)
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


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
            issue_type=issue_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            image_path=image_path,
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
        payload.append(
            {
                "id": r.id,
                "issue_type": r.issue_type,
                "description": r.description,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "image_path": r.image_path,
                "distance_km": round(dist, 2),
                "is_near": dist <= radius_km,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    payload.sort(key=lambda x: x["distance_km"])
    return payload


# ---------------------------------------------------------------------------
# Local / Replit entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
