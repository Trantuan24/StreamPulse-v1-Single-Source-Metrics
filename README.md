# StreamPulse v1 - Real-time Data Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Apache Flink](https://img.shields.io/badge/Apache%20Flink-1.17-orange.svg)](https://flink.apache.org/)
[![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-7.4.0-red.svg)](https://kafka.apache.org/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Trantuan24/StreamPulse-v1-Single-Source-Metrics)

> **Level 1 - StreamMetrics Starter Project**
> A comprehensive real-time data pipeline for learning stream processing fundamentals

## 📋 Tổng quan

StreamPulse v1 là một pipeline xử lý dữ liệu thời gian thực end-to-end được thiết kế để chạy trên một máy duy nhất. Dự án này hoàn hảo cho việc học tập và thực hành các công nghệ stream processing hiện đại.

### 🎯 Mục tiêu dự án

- **Ingest**: Đọc dữ liệu trip từ CSV/JSON và publish lên Kafka
- **Processing**: Sử dụng Apache Flink để xử lý event-time với windowing và watermarks
- **Serving**: Lưu kết quả vào Redis và expose qua FastAPI
- **Monitoring**: Theo dõi pipeline với Prometheus + Grafana

### 🏗️ Kiến trúc hệ thống

```
CSV Data → Kafka → Flink (Windowing) → Redis → FastAPI → Grafana Dashboard
```

### 🛠️ Technology Stack

- **Message Bus**: Apache Kafka (1 broker)
- **Stream Processing**: Apache Flink (1 JobManager, 1-2 TaskManagers)
- **Serving Layer**: Redis (key-value store)
- **API Layer**: FastAPI (Python)
- **Monitoring**: Prometheus + Grafana
- **Deployment**: Docker Compose

### SLO (Service Level Objectives)

- **Latency**: p95 end-to-end latency ≤ 3 giây
- **Throughput**: Xử lý được 1-3k events/giây trên laptop
- **Reliability**: Consumer lag ≈ 0 trong ít nhất 5 phút liên tục
- **Recovery**: Khôi phục từ checkpoint khi TaskManager bị kill

### Cấu Trúc Dự Án

```
tripstream-analytics/
├── infra/
│   └── docker-compose/          # Docker Compose configurations
├── streaming/
│   ├── jobs/                    # Flink applications
│   └── schemas/                 # Data schemas (JSON/Avro)
├── producers/
│   ├── replay/                  # CSV/JSON replay producer
│   └── synthetic/               # Synthetic data generator
├── serving/
│   └── api/                     # FastAPI application
├── monitoring/
│   ├── prometheus.yml           # Prometheus configuration
│   ├── grafana-dashboards/      # Grafana dashboard definitions
│   └── alerts/                  # Alert rules
├── ops/
│   ├── Makefile                 # Automation scripts
│   ├── scripts/                 # Utility scripts
│   └── data/                    # Sample data files
└── README.md                    # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker và Docker Compose
- `make` command (hoặc chạy trực tiếp từ `ops/Makefile`)
- Ít nhất 4GB RAM available

### Khởi chạy pipeline

```bash
# Clone repository
git clone https://github.com/Trantuan24/StreamPulse-v1-Single-Source-Metrics
cd StreamPulse-v1

# Khởi động toàn bộ pipeline
cd ops
make setup

# Gửi dữ liệu test
make produce-test

# Kiểm tra API
make test-api
```

### 🔗 Truy cập các dịch vụ

| Service               | URL                        | Credentials |
| --------------------- | -------------------------- | ----------- |
| **Grafana Dashboard** | http://localhost:3000      | admin/admin |
| **Flink Web UI**      | http://localhost:8081      | -           |
| **Prometheus**        | http://localhost:9090      | -           |
| **FastAPI Docs**      | http://localhost:8000/docs | -           |

### Dừng và dọn dẹp

```bash
# Dừng services
make down

# Dọn dẹp hoàn toàn
make clean
```

## 📊 Data Schema & API

### Sample Data Schema

```json
{
  "trip_id": "trip_001",
  "region_id": 1,
  "event_time": "2025-08-15T10:30:00Z",
  "fare": 25.5,
  "duration": 1800,
  "distance": 12.5
}
```

### 🔌 API Endpoints

| Method | Endpoint                                | Description                            |
| ------ | --------------------------------------- | -------------------------------------- |
| `GET`  | `/metrics/region/{region_id}?window=1m` | Lấy metrics theo region và time window |
| `GET`  | `/health`                               | Health check endpoint                  |
| `GET`  | `/metrics`                              | Prometheus metrics endpoint            |
| `GET`  | `/docs`                                 | Interactive API documentation          |

### 📈 Monitoring Dashboards

- **Pipeline Overview**: Throughput, latency, error rates
- **Kafka Metrics**: Consumer lag, partition distribution
- **Flink Metrics**: Checkpoint status, backpressure, task utilization
- **Business Metrics**: Trip counts, average fare by region

## 🔧 Development & Troubleshooting

### Development Workflow

1. **Local Development**: Sử dụng Docker Compose để chạy tất cả services
2. **Testing**: Unit tests cho Flink jobs, integration tests cho API
3. **Debugging**: Logs aggregation, metrics monitoring
4. **Performance Testing**: Load testing với synthetic data

### Common Issues & Solutions

| Issue                       | Solution                                        |
| --------------------------- | ----------------------------------------------- |
| **Kafka Connection Issues** | Kiểm tra port 9092, container networking        |
| **Flink Job Failures**      | Xem logs trong Flink UI (http://localhost:8081) |
| **High Latency**            | Monitor backpressure, checkpoint duration       |
| **Data Loss**               | Verify checkpoint configuration và recovery     |
| **Out of Memory**           | Tăng memory limits trong docker-compose.yml     |

### Performance Tuning

- **Flink**: Adjust parallelism, checkpoint intervals
- **Kafka**: Tune batch size, compression
- **Redis**: Configure memory policies, persistence

## 🎯 SLO (Service Level Objectives)

- **Latency**: p95 end-to-end latency ≤ 3 giây
- **Throughput**: Xử lý được 1-3k events/giây trên laptop
- **Reliability**: Consumer lag ≈ 0 trong ít nhất 5 phút liên tục
- **Recovery**: Khôi phục từ checkpoint khi TaskManager bị kill

## 🚀 Next Steps

Sau khi hoàn thành Level 1, có thể tiến lên:

- **Level 2**: MultiStream Intelligence (Interval joins, OLAP, Schema Registry)
- **Level 3**: CloudStream Platform (Kubernetes, HA, Blue-Green deployment)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apache Flink Community
- Confluent Platform
- FastAPI Framework
- Grafana Labs

---
