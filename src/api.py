import os
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.predict import predict_demand, predict_day, forecast_options

app = FastAPI(
    title="Café Demand Forecasting API",
    description="Predict hourly beverage demand using ML",
    version="1.0.0"
)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

# Public frontend origin, provided during deployment
frontend_origin = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")

if frontend_origin:
    allowed_origins.append(frontend_origin)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)


# request model for prediction endpoint
class PredictionRequest(BaseModel):
    store: str
    date: date
    hour: int = Field(ge=0, le=23)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
def predict(request: PredictionRequest):
    try:
        prediction = predict_demand(
            store=request.store,
            date=str(request.date),
            hour=request.hour
        )

        return {
            "store": request.store,
            "date": str(request.date),
            "hour": request.hour,
            "predicted_drinks": prediction
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e


# request body for daily predictions
class DayPredictionRequest(BaseModel):
    store: str
    date: date


@app.post("/predict/day")
def predict_full_day(request: DayPredictionRequest):
    try:
        return predict_day(request.store, str(request.date))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/forecast/options")
def get_forecast_options():
    return forecast_options()


@app.get("/replay/status")
def replay_status():
    from src.sales import DATA_PATH
    from src.replay import status
    if DATA_PATH.name != "history.csv" or not (DATA_PATH.parent / "replay.json").exists():
        return {"enabled": False}
    return status(DATA_PATH.parent)
