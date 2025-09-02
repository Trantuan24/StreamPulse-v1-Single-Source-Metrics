# StreamPulse v1 - Troubleshooting Guide

**Version**: 1.0  
**Last Updated**: August 2025

---

## 🎯 Overview

This guide covers common issues encountered during StreamPulse v1 development and their solutions. Use this as a reference for diagnosing and resolving pipeline issues.

---

## 🚨 Common Issues & Solutions

### 1. **Watermark Issues**

#### **Problem**: Flink job shows "No watermark received" warnings

```
WARN: No watermark received within the last 200000 ms for input xxx
```

#### **Root Cause**:

- Events too old relative to current watermark
- Source marked as idle
- Incorrect timestamp extraction

#### **Solution**:

```java
// Increase out-of-orderness allowance
WatermarkStrategy.<TripEvent>forBoundedOutOfOrderness(Duration.ofSeconds(20))
    .withIdleness(Duration.ofSeconds(10)) // Mark source as idle after 10s
    .withTimestampAssigner((event, timestamp) -> event.getEventTimeMillis())
```

#### **Verification**:

- Check Flink UI → Job → Watermarks tab
- Look for increasing watermark values
- Verify timestamp extraction in logs

---

### 2. **Pydantic Version Conflicts**

#### **Problem**: Import errors with Pydantic models

```
ImportError: cannot import name 'Field' from 'pydantic'
AttributeError: 'BaseModel' object has no attribute 'parse_obj'
```

#### **Root Cause**:

- Pydantic v2 breaking changes
- Inconsistent versions across components

#### **Solution**:

```bash
# Use Pydantic v1.x for compatibility
pip install pydantic==1.10.13

# Update imports for v2 if needed
from pydantic.v1 import BaseModel, Field
```

#### **In Code**:

```python
# V1 syntax (current)
trip_event = TripEvent.parse_obj(data)

# V2 syntax (if upgrading)
trip_event = TripEvent.model_validate(data)
```

---

### 3. **File Path Issues**

#### **Problem**: Producer cannot find CSV files

```
FileNotFoundError: [Errno 2] No such file or directory: 'data/sample.csv'
```

#### **Root Cause**:

- Relative path dependencies
- Working directory confusion
- Docker volume mounting

#### **Solution**:

```python
# Use absolute paths or proper relative paths
import os
csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'ops', 'data', 'sample.csv')

# Or use from ops directory
cd ops/
python ../producers/replay/csv_replay_producer.py --csv-file data/sample.csv
```

#### **Docker Solution**:

```bash
# Mount data directory as volume
docker run -v $(pwd)/ops/data:/data producer --csv-file /data/sample.csv
```

---

### 4. **Dead Letter Queue Issues**

#### **Problem**: Failed events not appearing in DLQ topic

#### **Diagnosis Steps**:

```bash
# 1. Check if DLQ topic exists
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --list | grep dlq'

# 2. Check Flink job logs
docker-compose logs flink-jobmanager | grep DLQ

# 3. Consume from DLQ topic
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic events_dlq \
  --from-beginning'
```

#### **Solutions**:

- Verify topic creation: `make create-topics`
- Check Flink job deployment status
- Validate malformed data format
- Review side output configuration

---

### 5. **Kafka Connectivity Issues**

### Testing the Dead Letter Queue

To verify that the DLQ is working correctly, you can intentionally send malformed data to the `events` topic. The project includes a sample file for this purpose.

1.  **Run the producer with malformed data**:

    ```bash
    # From the ops/ directory (Windows example)
    ..\api_venv\Scripts\python.exe ..\producers\replay\csv_replay_producer.py --csv-file .\data\malformed_test_data.csv --max-events 20

    # Linux/macOS equivalent
    ../api_venv/bin/python ../producers/replay/csv_replay_producer.py --csv-file ./data/malformed_test_data.csv --max-events 20
    ```

2.  **Consume from the DLQ topic**:

    You should see the malformed records appear in the `events_dlq` topic, enriched with error metadata.

    ```bash
    docker compose -f "..\infra\docker-compose\docker-compose.yml" exec kafka bash -c "unset KAFKA_OPTS && kafka-console-consumer --bootstrap-server kafka:29092 --topic events_dlq --from-beginning --timeout-ms 5000"
    ```

#### **Problem**: Producer fails to connect to Kafka

```
KafkaError: [Errno -195] Resolve error
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
```

#### **Diagnosis**:

```bash
# Check Kafka container status
docker-compose ps kafka

# Check Kafka logs
docker-compose logs kafka | tail -50

# Test connectivity from within network
docker-compose exec api python -c "
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers=['kafka:29092'])
print('Connected successfully')
"
```

#### **Solutions**:

1. **Service Discovery**: Use `kafka:29092` inside Docker network
2. **External Access**: Use `localhost:9092` from host machine
3. **Wait for Service**: Add health checks and startup delays
4. **Network Issues**: Check `docker-compose.yml` networking

---

### 6. **Redis Connection Failures**

#### **Problem**: API health check fails for Redis

```
redis.exceptions.ConnectionError: Error connecting to Redis
```

#### **Diagnosis**:

