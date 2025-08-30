package com.streampulse;

import org.apache.flink.api.common.functions.AggregateFunction;

import java.util.Collections;

/**
 * Implements the core aggregation logic for trip metrics.
 * This function is applied to each window of events.
 */
public class TripMetricsAggregator implements AggregateFunction<TripEvent, TripMetricsAccumulator, TripMetrics> {

    @Override
    public TripMetricsAccumulator createAccumulator() {
        return new TripMetricsAccumulator();
    }

    @Override
    public TripMetricsAccumulator add(TripEvent value, TripMetricsAccumulator accumulator) {
        accumulator.count++;
        accumulator.totalFare += value.getFare();
        accumulator.totalDistance += value.getDistance();
        accumulator.totalDuration += value.getDuration();
        accumulator.durationList.add(value.getDuration());
        return accumulator;
    }

    @Override
    public TripMetrics getResult(TripMetricsAccumulator accumulator) {
        TripMetrics metrics = new TripMetrics();
        if (accumulator.count == 0) {
            // Handle empty window
            metrics.setTripCount(0);
            metrics.setAvgFare(0.0);
            metrics.setTotalDistance(0.0);
            metrics.setAvgDuration(0.0);
            metrics.setP50Duration(0.0);
            metrics.setP95Duration(0.0);
            return metrics;
        }

        metrics.setTripCount(accumulator.count);
        metrics.setAvgFare(accumulator.totalFare / accumulator.count);
        metrics.setTotalDistance(accumulator.totalDistance);
        metrics.setAvgDuration((double) accumulator.totalDuration / accumulator.count);

        // Calculate percentiles
        Collections.sort(accumulator.durationList);
        metrics.setP50Duration(getPercentile(accumulator.durationList, 50.0));
        metrics.setP95Duration(getPercentile(accumulator.durationList, 95.0));

        return metrics;
    }

    @Override
    public TripMetricsAccumulator merge(TripMetricsAccumulator a, TripMetricsAccumulator b) {
        a.count += b.count;
        a.totalFare += b.totalFare;
        a.totalDistance += b.totalDistance;
        a.totalDuration += b.totalDuration;
        a.durationList.addAll(b.durationList);
        return a;
    }

    private double getPercentile(java.util.List<Integer> sortedList, double percentile) {
        if (sortedList.isEmpty()) {
            return 0.0;
        }
        int index = (int) Math.ceil(percentile / 100.0 * sortedList.size());
        return sortedList.get(Math.max(0, index - 1));
    }
}

