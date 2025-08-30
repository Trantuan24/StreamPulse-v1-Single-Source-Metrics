#!/usr/bin/env python3
"""
TripStream Analytics - FastAPI Serving Layer
Provides REST API endpoints to query real-time trip metrics from Redis.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
import redis.asyncio as redis
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable for Redis connection pool
redis_pool = None

def get_redis_pool():
    global redis_pool
    if redis_pool is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
        redis_pool = redis.ConnectionPool(host=redis_host, port=redis_port, db=0, decode_responses=True)
    return redis_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis connection
    global redis_pool
    redis_pool = get_redis_pool()
    # Yield control to the application
    yield
    # Shutdown: Close Redis connection
    if redis_pool:
        logger.info("Closing Redis connection pool.")
        await redis_pool.disconnect()

# FastAPI app initialization with lifespan manager
app = FastAPI(
    title="TripStream Analytics API",
    description="Real-time trip metrics API for Level 1 pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class TripMetrics(BaseModel):
    """Response model for trip metrics."""
    region_id: int = Field(alias='regionId')
    window_start: str = Field(alias='windowStart')
    window_end: str = Field(alias='windowEnd')
    trip_count: int = Field(alias='tripCount')
    avg_fare: float = Field(alias='avgFare')
    total_distance: float = Field(alias='totalDistance')
    avg_duration: float = Field(alias='avgDuration')
    p50_duration: Optional[float] = Field(alias='p50Duration', default=None)
    p95_duration: Optional[float] = Field(alias='p95Duration', default=None)

    @field_validator('window_start', 'window_end', mode='before')
    @classmethod
    def format_timestamp(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            # Return in ISO 8601 format with 'Z' for UTC
            return datetime.fromtimestamp(v, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
        return str(v)

    class Config:
        populate_by_name = True

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    services: Dict[str, str]

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify service status and dependencies."""
    redis_status = "disconnected"
    try:
        r = redis.Redis(connection_pool=redis_pool)
        if await r.ping():
            redis_status = "connected"
        else:
            redis_status = "connection_failed"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "error"

    api_status = "healthy" if redis_status == "connected" else "degraded"

    return HealthResponse(
        status=api_status,
        timestamp=datetime.utcnow().isoformat(),
        services={
            "redis": redis_status,
            "api": "running"
        }
    )

@app.get("/metrics/region/{region_id}", response_model=TripMetrics)
async def get_region_metrics(
    region_id: int,
    window: str = Query("1m", description="Time window (currently only '1m' is supported)")
):
    """
    Get trip metrics for a specific region and time window.
    """
    if window != "1m":
        raise HTTPException(status_code=400, detail="Only '1m' window is supported at the moment.")

    try:
        r = redis.Redis(connection_pool=redis_pool)
        # Use SCAN to find the latest window key for the region without blocking the server.
        key_pattern = f"region:{region_id}:window:*"

        # Find all keys matching the pattern.
        # Note: in a production system with millions of keys, this could be slow.
        # A better approach might be to use a sorted set to track latest keys.
        # For this project, SCAN is sufficient.
        keys = [key async for key in r.scan_iter(match=key_pattern)]

        if not keys:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics found for region {region_id}. No keys available."
            )

        # The key with the highest timestamp is the latest one.
        latest_key = max(keys)
        logger.info(f"Found latest key for region {region_id}: {latest_key}")

        data = await r.get(latest_key)

        if data:
            # Data in Redis is stored as a JSON string, so we parse it.
            metrics_data = json.loads(data)
            # Pydantic model will handle aliasing and validation
            return TripMetrics.model_validate(metrics_data)
        else:
            # This case is unlikely if the key was just found, but it's good practice.
            raise HTTPException(
                status_code=404,
                detail=f"Metrics data for key {latest_key} disappeared."
            )
    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTPException to be handled by FastAPI
    except Exception as e:
        logger.error(f"Error retrieving metrics for region {region_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching metrics.")

@app.get("/metrics/regions/top")
async def get_top_regions(
    window: str = Query("1m", description="Time window"),
    metric: str = Query("trip_count", description="Metric to rank by"),
    limit: int = Query(10, description="Number of top regions to return")
):
    """
    Get top regions by specified metric.

    Args:
        window: Time window size
        metric: Metric to rank by (trip_count, avg_fare, total_distance)
        limit: Number of regions to return

    Returns:
        List of regions ranked by the specified metric
    """
    # TODO: Implement top regions query
    # 1. Scan Redis for all region keys in the time window
    # 2. Retrieve metrics for all regions
    # 3. Sort by specified metric
    # 4. Return top N regions

    raise HTTPException(status_code=501, detail="Implementation needed")

@app.get("/metrics/timeline/{region_id}")
async def get_region_timeline(
    region_id: int,
    hours: int = Query(1, description="Number of hours of history"),
    window: str = Query("1m", description="Window size")
):
    """
    Get historical timeline of metrics for a region.

    Args:
        region_id: Region identifier
        hours: Number of hours of history to retrieve
        window: Window size for aggregation

    Returns:
        Time series data for the specified region
    """
    # TODO: Implement timeline query
    # 1. Calculate time range based on hours parameter
    # 2. Generate list of window keys for the time range
    # 3. Retrieve metrics for each window
    # 4. Return time series data

    raise HTTPException(status_code=501, detail="Implementation needed")



# Instrument the app with default metrics.
# This will expose a /metrics endpoint.
Instrumentator().instrument(app).expose(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
Implementation Notes:

1. Redis Key Patterns:
   - Metrics: region:{region_id}:window:{window_start_timestamp}
   - TTL: 1 hour for metrics data
   - JSON format for metric values

2. Error Handling:
   - 404 for missing data
   - 500 for Redis connection errors
   - 400 for invalid parameters
   - Proper logging for debugging

3. Performance Considerations:
   - Connection pooling for Redis
   - Caching for frequently accessed data
   - Async operations where possible
   - Request/response compression

4. Monitoring:
   - Request metrics for Prometheus
   - Error rate tracking
   - Response time monitoring
   - Redis connection health

5. Security (for production):
   - Rate limiting
   - Input validation
   - Authentication/authorization
   - CORS configuration

API Usage Examples:
  # Get latest 1-minute metrics for region 1
  GET /metrics/region/1?window=1m

  # Get previous 5-minute window for region 2
  GET /metrics/region/2?window=5m&offset=1

  # Get top 5 regions by trip count
  GET /metrics/regions/top?metric=trip_count&limit=5

  # Get 2-hour timeline for region 1
  GET /metrics/timeline/1?hours=2&window=1m
"""
