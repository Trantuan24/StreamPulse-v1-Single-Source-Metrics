package com.streampulse;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.streaming.api.TimeCharacteristic;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;

import java.util.Properties;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.time.LocalDateTime;

import org.apache.flink.streaming.connectors.redis.RedisSink;
import org.apache.flink.streaming.connectors.redis.common.config.FlinkJedisPoolConfig;

/**
 * StreamPulse v1 - Trip Metrics Job
 *
 * Real-time streaming analytics for trip events using event-time processing
 * with proper watermark handling for out-of-order events.
 */
public class TripMetricsJob {

    private static final Logger LOG = LoggerFactory.getLogger(TripMetricsJob.class);

    // OutputTag for failed JSON parsing events
    private static final OutputTag<String> FAILED_EVENTS_TAG = new OutputTag<String>("failed-events"){};

    public static void main(String[] args) throws Exception {

        // 1. Setup execution environment
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // IMPORTANT: Set the time characteristic to EventTime for all time-based operations
        env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime);

        // PERFORMANCE OPTIMIZATION: Increase parallelism
        env.setParallelism(4);  // Increased from 2 to 4 for better throughput
        
        // Performance optimizations
        env.enableCheckpointing(30000);  // 30 seconds (reduced from default 60s)
        env.getConfig().setAutoWatermarkInterval(1000L);  // 1s watermark interval
        env.getConfig().setLatencyTrackingInterval(5000L);  // 5s latency tracking

        LOG.info("🚀 Starting StreamPulse v1 - Trip Metrics Job");
        LOG.info("📊 Parallelism: {}", env.getParallelism());

        // 2. Configure Kafka source with OPTIMIZED consumer properties 
        Properties kafkaProps = new Properties();
        kafkaProps.setProperty("enable.auto.commit", "true");
        kafkaProps.setProperty("auto.commit.interval.ms", "1000");  // Reduced from 5000ms
        kafkaProps.setProperty("session.timeout.ms", "30000");
        kafkaProps.setProperty("heartbeat.interval.ms", "3000");  // Reduced from 10000ms
        
        // Performance optimizations
        kafkaProps.setProperty("fetch.min.bytes", "1024");  // Fetch at least 1KB
        kafkaProps.setProperty("fetch.max.wait.ms", "500");  // Max wait 500ms
        kafkaProps.setProperty("max.partition.fetch.bytes", "1048576");  // 1MB per partition

        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers("kafka:29092")  // Internal Docker network
                .setTopics("events")
                .setGroupId("trip-metrics-job")
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .setProperties(kafkaProps)  // Add consumer properties
                .build();

        LOG.info("📨 Kafka source configured: topic=events, servers=kafka:29092");

        // 3. Create data stream from Kafka WITHOUT watermarks first
        DataStream<String> kafkaStream = env.fromSource(
                kafkaSource,
                WatermarkStrategy.noWatermarks(),
                "Kafka Source"
        );

        // 4. Parse JSON and transform to TripEvent objects
        SingleOutputStreamOperator<TripEvent> tripStreamWithSideOutputs = kafkaStream
                .process(new EnhancedJsonToTripEventProcessor())
                .name("Enhanced JSON Parser");

        // 5. Apply event-time watermarks with bounded out-of-orderness
        DataStream<TripEvent> tripStream = tripStreamWithSideOutputs
                .assignTimestampsAndWatermarks(
                    WatermarkStrategy.<TripEvent>forBoundedOutOfOrderness(Duration.ofMinutes(2))
                        .withTimestampAssigner((event, timestamp) -> event.getEventTimeMillis())
                        .withIdleness(Duration.ofSeconds(10)) // Mark source as idle
                );

        // 6. Monitor failed events
        DataStream<String> failedEvents = tripStreamWithSideOutputs.getSideOutput(FAILED_EVENTS_TAG);
        failedEvents
                .map(failedJson -> "FAILED: " + failedJson.substring(0, Math.min(50, failedJson.length())) + "...")
                .name("Failed Events Monitor")
                .print("FAILED-EVENTS");

        // 7. Add window assignment monitoring
        DataStream<TripEvent> monitoredStream = tripStream
                .process(new WindowAssignmentMonitor())
                .name("Window Assignment Monitor");

        // 8. Enhanced keyed stream with custom key selector and detailed logging
        LOG.info("🔑 Setting up keyed stream by region_id with enhanced monitoring...");

        // Create enhanced key selector
        RegionKeySelector regionKeySelector = new RegionKeySelector();

        // Apply keyed stream with enhanced monitoring
        DataStream<TripMetrics> aggregatedStream = monitoredStream
                .keyBy(regionKeySelector)
                .window(TumblingEventTimeWindows.of(Time.minutes(1)))
                .aggregate(new TripMetricsAggregator(), new TripMetricsWindowFunction())
                .name("Trip Metrics Aggregation");

        // Configure Redis connection
        FlinkJedisPoolConfig jedisPoolConfig = new FlinkJedisPoolConfig.Builder()
                .setHost("redis") // Service name in Docker Compose
                .setPort(6379)
                .build();

        // Create Redis Sink with TTL
        RedisSink<TripMetrics> redisSink = new RedisSink<>(jedisPoolConfig, new TripMetricsRedisMapper());

        // Add sink to the pipeline
        aggregatedStream.addSink(redisSink).name("Redis Sink");

        // 9. Execute job
        LOG.info("🎯 Starting StreamPulse Trip Metrics Job with Enhanced Keyed Streams...");
        env.execute("StreamPulse v1 - Enhanced Trip Metrics Job");
    }

    /**
     * ProcessFunction to parse JSON strings to TripEvent objects with error handling
     */
    public static class EnhancedJsonToTripEventProcessor extends ProcessFunction<String, TripEvent> {

        private static final Logger LOG = LoggerFactory.getLogger(EnhancedJsonToTripEventProcessor.class);
        private transient ObjectMapper objectMapper;
        private long successCount = 0;
        private long failureCount = 0;

        @Override
        public void open(org.apache.flink.configuration.Configuration parameters) {
            objectMapper = new ObjectMapper();
            objectMapper.registerModule(new JavaTimeModule());
            LOG.info("JSON Parser initialized");
        }

        @Override
        public void processElement(String jsonString, Context context, Collector<TripEvent> out) {
            try {
                if (jsonString == null || jsonString.trim().isEmpty()) {
                    handleParsingFailure("Empty JSON", jsonString, context);
                    return;
                }

                TripEvent trip = objectMapper.readValue(jsonString, TripEvent.class);

                if (trip.getTripId() == null || trip.getRegionId() == null) {
                    handleParsingFailure("Missing required fields", jsonString, context);
                    return;
                }

                out.collect(trip);
                successCount++;

                // Log progress periodically
                if (successCount % 100 == 0) {
                    LOG.info("Processed {} events successfully. Failures: {}", successCount, failureCount);
                }

            } catch (Exception e) {
                handleParsingFailure(e.getMessage(), jsonString, context);
            }
        }

        private void handleParsingFailure(String errorMessage, String jsonString, Context context) {
            failureCount++;
            context.output(FAILED_EVENTS_TAG, jsonString);

            if (failureCount % 10 == 0) {
                LOG.warn("Failed to parse JSON #{}: {}", failureCount, errorMessage);
            }
        }
    }
}