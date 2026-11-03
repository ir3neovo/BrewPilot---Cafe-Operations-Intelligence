
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.predict import predict_demand

app = FastAPI(
    title="Café Demand Forecasting API",
    description="Predict hourly beverage demand using ML",
    version="1.0.0"
)

# allow requests from future React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
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
    forecasts = []
    skipped_hours = []

    # recorded hours in our dataset range from 6 to 20
    for hour in range(6, 21):
        try:
            prediction = predict_demand(
                store=request.store,
                date=str(request.date),
                hour=hour
            )

            forecasts.append({
                "hour": hour,
                "predicted_drinks": prediction
            })

        except ValueError as e:
            skipped_hours.append({
                "hour": hour,
                "reason": str(e)
            })

    if not forecasts:
        raise HTTPException(
            status_code=400,
            detail=(
                skipped_hours[0]["reason"]
                if skipped_hours
                else "No forecast hours available"
            )
        )

    return {
        "store": request.store,
        "date": str(request.date),
        "forecasts": forecasts,
        "skipped_hours": skipped_hours
    }
