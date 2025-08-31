package com.streampulse;

import org.junit.Test;
import static org.junit.Assert.*;
import java.time.LocalDateTime;

public class TripMetricsAggregatorTest {

    private final TripMetricsAggregator aggregator = new TripMetricsAggregator();

    @Test
    public void testCreateAccumulator() {
        TripMetricsAccumulator acc = aggregator.createAccumulator();
        assertNotNull(acc);
        assertEquals(0, acc.getCount());
        assertEquals(0.0, acc.getFareSum(), 0.0);
        assertEquals(0.0, acc.getDistanceSum(), 0.0);
        assertEquals(0, acc.getDurationSum());
        assertTrue(acc.getDurationList().isEmpty());
    }

    @Test
    public void testAdd() {
        TripMetricsAccumulator acc = aggregator.createAccumulator();
        TripEvent event = new TripEvent("t1", 1, LocalDateTime.now(), 10.5, 120, 5.5);

        aggregator.add(event, acc);

        assertEquals(1, acc.getCount());
        assertEquals(10.5, acc.getFareSum(), 0.0);
        assertEquals(5.5, acc.getDistanceSum(), 0.0);
        assertEquals(120, acc.getDurationSum());
        assertEquals(1, acc.getDurationList().size());
        assertEquals(Integer.valueOf(120), acc.getDurationList().get(0));
    }

    @Test
    public void testGetResult() {
        TripMetricsAccumulator acc = aggregator.createAccumulator();
        aggregator.add(new TripEvent("t1", 1, LocalDateTime.now(), 10.0, 100, 5.0), acc);
        aggregator.add(new TripEvent("t2", 1, LocalDateTime.now(), 20.0, 200, 10.0), acc);

        TripMetrics result = aggregator.getResult(acc);

        assertEquals(2, result.getTripCount());
        assertEquals(15.0, result.getAvgFare(), 0.0);
        assertEquals(15.0, result.getTotalDistance(), 0.0);
        assertEquals(150.0, result.getAvgDuration(), 0.0);
        assertEquals(100.0, result.getP50Duration(), 0.0);
        assertEquals(200.0, result.getP95Duration(), 0.0);
    }

    @Test
    public void testMerge() {
        TripMetricsAccumulator acc1 = aggregator.createAccumulator();
        aggregator.add(new TripEvent("t1", 1, LocalDateTime.now(), 10.0, 100, 5.0), acc1);

        TripMetricsAccumulator acc2 = aggregator.createAccumulator();
        aggregator.add(new TripEvent("t2", 1, LocalDateTime.now(), 20.0, 200, 10.0), acc2);

        TripMetricsAccumulator mergedAcc = aggregator.merge(acc1, acc2);

        assertEquals(2, mergedAcc.getCount());
        assertEquals(30.0, mergedAcc.getFareSum(), 0.0);
        assertEquals(15.0, mergedAcc.getDistanceSum(), 0.0);
        assertEquals(300, mergedAcc.getDurationSum());
        assertEquals(2, mergedAcc.getDurationList().size());
    }

    @Test
    public void testGetResultWithEmptyAccumulator() {
        TripMetricsAccumulator acc = aggregator.createAccumulator();
        TripMetrics result = aggregator.getResult(acc);

        assertEquals(0, result.getTripCount());
        assertEquals(0.0, result.getAvgFare(), 0.0);
        assertEquals(0.0, result.getTotalDistance(), 0.0);
        assertEquals(0.0, result.getAvgDuration(), 0.0);
        assertEquals(0.0, result.getP50Duration(), 0.0);
        assertEquals(0.0, result.getP95Duration(), 0.0);
    }
}

