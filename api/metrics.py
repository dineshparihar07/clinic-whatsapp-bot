from fastapi import APIRouter
from lib.monitoring import metrics

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    return {
        "status": "ok",
        "metrics": metrics.get_stats(),
        "last_error": metrics.last_error
    }

@router.get("/metrics/counters")
async def get_counters():
    """Get counter metrics"""
    return {
        "counters": metrics.counters.copy()
    }

@router.get("/metrics/timings")
async def get_timings():
    """Get timing metrics"""
    stats = metrics.get_stats()
    return {
        "timings": stats.get("timings", {})
    }

@router.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics"""
    metrics.counters = {}
    metrics.timings = {}
    metrics.last_error = None
    return {"status": "ok", "message": "Metrics reset"}
