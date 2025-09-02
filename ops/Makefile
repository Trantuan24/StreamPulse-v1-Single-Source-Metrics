# StreamPulse v1 - Universal Makefile for Pipeline Automation
# Optimized for cross-platform use (Linux, macOS, Windows with Git Bash/WSL)
# Author: Cascade
# Last Updated: 2025-09-02

# =============================================================================
# CONFIGURATION
# =============================================================================

# Variables for core components
COMPOSE_FILE := ../infra/docker-compose/docker-compose.yml
COMPOSE_CMD := docker compose -f $(COMPOSE_FILE)

# Python interpreter - assumes a virtual environment is activated or python3 is in PATH
PYTHON_EXEC ?= python3

# Producer scripts and data files
PRODUCER_SCRIPT := ../producers/replay/csv_replay_producer_optimized.py
SAMPLE_DATA := data/streampulse_sample_trips.csv
LOAD_TEST_DATA := data/streampulse_load_test_50k.csv
MALFORMED_DATA := data/malformed_test_data.csv

# Default target when 'make' is run without arguments
.DEFAULT_GOAL := help

# =============================================================================
# HELPERS
# =============================================================================

.PHONY: help
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Core Commands:"
	@echo "  up              - Build and start all services in detached mode."
	@echo "  down            - Stop and remove all services, including volumes."
	@echo "  stop            - Stop all services without removing them."
	@echo "  clean           - A more thorough cleanup: stops services and removes Docker artifacts."
	@echo ""
	@echo "Pipeline Workflow:"
	@echo "  setup           - Run the full setup: up, create-topics, submit-job."
	@echo "  create-topics   - Create the 'events' and 'events_dlq' Kafka topics."
	@echo "  submit-job      - Submit the Flink job to the cluster."
	@echo ""
	@echo "Testing & Data:"
	@echo "  full-test       - Run a full E2E test: setup, produce sample data, and test the API."
	@echo "  produce-sample  - Produce a small sample dataset to Kafka."
	@echo "  produce-load    - Produce a larger 50k-event dataset for load testing."
	@echo "  produce-malformed - Produce malformed data to test the Dead Letter Queue."
	@echo "  test-api        - Run a curl command to test the region metrics API."
	@echo ""
	@echo "Diagnostics:"
	@echo "  status          - Show the status of all running services."
	@echo "  logs            - Tail the logs of all services."
	@echo "  logs-flink      - Tail the logs of the Flink JobManager."
	@echo "  logs-api        - Tail the logs of the FastAPI service."

# =============================================================================
# CORE COMMANDS
# =============================================================================

.PHONY: up
up:
	@echo "🚀 Building images and starting all StreamPulse services..."
	@DOCKER_BUILDKIT=0 $(COMPOSE_CMD) up -d --build
	@echo "✅ All services are up and running."

.PHONY: down
down:
	@echo "🔥 Stopping and removing all StreamPulse services and volumes..."
	@$(COMPOSE_CMD) down -v

.PHONY: stop
stop:
	@echo "🛑 Stopping all StreamPulse services..."
	@$(COMPOSE_CMD) stop
	@echo "✅ Services stopped."

.PHONY: clean
clean:
	@echo "🧹 Cleaning up the environment thoroughly..."
	@make down
	@echo "🔥 Pruning Docker system..."
	@docker system prune -af
	@echo "✅ Environment is clean."

# =============================================================================
# PIPELINE WORKFLOW
# =============================================================================

.PHONY: setup
setup:
	@echo "🛠️  Setting up the full pipeline..."
	@make up
	@echo "⏳ Waiting 20 seconds for services to stabilize..."
	@sleep 20
	@make create-topics
	@sleep 5
	@make submit-job
	@echo "✅ Pipeline setup complete."

.PHONY: create-topics
create-topics:
	@echo "✒️ Creating Kafka topics 'events' (4 partitions) and 'events_dlq' (1 partition)..."
	@$(COMPOSE_CMD) exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events --partitions 4 --replication-factor 1'
	@$(COMPOSE_CMD) exec kafka bash -c 'unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events_dlq --partitions 1 --replication-factor 1'
	@echo "✅ Kafka topics created."

.PHONY: submit-job
submit-job:
	@echo "🚀 Submitting Flink job to the cluster..."
	@$(COMPOSE_CMD) exec flink-jobmanager bash -c 'flink run -d /opt/flink/usrlib/trip-metrics-job-1.0-SNAPSHOT.jar --parallelism 4'
	@echo "✅ Flink job submitted. View status at http://localhost:8081"

# =============================================================================
# TESTING & DATA
# =============================================================================

.PHONY: full-test
full-test:
	@echo "🧪 Running a full end-to-end test..."
	@make setup
	@echo "⏳ Waiting 15 seconds for Flink job to initialize..."
	@sleep 15
	@make produce-sample
	@echo "⏳ Waiting 10 seconds for data to be processed..."
	@sleep 10
	@make test-api
	@echo "✅ Full test complete."

.PHONY: produce-sample
produce-sample:
	@echo "📤 Producing sample data from $(SAMPLE_DATA)..."
	@$(PYTHON_EXEC) $(PRODUCER_SCRIPT) --csv-file $(SAMPLE_DATA)
	@echo "✅ Sample data produced."

.PHONY: produce-load
produce-load:
	@echo "📤 Producing load test data from $(LOAD_TEST_DATA)..."
	@$(PYTHON_EXEC) $(PRODUCER_SCRIPT) --csv-file $(LOAD_TEST_DATA)
	@echo "✅ Load test data produced."

.PHONY: produce-malformed
produce-malformed:
	@echo "📤 Producing malformed data from $(MALFORMED_DATA) to test DLQ..."
	@$(PYTHON_EXEC) $(PRODUCER_SCRIPT) --csv-file $(MALFORMED_DATA)
	@echo "✅ Malformed data produced."

.PHONY: test-api
test-api:
	@echo "📞 Testing API endpoint for region 5..."
	@curl -s http://localhost:8000/metrics/region/5 | jq
	@echo ""

# =============================================================================
# DIAGNOSTICS
# =============================================================================

.PHONY: status
status:
	@echo "📊 Displaying service status..."
	@$(COMPOSE_CMD) ps

.PHONY: logs
logs:
	@echo "📜 Tailing logs for all services (Press Ctrl+C to stop)..."
	@$(COMPOSE_CMD) logs -f

.PHONY: logs-flink
logs-flink:
	@echo "📜 Tailing logs for Flink JobManager (Press Ctrl+C to stop)..."
	@$(COMPOSE_CMD) logs -f flink-jobmanager

.PHONY: logs-api
logs-api:
	@echo "📜 Tailing logs for FastAPI service (Press Ctrl+C to stop)..."
	@$(COMPOSE_CMD) logs -f api
