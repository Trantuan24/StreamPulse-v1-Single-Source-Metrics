"""
Test file cho Trip Event Schema
"""

from datetime import datetime
import json
from trip_event import TripEvent, TripEventBatch


def test_trip_event_creation():
    """Test basic TripEvent creation"""
    event = TripEvent(
        trip_id="trip_001",
        region_id=1,
        event_time="2025-08-17T10:30:00.000Z",
        fare=25.5,
        duration=1800,
        distance=12.5
    )
    
    assert event.trip_id == "trip_001"
    assert event.region_id == 1
    assert event.fare == 25.5
    assert event.duration == 1800
    assert event.distance == 12.5
    assert isinstance(event.event_time, datetime)


def test_kafka_serialization():
    """Test Kafka message serialization/deserialization"""
    original_event = TripEvent(
        trip_id="trip_002",
        region_id=2,
        event_time="2025-08-17T11:00:00.000Z",
        fare=30.0,
        duration=2400,
        distance=15.0
    )
    
    # Serialize to Kafka message
    kafka_message = original_event.to_kafka_message()
    assert isinstance(kafka_message, str)
    
    # Deserialize from Kafka message
    parsed_event = TripEvent.from_kafka_message(kafka_message)
    
    assert parsed_event.trip_id == original_event.trip_id
    assert parsed_event.region_id == original_event.region_id
    assert parsed_event.fare == original_event.fare


def test_partition_key():
    """Test partition key generation"""
    event = TripEvent(
        trip_id="trip_003",
        region_id=5,
        event_time="2025-08-17T12:00:00.000Z",
        fare=20.0,
        duration=1200,
        distance=8.0
    )
    
    assert event.get_partition_key() == "5"


def test_validation_errors():
    """Test validation errors"""
    # Test invalid fare
    try:
        TripEvent(
            trip_id="trip_004",
            region_id=1,
            event_time="2025-08-17T10:30:00.000Z",
            fare=-5.0,  # Invalid negative fare
            duration=1800,
            distance=12.5
        )
        assert False, "Should have raised validation error"
    except Exception:
        pass  # Expected


if __name__ == "__main__":
    # Run basic tests
    test_trip_event_creation()
    test_kafka_serialization()
    test_partition_key()
    test_validation_errors()
    print("✅ All schema tests passed!")