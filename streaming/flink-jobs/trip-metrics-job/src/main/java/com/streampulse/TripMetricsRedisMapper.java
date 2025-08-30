package com.streampulse;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.apache.flink.streaming.connectors.redis.common.mapper.RedisCommand;
import org.apache.flink.streaming.connectors.redis.common.mapper.RedisCommandDescription;
import org.apache.flink.streaming.connectors.redis.common.mapper.RedisMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TripMetricsRedisMapper implements RedisMapper<TripMetrics> {

    private static final Logger LOG = LoggerFactory.getLogger(TripMetricsRedisMapper.class);
    private transient ObjectMapper objectMapper;

    // Get the Redis command
    @Override
    public RedisCommandDescription getCommandDescription() {
        // We use SET command, but RedisSink will handle the TTL via SETEX
        return new RedisCommandDescription(RedisCommand.SET);
    }

    // Get the key from the input data
    @Override
    public String getKeyFromData(TripMetrics data) {
        if (objectMapper == null) {
            objectMapper = new ObjectMapper();
            objectMapper.registerModule(new JavaTimeModule());
        }
        String key = String.format("region:%d:window:%d",
                data.getRegionId(),
                data.getWindowStart().getEpochSecond());
        LOG.debug("Generated Redis Key: {}", key);
        return key;
    }

    // Get the value from the input data
    @Override
    public String getValueFromData(TripMetrics data) {
        if (objectMapper == null) {
            objectMapper = new ObjectMapper();
            objectMapper.registerModule(new JavaTimeModule());
        }
        try {
            String value = objectMapper.writeValueAsString(data);
            LOG.debug("Generated Redis Value: {}", value);
            return value;
        } catch (Exception e) {
            LOG.error("Error serializing TripMetrics to JSON", e);
            return null; // Or a default JSON object
        }
    }
}

