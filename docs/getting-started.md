# StreamPulse v1 - Getting Started Guide

**Version**: 1.0  
**Last Updated**: August 2025  

---

## 1. Prerequisites

- **Docker Desktop**: Latest stable version with Docker Compose.
- **Git**: For cloning the repository.
- **Python**: Version 3.9+.
- **Make Utility**: Recommended for the quick start workflow (standard on Linux/macOS; available on Windows via Git Bash, WSL, or Chocolatey).

---

## 2. Initial Setup (One-Time Steps)

These steps should be performed from your terminal in your desired workspace.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd streampulse
```

### Step 2: Prepare Python Environment

This creates an isolated environment for running data producer scripts.

```bash
# Create a virtual environment from the project root
python3 -m venv api_venv

# Activate it
# On Linux/macOS: source api_venv/bin/activate
# On Windows:     api_venv\Scripts\activate
```

> **⚠️ IMPORTANT: Install Dependencies**
> You **MUST** install the required Python packages before running any producer script. This step is crucial for the scripts to function correctly.

```bash
# Inside the activated environment, install packages
pip install -r serving/api/requirements.txt
pip install -r producers/replay/requirements.txt
```

---

## 3. Quick Start Workflow (Using Makefile)

This is the fastest and recommended way to operate the pipeline. **All `make` commands must be run from the `ops/` directory.**

```bash
cd ops
```

### Step 1: Clean and Set Up the Pipeline

This command starts the project from a clean state, automating the entire setup process.

```bash
make clean && make setup
```

- `make clean`: Stops and removes any old containers, volumes, and networks, and prunes the Docker system.
- `make setup`: Builds images, starts all services, creates Kafka topics, and submits the Flink job.

### Step 2: Produce Data

Once the pipeline is running, send data using one of the following commands:

```bash
make produce-test     # Send 50 sample events for quick testing
# OR for performance testing:
make produce-fast     # Send 1,000 events with optimized producer
make produce-load     # Send 10,000 events for load testing
```

### Step 3: Verify the Pipeline

After producing data, wait ~60 seconds for processing, then test the API.

```bash
make test-api
```

_A successful JSON response confirms the end-to-end pipeline is working._

### Step 4: Shutdown

When finished, this command stops and removes all project-related infrastructure.

```bash
make down
```

---

## 4. Detailed Step-by-Step Guide (Manual Commands)

Use this workflow if you do not have `make`. **All commands below should be run from the project's root directory.**

1.  **Build and Start Services**:

    ```bash
    docker compose -f infra/docker-compose/docker-compose.yml up -d --build
    ```

2.  **Create Kafka Topics**:

    ```bash
    docker compose -f infra/docker-compose/docker-compose.yml exec kafka bash -c "unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events --partitions 4 --replication-factor 1"
    docker compose -f infra/docker-compose/docker-compose.yml exec kafka bash -c "unset KAFKA_OPTS && kafka-topics --bootstrap-server kafka:29092 --create --if-not-exists --topic events_dlq --partitions 1 --replication-factor 1"
    ```

3.  **Submit Flink Job**:

    ```bash
    docker compose -f infra/docker-compose/docker-compose.yml exec flink-jobmanager bash -c "flink run -d /opt/flink/usrlib/trip-metrics-job-1.0-SNAPSHOT.jar --parallelism 4"
    ```

4.  **Produce Data** (ensure `api_venv` is activated):

    ```bash
    # From project root directory
    python producers/replay/csv_replay_producer.py --csv-file ops/data/streampulse_sample_trips.csv --no-preserve-timestamps --max-events 50
    ```

5.  **Test API**:

    ```bash
    curl http://localhost:8000/metrics/region/5
    ```

6.  **Shutdown**:
    ```bash
    docker compose -f infra/docker-compose/docker-compose.yml down -v
    ```
