from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import BehaviorRequest, BehaviorResponse, HeatmapRequest, HeatmapResponse
from .services.analysis_service import build_behavior_response, build_heatmap_response

app = FastAPI(title="Time Structure Heatmap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:80",
        "http://127.0.0.1:80",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/analysis/heatmap", response_model=HeatmapResponse)
def heatmap(request: HeatmapRequest):
    try:
        return build_heatmap_response(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/analysis/behavior", response_model=BehaviorResponse)
def behavior(request: BehaviorRequest):
    try:
        return build_behavior_response(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


