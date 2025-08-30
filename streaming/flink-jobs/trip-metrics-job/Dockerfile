# StreamPulse v1 - Self-contained Flink Job Build
# Multi-stage Dockerfile for zero-dependency deployment

# =============================================================================
# Stage 1: Build Stage
# =============================================================================
FROM maven:3.8.6-openjdk-11 AS build

# Set working directory
WORKDIR /app

# Copy pom.xml first for dependency caching
COPY pom.xml ./

# Copy source code
COPY src/ ./src/

# Build the application using Maven directly

RUN mvn clean package -DskipTests -B

# =============================================================================
# Stage 2: Runtime Stage
# =============================================================================
FROM flink:1.17-java11

# Metadata
LABEL maintainer="StreamPulse Project"
LABEL description="StreamPulse v1 - Trip Metrics Flink Job"
LABEL version="1.0.0"

# Copy the built JAR from build stage
COPY --from=build /app/target/trip-metrics-job-*.jar /opt/flink/usrlib/
# Create and set permissions for the checkpoints directory
USER root
RUN mkdir -p /tmp/flink-checkpoints && \
    chown -R flink:flink /tmp/flink-checkpoints


# Copy additional connectors if needed
# Note: Redis connector and other dependencies are already included in the fat JAR

# Verify JAR placement
RUN echo "Flink job JAR files:" && \
    ls -la /opt/flink/usrlib/ && \
    echo "Flink installation:" && \
    ls -la /opt/flink/

# Set proper permissions
RUN chmod +r /opt/flink/usrlib/*.jar

# Health check for the runtime image
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/taskmanagers || exit 1

# Default command (will be overridden by docker-compose)
CMD ["jobmanager"]
