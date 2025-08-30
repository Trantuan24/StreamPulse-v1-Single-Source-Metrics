package com.streampulse;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Objects;

/**
 * POJO representing a trip event from Kafka with event-time support
 */
public class TripEvent {

    @JsonProperty("trip_id")
    private String tripId;

    @JsonProperty("region_id")
    private Integer regionId;

    @JsonProperty("event_time")
    private String eventTimeString;

    private LocalDateTime eventTime;
    
    @JsonProperty("fare")
    private Double fare;
    
    @JsonProperty("duration")
    private Integer duration;
    
    @JsonProperty("distance")
    private Double distance;
    
    // Default constructor (required for Jackson)
    public TripEvent() {}
    
    // Constructor with all fields
    public TripEvent(String tripId, Integer regionId, LocalDateTime eventTime,
                     Double fare, Integer duration, Double distance) {
        this.tripId = tripId;
        this.regionId = regionId;
        this.eventTime = eventTime;
        this.fare = fare;
        this.duration = duration;
        this.distance = distance;
    }

    // Getters and Setters
    public String getTripId() { return tripId; }
    public void setTripId(String tripId) { this.tripId = tripId; }

    public Integer getRegionId() { return regionId; }
    public void setRegionId(Integer regionId) { this.regionId = regionId; }

    public LocalDateTime getEventTime() {
        if (eventTime == null && eventTimeString != null) {
            try {
                // Parse ISO timestamp with timezone
                java.time.Instant instant = java.time.Instant.parse(eventTimeString);
                eventTime = LocalDateTime.ofInstant(instant, ZoneOffset.UTC);
            } catch (Exception e) {
                try {
                    // Handle various timezone formats
                    String cleanTime = eventTimeString;
                    if (cleanTime.endsWith("+00:00Z")) {
                        cleanTime = cleanTime.replace("+00:00Z", "Z");
                    } else if (cleanTime.endsWith("+00:00")) {
                        cleanTime = cleanTime.replace("+00:00", "Z");
                    } else if (!cleanTime.endsWith("Z")) {
                        cleanTime = cleanTime + "Z";
                    }

                    java.time.Instant instant = java.time.Instant.parse(cleanTime);
                    eventTime = LocalDateTime.ofInstant(instant, ZoneOffset.UTC);
                } catch (Exception e2) {
                    // Fallback to current time
                    eventTime = LocalDateTime.now();
                }
            }
        }
        return eventTime;
    }

    public long getEventTimeMillis() {
        return getEventTime().toInstant(ZoneOffset.UTC).toEpochMilli();
    }

    public void setEventTime(LocalDateTime eventTime) { this.eventTime = eventTime; }

    public String getEventTimeString() { return eventTimeString; }
    public void setEventTimeString(String eventTimeString) {
        this.eventTimeString = eventTimeString;
        this.eventTime = null;
    }
    
    public Double getFare() { return fare; }
    public void setFare(Double fare) { this.fare = fare; }
    
    public Integer getDuration() { return duration; }
    public void setDuration(Integer duration) { this.duration = duration; }
    
    public Double getDistance() { return distance; }
    public void setDistance(Double distance) { this.distance = distance; }
    
    @Override
    public String toString() {
        return "TripEvent{" +
                "tripId='" + tripId + '\'' +
                ", regionId=" + regionId +
                ", eventTime=" + eventTime +
                ", fare=" + fare +
                ", duration=" + duration +
                ", distance=" + distance +
                '}';
    }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        TripEvent tripEvent = (TripEvent) o;
        return Objects.equals(tripId, tripEvent.tripId);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(tripId);
    }
}