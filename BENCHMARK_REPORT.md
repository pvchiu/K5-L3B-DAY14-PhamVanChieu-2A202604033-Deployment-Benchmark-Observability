# Benchmark & Observability Report — Day 14

**Họ tên:** Phạm Văn Chiêu  
**Mã sinh viên:** 2A202604033  
**Ngày chạy:** 26/11/2026  
**Môi trường:** Windows 11 (WSL2 Ubuntu 22.04, Docker Desktop)

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Đảm bảo trải nghiệm tương tác mượt mà cho người dùng cuối |
| Error rate `/ask` | < 1.0 % | Hệ thống production cần độ tin cậy cao, tỷ lệ lỗi dưới 1% |
| Accuracy trên golden dataset | ≥ 95 % (mục tiêu 100%) | Đảm bảo chất lượng câu trả lời chuẩn xác theo tri thức đã định nghĩa |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 45.2 | 18.5 | 24.1 | 30.2 | 0% | PASS |
| 10 | 185.4 | 48.2 | 85.6 | 110.4 | 0% | PASS |
| 50 | 290.1 | 145.0 | 260.3 | 340.5 | 0% | PASS |
| 100 | 315.6 | 280.4 | 440.2 | 495.0 | 0% | PASS |

**Nhận xét:** RPS tăng nhanh từ concurrency 1 đến 50 nhưng bắt đầu bão hòa ở mức 100 do giới hạn CPU và I/O của một tiến trình agent.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 22.4 | 35.1 | 42.0 |
| 0.03 (mặc định) | 36.8 | 120.5 | 280.4 |
| 0.1 | 68.2 | 310.0 | 480.2 |

**Nhận xét:** Chỉ số p99 và p95 nhạy nhất với request chậm vì các request ngoại lai (tail latency) bị kéo dài nhưng bị làm mờ khi tính trung bình (average). Do đó SLO luôn phải đặt theo percentile (p95/p99) thay vì average.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 78.2% | 91.3% | 100.0% |
| Avg tokens / câu | 120 | 145 | 148 |
| Tổng cost (USD) | $0.0018 | $0.0022 | $0.0023 |
| Cost / câu đúng (USD) | $0.0023 | $0.0024 | $0.0023 |
| Quality gate | FAIL | FAIL | PASS |

**Những câu v2 trả lời sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| Q05 | deployment strategy | Thêm định nghĩa Blue-Green và Canary vào `KNOWLEDGE_BASE` |
| Q12 | graceful shutdown | Bổ sung cơ chế xử lý SIGTERM và drain request vào `KNOWLEDGE_BASE` |

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải: `screenshots/grafana-dashboard.png`
- [x] Một trace chậm trong Jaeger: `screenshots/jaeger-slow-trace.png`
- [x] Một trace lỗi trong Jaeger: `screenshots/jaeger-error-trace.png`
- [x] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**: `screenshots/prometheus-alert-firing.png`

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | HighErrorRate | ~15s | Error Rate (%) |
| B | `MOCK_SLOW_RATE=0.3` | HighLatencyP95 | ~20s | Latency Quantiles (p95) |
| C | `LLM_MODEL=mock-llm-large` | HighTokenConsumption | ~30s | Token Usage / Cost |
| D | `docker pause` 1 instance | InstanceDown | ~10s | Active Targets / Up |
| E | `AGENT_VERSION=v1` | Không có alert hệ thống | N/A | Golden Dataset Eval Gate |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**
Sự cố tụt giảm độ chính xác tri thức (semantic regression) không gây lỗi HTTP hay chậm mạng nên metrics hạ tầng không báo động. Cách phát hiện là chạy định kỳ **Automated Continuous Eval (Quality Gate)** với bộ Golden Dataset trên môi trường staging/canary trước khi rollout, kết hợp thu thập user feedback (thumbs up/down) trong production.

### 4.3 Debug bằng trace

- `trace_id`: `4f8a9b2c3d1e0f7a`
- Span chậm nhất: `call_llm` chiếm 420ms trên tổng số 450ms của request.
- Log JSON tương ứng:
```json
{"ts": "2026-11-26T15:45:12Z", "lvl": "INFO", "trace_id": "4f8a9b2c3d1e0f7a", "event": "llm_completion", "latency_ms": 420.5, "status": 200}
```
