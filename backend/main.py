
from datetime import datetime
from typing import Literal
import asyncio
from contextlib import asynccontextmanager
from bidholi_db_pool import get_pool, close_pool
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from psycopg import Error as DatabaseError
from psycopg.errors import UniqueViolation
from bidholi_routing import router as bidholi_router
from bidholi_pedestrian_routing import (
    router as pedestrian_router
)
from database import (
    get_connection,
    get_locations,
    get_edges,
    save_crowd_report,
    get_crowd_reports,
    get_current_crowd_levels,
    get_analytics_summary,
    get_crowd_distribution,
    get_analytics_hotspots,
    get_hourly_crowd_analytics,
    get_user_by_email,
    create_student,
)

from routing import find_shortest_route

from ml.predict import (
    predict_crowd,
    predict_all_locations,
)

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)


# ============================================================
# CampusFlow Phase 9.9.2.6
# PostgreSQL Pool Lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize the Bidholi PostgreSQL connection pool
    at application startup and close it on shutdown.

    Other CampusFlow database operations remain unchanged.
    """

    # Pool initialization is synchronous, so run it
    # outside the event loop.
    await asyncio.to_thread(get_pool)

    print("CampusFlow: Bidholi PostgreSQL pool ready")

    try:
        yield

    finally:
        await asyncio.to_thread(close_pool)
        print("CampusFlow: Bidholi PostgreSQL pool closed")


app = FastAPI(
    title="CampusFlow API",
    description=(
        "Campus Navigation, Crowd Prediction, "
        "JWT Authentication and Admin Analytics"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# UPES Bidholi Navigation Routes
app.include_router(bidholi_router)
app.include_router(pedestrian_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# =====================================
# REQUEST MODELS
# =====================================

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    mode: Literal["shortest", "smart", "ml"] = "smart"
    departure_time: datetime | None = None


class CrowdReportRequest(BaseModel):
    location_id: str = Field(min_length=1)
    crowd_level: Literal["low", "medium", "high"]


class CrowdPredictionRequest(BaseModel):
    location_id: str = Field(min_length=1)
    prediction_time: datetime


def public_user(user):
    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
    }


# =====================================
# AUTHENTICATION
# =====================================

@app.post("/auth/register", status_code=201)
def register(request: RegisterRequest):
    email = str(request.email).strip().lower()
    name = request.full_name.strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=422,
            detail="Full name must contain at least 2 characters",
        )

    # Public registration never accepts an admin role.
    password_hash = hash_password(request.password)

    try:
        user = create_student(
            full_name=name,
            email=email,
            password_hash=password_hash,
        )

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        )

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Registration database unavailable",
        )

    return {
        "message": "Student account created successfully",
        "user": public_user(user),
    }


@app.post("/auth/login")
def login(request: LoginRequest):
    try:
        user = get_user_by_email(str(request.email))

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Authentication database unavailable",
        )

    # Verify password and account status.
    # Never return the stored password hash.
    if (
        user is None
        or not user["is_active"]
        or not verify_password(
            request.password,
            user["password_hash"],
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": public_user(user),
    }


@app.get("/auth/me")
def current_user_endpoint(
    user=Depends(get_current_user),
):
    return public_user(user)


# =====================================
# BASIC CAMPUS ENDPOINTS
# =====================================

@app.get("/")
def home():
    return {
        "message": "Welcome to CampusFlow API",
        "status": "running",
        "version": "2.0.0",
    }


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


@app.get("/locations")
def locations_endpoint():
    try:
        return get_locations()

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve locations",
        )


@app.get("/edges")
def edges_endpoint():
    try:
        return get_edges()

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve paths",
        )


# =====================================
# CROWD REPORTING
# =====================================

@app.get("/crowd/current")
def current_crowd_endpoint():
    try:
        return get_current_crowd_levels()

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve crowd levels",
        )


@app.get("/crowd/reports")
def crowd_reports_endpoint():
    try:
        return get_crowd_reports()

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve crowd reports",
        )


@app.post("/crowd/report", status_code=201)
def submit_crowd_report(
    request: CrowdReportRequest,
    user=Depends(get_current_user),
):
    try:
        locations = get_locations()

        valid_ids = {
            loc["id"]
            for loc in locations
        }

        if request.location_id not in valid_ids:
            raise HTTPException(
                status_code=400,
                detail="Invalid campus location",
            )

        report = save_crowd_report(
            request.location_id,
            request.crowd_level,
        )

        return {
            "message": "Crowd report submitted successfully",
            "report": report,
        }

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


# =====================================
# ML CROWD PREDICTION
# =====================================

@app.post("/crowd/predict")
def predict_crowd_endpoint(
    request: CrowdPredictionRequest,
):
    try:
        locations = get_locations()

        valid_ids = {
            loc["id"]
            for loc in locations
        }

        if request.location_id not in valid_ids:
            raise HTTPException(
                status_code=400,
                detail="Invalid campus location",
            )

        return predict_crowd(
            request.location_id,
            request.prediction_time,
        )

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# =====================================
# DIJKSTRA / ML ROUTING
# =====================================

@app.post("/routes/recommend")
def recommend_route(request: RouteRequest):
    try:
        locations = get_locations()
        edges = get_edges()

        valid_ids = {
            loc["id"]
            for loc in locations
        }

        if (
            request.source not in valid_ids
            or request.destination not in valid_ids
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid source or destination",
            )

        if request.source == request.destination:
            raise HTTPException(
                status_code=400,
                detail="Select different locations",
            )

        if request.mode == "shortest":
            crowd_levels = {}
            algorithm_mode = "shortest"
            crowd_source = "none"

        elif request.mode == "smart":
            crowd_levels = get_current_crowd_levels()
            algorithm_mode = "smart"
            crowd_source = "live_reports"

        else:
            if request.departure_time is None:
                raise HTTPException(
                    status_code=400,
                    detail="Departure time required for ML routing",
                )

            crowd_levels = predict_all_locations(
                locations,
                request.departure_time,
            )

            algorithm_mode = "smart"
            crowd_source = "ml_prediction"

        result = find_shortest_route(
            start=request.source,
            end=request.destination,
            locations=locations,
            edges=edges,
            crowd_levels=crowd_levels,
            mode=algorithm_mode,
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="No route found",
            )

        result["mode"] = request.mode
        result["crowd_source"] = crowd_source
        result["crowd_levels_used"] = crowd_levels

        if request.mode == "ml":
            result["departure_time"] = (
                request.departure_time.isoformat()
            )
            result["prediction_source"] = (
                "synthetic_training_data"
            )

        return result

    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# =====================================
# PROTECTED ADMIN ANALYTICS
# =====================================

@app.get("/analytics/summary")
def analytics_summary(
    admin=Depends(require_admin),
):
    try:
        return get_analytics_summary()
    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Analytics unavailable",
        )


@app.get("/analytics/distribution")
def analytics_distribution(
    admin=Depends(require_admin),
):
    try:
        return get_crowd_distribution()
    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Analytics unavailable",
        )


@app.get("/analytics/hotspots")
def analytics_hotspots(
    admin=Depends(require_admin),
):
    try:
        return get_analytics_hotspots()
    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Analytics unavailable",
        )


@app.get("/analytics/hourly")
def analytics_hourly(
    admin=Depends(require_admin),
):
    try:
        return get_hourly_crowd_analytics()
    except DatabaseError:
        raise HTTPException(
            status_code=503,
            detail="Analytics unavailable",
        )
