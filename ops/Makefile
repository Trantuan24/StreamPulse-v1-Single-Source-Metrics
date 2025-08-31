# StreamPulse v1 - Makefile for Pipeline Automation


# Define variables
COMPOSE_FILE = ../infra/docker-compose/docker-compose.yml
PRODUCER_SCRIPT = ../producers/replay/csv_replay_producer.py
SAMPLE_DATA = data/streampulse_sample_trips.csv

COMPOSE_CMD = docker compose
# Default target
.DEFAULT_GOAL := help

# =============================================================================
# HELPERS
# =============================================================================

.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup           - Build images, start all services, create topics, and submit the Flink job."
	@echo "  up              - Build and start all services in detached mode."
	@echo "  down            - Stop and remove all services, including volumes."
	@echo "  stop            - Stop all services without removing them."
	@echo "  status          - Show the status of all running services."
	@echo "  logs            - Tail the logs of all services."
	@echo "  logs-flink      - Tail the logs of the Flink JobManager."
	@echo "  logs-api        - Tail the logs of the FastAPI service."
	@echo "  create-topics   - Create the 'events' and 'events_dlq' Kafka topics."
	@echo "  submit-job      - Submit the Flink job to the cluster."
	@echo "  produce-test    - Produce sample data to Kafka immediately (no timestamp preservation)."
	@echo "  test-api        - Run a curl command to test the region metrics API."
	@echo "  full-test       - Run a full end-to-end test: setup, produce data, and test the API."
	@echo "  clean           - A more thorough cleanup: stops services and removes volumes, networks, and images."

# =============================================================================
# CORE TARGETS
# =============================================================================

.PHONY: up
up:
	@echo "🚀 Starting all StreamPulse services..."
		DOCKER_BUILDKIT=0 $(COMPOSE_CMD) -f $(COMPOSE_FILE) up -d --build
	@echo "✅ All services are up and running."

.PHONY: down
down:
	@echo "🔥 Stopping and removing all StreamPulse services and volumes..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) down -v

.PHONY: stop
stop:
	@echo "🛑 Stopping all StreamPulse services..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) stop
	@echo "✅ Services stopped."

.PHONY: status
status:
	@echo "📊 Displaying service status..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) ps

.PHONY: logs
logs:
	@echo "📜 Tailing logs for all services..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) logs -f

.PHONY: logs-flink
logs-flink:
	@echo "📜 Tailing logs for Flink JobManager..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) logs -f flink-jobmanager

.PHONY: logs-api
logs-api:
	@echo "📜 Tailing logs for FastAPI service..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) logs -f api

# =============================================================================
# PIPELINE MANAGEMENT TARGETS
# =============================================================================

.PHONY: create-topics
create-topics:
	@echo "✒️ Creating Kafka topics 'events' and 'events_dlq'..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events --partitions 2 --replication-factor 1'
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events_dlq --partitions 1 --replication-factor 1'
	@echo "✅ Kafka topics created."

.PHONY: submit-job
submit-job:
	@echo "🚀 Submitting Flink job to the cluster..."
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) exec flink-jobmanager bash -c 'flink run -d /opt/flink/usrlib/trip-metrics-job-1.0-SNAPSHOT.jar'
	@echo "✅ Flink job submitted."

.PHONY: produce-test
produce-test:
		@python3 $(PRODUCER_SCRIPT) --csv-file $(SAMPLE_DATA) --no-preserve-timestamps
	@echo "✅ Sample data produced."
	@echo "✅ Sample data produced."

.PHONY: test-api
test-api:
	@echo "📞 Testing API endpoint for region 1..."
	@curl http://localhost:8000/metrics/region/1
	@echo ""

# =============================================================================
# AUTOMATION & CLEANUP
# =============================================================================

.PHONY: setup
setup:
	@echo "🛠️  Setting up the full pipeline..."
	@make up
	@echo "⏳ Waiting for services to stabilize..."
	@sleep 15
	@make create-topics
	@sleep 5
	@make submit-job
	@echo "✅ Pipeline setup complete."

.PHONY: full-test
full-test:
	@echo "🧪 Running a full end-to-end test..."
	@make setup
	@echo "⏳ Waiting for Flink job to initialize..."
	@sleep 10
	@make produce-test
	@echo "⏳ Waiting for data to be processed..."
	@sleep 10
	@make test-api
	@echo "✅ Full test complete."

.PHONY: clean
clean:
	@echo "🧹 Cleaning up the environment thoroughly..."
	@make down
		docker system prune -af
	@echo "✅ Environment is clean."
