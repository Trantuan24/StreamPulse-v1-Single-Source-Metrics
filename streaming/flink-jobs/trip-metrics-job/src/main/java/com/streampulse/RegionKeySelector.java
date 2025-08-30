package com.streampulse;

import org.apache.flink.api.java.functions.KeySelector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Enhanced KeySelector for region-based partitioning with monitoring
 * 
 * This selector extracts region_id from TripEvent and provides
 * detailed logging and metrics for key distribution analysis.
 */
public class RegionKeySelector implements KeySelector<TripEvent, Integer> {
    
    private static final Logger LOG = LoggerFactory.getLogger(RegionKeySelector.class);
    
    // Counters for monitoring key distribution
    private final AtomicLong totalEvents = new AtomicLong(0);
    private final AtomicLong nullRegionEvents = new AtomicLong(0);
    
    // Log every N events to avoid spam
    private static final long LOG_INTERVAL = 100;
    
    @Override
    public Integer getKey(TripEvent tripEvent) throws Exception {
        long eventCount = totalEvents.incrementAndGet();
        
        // Validate region_id
        Integer regionId = tripEvent.getRegionId();
        
        if (regionId == null) {
            long nullCount = nullRegionEvents.incrementAndGet();
            LOG.warn("🚨 Null region_id found in trip: {} (total null: {})", 
                    tripEvent.getTripId(), nullCount);
            // Return default region for null values
            return -1;
        }
        
        // Validate region_id range
        if (regionId < 1 || regionId > 100) {
            LOG.warn("🚨 Invalid region_id: {} for trip: {}", regionId, tripEvent.getTripId());
            // Return normalized region_id
            return Math.max(1, Math.min(100, Math.abs(regionId)));
        }
        
        // Periodic logging for monitoring
        if (eventCount % LOG_INTERVAL == 0) {
            LOG.info("📊 Key distribution progress: {} events processed, region_id: {}, null_regions: {}", 
                    eventCount, regionId, nullRegionEvents.get());
        }
        
        return regionId;
    }
    
    /**
     * Get statistics for monitoring
     */
    public long getTotalEvents() {
        return totalEvents.get();
    }
    
    public long getNullRegionEvents() {
        return nullRegionEvents.get();
    }
    
    /**
     * Reset counters (useful for testing)
     */
    public void resetCounters() {
        totalEvents.set(0);
        nullRegionEvents.set(0);
    }
}
