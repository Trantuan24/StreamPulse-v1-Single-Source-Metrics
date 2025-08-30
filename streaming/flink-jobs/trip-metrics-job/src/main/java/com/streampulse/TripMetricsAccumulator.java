package com.streampulse;

import java.util.ArrayList;
import java.util.List;

/**
 * Accumulator to hold the intermediate state for the aggregation.
 * This is where we store running totals and lists of values needed for calculations.
 */
public class TripMetricsAccumulator {

    public long count = 0;
    public double totalFare = 0.0;
    public double totalDistance = 0.0;
    public long totalDuration = 0;
    public List<Integer> durationList = new ArrayList<>();

}

