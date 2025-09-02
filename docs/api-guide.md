# StreamPulse v1 - API Reference Guide

**Version**: 1.0
**Last Updated**: August 2025
**Base URL**: `http://localhost:8000`

---

## API Overview

The StreamPulse API provides RESTful access to real-time trip analytics processed by the streaming pipeline. Built with FastAPI, the API offers high-performance endpoints with comprehensive validation, error handling, and monitoring capabilities.

### API Characteristics

- **Response Format**: JSON with standardized field naming
- **Authentication**: Currently none (development environment)
- **Rate Limiting**: Not implemented (future enhancement)
- **CORS**: Enabled for cross-origin requests
- **Content Type**: `application/json`

### Response Standards

All API responses follow consistent patterns:

- **Success Responses**: HTTP 200 with data payload
- **Error Responses**: HTTP 4xx/5xx with descriptive error messages
- **Timestamps**: ISO 8601 format with UTC timezone
- **Field Naming**: camelCase for JSON responses

---

## Health Monitoring

### Health Check Endpoint

**Endpoint**: `GET /health`

**Description**: Comprehensive health check providing system-wide status information including dependency connectivity and performance metrics.

**Response Fields**:

- **status**: Overall system health (`healthy`, `degraded`, `unhealthy`)
- **timestamp**: Current system timestamp in ISO format
- **services**: Detailed status for each system component
- **response_time_ms**: Health check execution time in milliseconds

