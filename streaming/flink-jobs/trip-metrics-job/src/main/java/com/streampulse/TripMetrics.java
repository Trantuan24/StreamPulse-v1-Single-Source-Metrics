package com.streampulse;

import java.time.Instant;

/**
 * POJO class to hold the final aggregated metrics for a specific window and region.
 */
public class TripMetrics {

    private int regionId;
    private Instant windowStart;
    private Instant windowEnd;
    private long tripCount;
    private double avgFare;
    private double totalDistance;
    private double avgDuration;
    private double p50Duration;
    private double p95Duration;

    // Default constructor for Flink serialization
    public TripMetrics() {}

    // Getters and Setters
    public int getRegionId() {
        return regionId;
    }

    public void setRegionId(int regionId) {
        this.regionId = regionId;
    }

    public Instant getWindowStart() {
        return windowStart;
    }

    public void setWindowStart(Instant windowStart) {
        this.windowStart = windowStart;
    }

    public Instant getWindowEnd() {
        return windowEnd;
    }

    public void setWindowEnd(Instant windowEnd) {
        this.windowEnd = windowEnd;
    }

    public long getTripCount() {
        return tripCount;
    }

    public void setTripCount(long tripCount) {
        this.tripCount = tripCount;
    }

    public double getAvgFare() {
        return avgFare;
    }

    public void setAvgFare(double avgFare) {
        this.avgFare = avgFare;
    }

    public double getTotalDistance() {
        return totalDistance;
    }

    public void setTotalDistance(double totalDistance) {
        this.totalDistance = totalDistance;
    }

    public double getAvgDuration() {
        return avgDuration;
    }

    public void setAvgDuration(double avgDuration) {
        this.avgDuration = avgDuration;
    }

    public double getP50Duration() {
        return p50Duration;
    }

    public void setP50Duration(double p50Duration) {
        this.p50Duration = p50Duration;
    }

    public double getP95Duration() {
        return p95Duration;
    }

    public void setP95Duration(double p95Duration) {
        this.p95Duration = p95Duration;
    }

    @Override
    public String toString() {
        return "TripMetrics{" +
                "regionId=" + regionId +
                ", windowStart=" + windowStart +
                ", windowEnd=" + windowEnd +
                ", tripCount=" + tripCount +
                ", avgFare=" + String.format("%.2f", avgFare) +
                ", totalDistance=" + String.format("%.2f", totalDistance) +
                ", avgDuration=" + String.format("%.2f", avgDuration) +
                ", p50Duration=" + p50Duration +
                ", p95Duration=" + p95Duration +
                '}';
    }
}

