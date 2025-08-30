package com.streampulse;

import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Monitor for tracking window assignment and event processing
 * 
 * This function logs detailed information about how events are
 * assigned to windows and tracks timing information.
 */
public class WindowAssignmentMonitor extends ProcessFunction<TripEvent, TripEvent> {
    
    private static final Logger LOG = LoggerFactory.getLogger(WindowAssignmentMonitor.class);
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    
    private final AtomicLong processedEvents = new AtomicLong(0);
    private static final long LOG_INTERVAL = 50;
    
    @Override
    public void processElement(TripEvent tripEvent, Context context, Collector<TripEvent> collector) throws Exception {
        long eventCount = processedEvents.incrementAndGet();
        
        // Get current processing time and event time
        long processingTime = context.timerService().currentProcessingTime();
        long eventTime = tripEvent.getEventTimeMillis();
        long watermark = context.timerService().currentWatermark();
        
        // Calculate window boundaries for 1-minute tumbling windows
        long windowSize = 60 * 1000; // 1 minute in milliseconds
        long windowStart = (eventTime / windowSize) * windowSize;
        long windowEnd = windowStart + windowSize;
        
        // Convert timestamps to readable format
        String eventTimeStr = LocalDateTime.ofInstant(Instant.ofEpochMilli(eventTime), ZoneOffset.UTC).format(FORMATTER);
        String windowStartStr = LocalDateTime.ofInstant(Instant.ofEpochMilli(windowStart), ZoneOffset.UTC).format(FORMATTER);
        String windowEndStr = LocalDateTime.ofInstant(Instant.ofEpochMilli(windowEnd), ZoneOffset.UTC).format(FORMATTER);
        
        // Check if event is late (arrives after watermark)
        boolean isLate = eventTime < watermark;
        
        // Periodic detailed logging
        if (eventCount % LOG_INTERVAL == 0) {
            LOG.info("🪟 Window Assignment - Trip: {}, Region: {}, EventTime: {}, Window: [{} - {}], Late: {}, Watermark: {}", 
                    tripEvent.getTripId(),
                    tripEvent.getRegionId(),
                    eventTimeStr,
                    windowStartStr,
                    windowEndStr,
                    isLate,
                    watermark > 0 ? LocalDateTime.ofInstant(Instant.ofEpochMilli(watermark), ZoneOffset.UTC).format(FORMATTER) : "No watermark"
            );
        }
        
        // Log late events immediately
        if (isLate) {
            LOG.warn("⏰ Late event detected - Trip: {}, Region: {}, EventTime: {}, Watermark: {}, Delay: {}ms", 
                    tripEvent.getTripId(),
                    tripEvent.getRegionId(),
                    eventTimeStr,
                    LocalDateTime.ofInstant(Instant.ofEpochMilli(watermark), ZoneOffset.UTC).format(FORMATTER),
                    watermark - eventTime
            );
        }
        
        // Forward the event
        collector.collect(tripEvent);
    }
    
    public long getProcessedEvents() {
        return processedEvents.get();
    }
}