**Success Response Example**:

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "timestamp": "2025-09-01T18:00:00.000000+00:00",
  "services": {
    "redis": "connected",
    "kafka": "connected",
    "api": "running",
    "response_time_ms": "150"
  }
}
```

The health endpoint returns detailed status information for all critical system components. A healthy system shows all services as connected with reasonable response times.

**Error Scenarios**:

- **Redis Unavailable**: Status becomes `degraded` or `unhealthy`
- **Kafka Connectivity Issues**: Kafka service shows `connection_error`
- **High Response Time**: Indicates system under load or performance degradation

**Usage Recommendations**:

- Monitor this endpoint regularly for operational health
- Set up automated alerts based on status changes
- Use response time metrics for performance baseline establishment
- Include in load balancer health checks for high availability setups

---

## Trip Metrics API

### Region Metrics Endpoint

**Endpoint**: `GET /metrics/region/{region_id}`

**Description**: Retrieves the most recent aggregated trip metrics for a specific geographical region. Metrics represent 1-minute tumbling window aggregations processed in real-time.

**Path Parameters**:

- **region_id** (integer, required): Unique identifier for the geographical region (valid range: 1-100)

**Query Parameters**:

- **window** (string, optional): Time window size (currently only `1m` supported)

**Response Fields**:

- **regionId**: Geographic region identifier
- **windowStart**: Window start timestamp (ISO 8601 format)
- **windowEnd**: Window end timestamp (ISO 8601 format)
- **tripCount**: Total number of trips in the window
- **avgFare**: Average fare amount across all trips
- **totalDistance**: Sum of all trip distances in kilometers
- **avgDuration**: Average trip duration in seconds
- **p50Duration**: 50th percentile trip duration
- **p95Duration**: 95th percentile trip duration

**Success Response Example**:

```bash
curl http://localhost:8000/metrics/region/5
```

```json
{
  "regionId": 5,
  "windowStart": "2025-09-01T11:40:00+00:00",
  "windowEnd": "2025-09-01T11:41:00+00:00",
  "tripCount": 7,
  "avgFare": 50.25,
  "totalDistance": 117.6,
  "avgDuration": 1442.57,
  "p50Duration": 1602.0,
  "p95Duration": 2113.0,
  "p99Duration": 2113.0
}
```

A successful response contains comprehensive trip analytics for the requested region and time window. All monetary values are in USD, distances in kilometers, and durations in seconds.

**Error Responses**:

**404 Not Found**: Occurs when no metrics exist for the specified region. This can happen if:

- No trips have been processed for the region
- The region ID is outside the valid range
- Data processing is still in progress for recent events

**500 Internal Server Error**: Indicates system-level issues such as:

- Redis connectivity problems
- Data serialization errors
- Internal processing failures

**Usage Patterns**:

- Query multiple regions to build comprehensive dashboards
- Implement periodic polling for real-time updates
- Cache responses appropriately based on data freshness requirements
- Handle 404 responses gracefully in client applications

### Future Endpoints (Planned)

**Top Regions Endpoint**: `GET /metrics/regions/top`

- Returns highest-performing regions by specified metrics
- Supports ranking by trip count, average fare, or total distance
- Configurable result limits and time window selection

**Historical Timeline**: `GET /metrics/timeline/{region_id}`

- Provides historical metric trends for a specific region
- Supports configurable time ranges and aggregation intervals
- Enables time-series analysis and trend identification

**Prometheus Metrics**: `GET /metrics`

- Exposes application metrics in Prometheus format
- Includes API performance, error rates, and system health indicators
- Used by Prometheus for monitoring and alerting

---

## Error Handling

### Error Response Format

All error responses follow a standardized format with descriptive messages and appropriate HTTP status codes.

### HTTP Status Codes

- **200 OK**: Successful request with valid response data
- **400 Bad Request**: Invalid request parameters or malformed input
- **404 Not Found**: Requested resource not found or no data available
- **500 Internal Server Error**: Server-side processing error
- **503 Service Unavailable**: Dependent service unavailable

### Error Recovery Strategies

**Client-side Recommendations**:

- Implement exponential backoff for 5xx errors
- Cache successful responses to reduce API load
- Provide meaningful error messages to end users
- Log errors for debugging and monitoring purposes

**Monitoring Integration**:

- Track error rates by endpoint and error type
- Set up alerts for elevated error rates or specific error patterns
- Monitor response times and success rates continuously
- Implement circuit breaker patterns for resilience

---

## Performance Considerations

### Response Time Expectations

- **Health Check**: < 200ms under normal conditions
- **Metrics Queries**: < 100ms for cached data
- **Cold Start**: May experience higher latency for new regions

### Optimization Recommendations

**Client Optimization**:

- Implement appropriate caching strategies based on data update frequencies
- Use connection pooling for applications making multiple requests
- Consider request batching for bulk operations when available
- Implement proper timeout handling for network requests

**Monitoring Integration**:

- Track response times and establish performance baselines
- Monitor cache hit rates and effectiveness
- Set up alerts for performance degradation
- Analyze usage patterns to optimize caching strategies

---

## Integration Examples

### Basic Integration Pattern

Typical integration involves checking system health before making data requests, implementing proper error handling, and caching responses appropriately based on business requirements.

### Monitoring Dashboard Integration

For building real-time dashboards, implement periodic polling with appropriate intervals based on data freshness requirements. Consider websocket upgrades for real-time streaming in future versions.

### Automated Alerting Integration

Integrate metrics endpoints with monitoring systems to trigger alerts based on business rules. Examples include trip count thresholds, fare anomalies, or regional performance variations.

---

## Monitoring and Observability

### Built-in Metrics

The API exposes Prometheus-compatible metrics at `/metrics` endpoint for operational monitoring:

- Request rates and response times by endpoint
- Error rates by status code and endpoint
- Active connection counts and pool utilization
- Dependency health check success rates

### Logging Standards

All API requests are logged with:

- Request timestamp and unique identifier
- Endpoint accessed and response status
- Response time and data size
- Error details for failed requests

### Performance Monitoring

Key performance indicators tracked automatically:

- Average response time by endpoint
- Request volume patterns and peak usage
- Error rate trends and patterns
- Dependency response times and availability

---

## Development and Testing

### Local Development Setup

For local development and testing, ensure all pipeline components are running and healthy before testing API endpoints. Use the health check endpoint to verify system readiness.

### Testing Recommendations

- Test all endpoints with valid and invalid parameters
- Verify error handling with various failure scenarios
- Load test with realistic traffic patterns
- Validate response formats and data accuracy

### API Evolution

Future API versions will maintain backward compatibility while adding enhanced functionality. Monitor API version headers and deprecation notices for smooth transitions.