```bash
# Check Redis container
docker-compose ps redis

# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check from API container
docker-compose exec api python -c "
import redis
r = redis.Redis(host='redis', port=6379)
print(r.ping())
"
```

#### **Solutions**:

- Verify Redis container health
- Check connection pooling configuration
- Review Docker networking
- Validate Redis authentication (if enabled)

---

### 7. **Flink Job Recovery Issues**

#### **Problem**: Job doesn't recover after TaskManager restart

#### **Diagnosis**:

```bash
# Check Flink cluster status
curl http://localhost:8081/overview

# Check job status
curl http://localhost:8081/jobs

# Review checkpoint directory
docker-compose exec flink-jobmanager ls -la /tmp/flink-checkpoints
```

#### **Solutions**:

1. **Checkpoint Configuration**:

```java
env.enableCheckpointing(30000); // 30 second interval
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
```

2. **Restart Strategy**:

```yaml
restart-strategy: fixed-delay
restart-strategy.fixed-delay.attempts: 5
restart-strategy.fixed-delay.delay: 10s
```

3. **State Backend**:

```yaml
state.backend: rocksdb
state.checkpoints.dir: file:///tmp/flink-checkpoints
```

---

### 8. **Performance Issues**

#### **Problem**: Low throughput or high latency

#### **Diagnosis**:

- Check Flink UI backpressure indicators
- Monitor resource utilization
- Review parallelism settings

#### **Solutions**:

1. **Increase Parallelism**:

```java
env.setParallelism(4); // Match TaskManager slots
```

2. **Optimize Kafka**:

```python
# Producer optimization
producer_config = {
    'batch_size': 131072,  # 128KB
    'buffer_memory': 268435456,  # 256MB
    'compression_type': 'gzip'
}
```

3. **Memory Tuning**:

```yaml
taskmanager.memory.process.size: 2048m
jobmanager.memory.process.size: 1600m
```

---

## 🔧 Diagnostic Commands

### **Pipeline Health Check**:

```bash
# Full system status
make status
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml ps

# Health check API
curl http://localhost:8000/health

# Check all services
docker-compose ps
```

### **Kafka Debugging**:

```bash
# List topics
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --list'

# Consumer group status
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-consumer-groups \
  --bootstrap-server kafka:29092 \
  --group trip-metrics-job \
  --describe'

# Consume from beginning
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic events \
  --from-beginning'
```

### **Flink Debugging**:

```bash
# Job list
curl http://localhost:8081/jobs

# Job details
curl http://localhost:8081/jobs/<job-id>

# Job exceptions
curl http://localhost:8081/jobs/<job-id>/exceptions
```

### **Log Analysis**:

```bash
# All service logs
make logs
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml logs -f

# Specific service logs
docker-compose logs -f flink-jobmanager
docker-compose logs -f api
docker-compose logs -f kafka
```

---

## 🚀 Recovery Procedures

### **Complete Pipeline Reset**:

```bash
# Stop everything
make down
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml down -v

# Clean volumes and networks
make clean
# Equivalent: make down && docker system prune -af

# Fresh start
make setup
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml up -d --build; sleep 15; make create-topics; sleep 5; make submit-job
```

### **Flink Job Reset**:

```bash
# Cancel job
curl -X PATCH http://localhost:8081/jobs/<job-id>

# Restart from clean state
make submit-job
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml exec flink-jobmanager bash -c 'flink run -d /opt/flink/usrlib/trip-metrics-job-1.0-SNAPSHOT.jar'
```

### **Data Replay**:

```bash
# Clear Kafka topic
docker-compose exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics \
  --bootstrap-server kafka:29092 \
  --delete --topic events'

# Recreate topic
make create-topics
# Equivalent: docker-compose -f ../infra/docker-compose/docker-compose.yml exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events --partitions 2 --replication-factor 1'

# Replay data
make produce-test
# Equivalent: python3 ../producers/replay/csv_replay_producer_optimized.py --csv-file data/streampulse_sample_trips.csv --no-preserve-timestamps
```

---

## 📊 Monitoring & Alerting

### **Key Metrics to Watch**:

- **Kafka Consumer Lag**: Should be near 0
- **Flink Checkpoint Duration**: < 30 seconds
- **API Response Time**: < 100ms
- **DLQ Message Rate**: Minimal under normal operation

### **Alert Thresholds**:

- Consumer lag > 1000 messages
- Checkpoint failures > 5% rate
- API error rate > 1%
- No data processed for > 5 minutes

---

## 📞 Escalation Path

1. **Check this troubleshooting guide**
2. **Review service logs**: `make logs`
3. **Verify system health**: `curl localhost:8000/health`
4. **Check monitoring dashboards**: Grafana at `localhost:3000`
5. **Full system restart**: `make clean && make setup`

---

## 🔄 Maintenance Tasks

### **Daily**:

- Check pipeline health status
- Review error rates in logs
- Verify data freshness

### **Weekly**:

- Analyze DLQ message patterns
- Review performance metrics
- Update monitoring thresholds

### **Monthly**:

- Archive old logs
- Review and update this guide
- Performance optimization review

---

**Note**: This guide will be updated as new issues are discovered and resolved. Always check the latest version before troubleshooting.
