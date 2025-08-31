"""
Trip Event Schema Definition for StreamPulse v1
Author: Trần Duy Tuấn
Date: 2025-08-17
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import json


class TripEvent(BaseModel):
    """
    Trip Event schema cho StreamPulse v1 pipeline
    
    Represents a single trip/taxi event với event-time processing support
    """
    
    trip_id: str = Field(
        ..., 
        description="Unique identifier cho trip",
        min_length=1,
        max_length=50
    )
    
    region_id: int = Field(
        ..., 
        description="Region identifier cho geographical partitioning",
        ge=1,  # >= 1
        le=100  # <= 100 (giả sử có tối đa 100 regions)
    )
    
    event_time: datetime = Field(
        ..., 
        description="Event timestamp (ISO 8601 format) cho event-time processing"
    )
    
    fare: float = Field(
        ..., 
        description="Trip fare in USD",
        ge=0.0,  # >= 0
        le=1000.0  # <= 1000 (reasonable max fare)
    )
    
    duration: int = Field(
        ..., 
        description="Trip duration in seconds",
        ge=60,  # >= 1 minute
        le=7200  # <= 2 hours
    )
    
    distance: float = Field(
        ..., 
        description="Trip distance in kilometers",
        ge=0.1,  # >= 0.1 km
        le=200.0  # <= 200 km
    )
    
    @validator('event_time', pre=True)
    def parse_event_time(cls, v):
        """Parse event_time từ string hoặc datetime object"""
        if isinstance(v, str):
            try:
                # Support multiple datetime formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO with microseconds
                    "%Y-%m-%dT%H:%M:%SZ",     # ISO without microseconds
                    "%Y-%m-%d %H:%M:%S",      # Simple format
                ]:
                    try:
                        return datetime.strptime(v, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Unable to parse datetime: {v}")
            except Exception as e:
                raise ValueError(f"Invalid datetime format: {v}, error: {e}")
        return v
    
    @validator('trip_id')
    def validate_trip_id(cls, v):
        """Validate trip_id format"""
        if not v or not v.strip():
            raise ValueError("trip_id cannot be empty")
        return v.strip()
    
    def to_kafka_message(self) -> str:
        """
        Convert TripEvent to JSON string cho Kafka message
        
        Returns:
            JSON string với event_time trong ISO format
        """
        data = self.dict()
        # Convert datetime to ISO string cho Kafka
        data['event_time'] = self.event_time.isoformat() + 'Z'
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_kafka_message(cls, message: str) -> 'TripEvent':
        """
        Parse TripEvent từ Kafka JSON message
        
        Args:
            message: JSON string từ Kafka
            
        Returns:
            TripEvent object
        """
        try:
            data = json.loads(message)
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse Kafka message: {e}")
    
    def get_partition_key(self) -> str:
        """
        Get partition key cho Kafka partitioning
        
        Returns:
            String key based on region_id
        """
        return str(self.region_id)
    
    class Config:
        """Pydantic configuration"""
        # Allow datetime objects
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }
        # Example for documentation
        schema_extra = {
            "example": {
                "trip_id": "trip_001",
                "region_id": 1,
                "event_time": "2025-08-17T10:30:00.000Z",
                "fare": 25.5,
                "duration": 1800,
                "distance": 12.5
            }
        }


class TripEventBatch(BaseModel):
    """
    Batch of trip events cho bulk processing
    """
    events: list[TripEvent] = Field(
        ..., 
        description="List of trip events"
    )
    
    batch_id: Optional[str] = Field(
        None, 
        description="Optional batch identifier"
    )
    
    def __len__(self) -> int:
        return len(self.events)
    
    def get_events_by_region(self, region_id: int) -> list[TripEvent]:
        """Filter events by region_id"""
        return [event for event in self.events if event.region_id == region_id]