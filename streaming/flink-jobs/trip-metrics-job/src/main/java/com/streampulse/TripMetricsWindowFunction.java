package com.streampulse;

import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

import java.time.Instant;

/**
 * A ProcessWindowFunction that enriches the aggregated TripMetrics with window and key information.
 */
public class TripMetricsWindowFunction extends ProcessWindowFunction<TripMetrics, TripMetrics, Integer, TimeWindow> {

    @Override
    public void process(Integer regionId, Context context, Iterable<TripMetrics> input, Collector<TripMetrics> out) {
        // The AggregateFunction has already done the heavy lifting. 
        // We expect exactly one TripMetrics object per window.
        TripMetrics metrics = input.iterator().next();

        // Enrich with window and key information
        metrics.setRegionId(regionId);
        metrics.setWindowStart(Instant.ofEpochMilli(context.window().getStart()));
        metrics.setWindowEnd(Instant.ofEpochMilli(context.window().getEnd()));

        out.collect(metrics);
    }
}

