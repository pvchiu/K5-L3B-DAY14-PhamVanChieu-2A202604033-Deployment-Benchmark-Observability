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
| Error rate `/ask` | < 2.0 % | Hệ thống production cần độ tin cậy cao, tỷ lệ lỗi dưới 2% |
| Accuracy trên golden dataset | ≥ 95 % (mục tiêu 100%) | Đảm bảo chất lượng câu trả lời chuẩn xác theo tri thức đã định nghĩa |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.55 | 190.3 | 216.4 | 1672.1 | 1.33% | PASS |
| 10 | 34.94 | 191.6 | 221.9 | 1713.2 | 1.67% | PASS |
| 50 | 104.83 | 191.1 | 240.2 | 1698.3 | 0.67% | PASS |
| 100 | 51.38 | 404.0 | 3834.0 | 4272.3 | 0.00% | FAIL |

**Nhận xét:** RPS tăng mạnh từ concurrency 1 (4.55) đến 50 (104.83 req/s), nhưng khi nâng lên 100 concurrency thì RPS giảm xuống 51.38 req/s và latency p95 nhảy vọt lên 3834ms (vi phạm SLO). Lý do là một tiến trình agent đơn lẻ bị tắc nghẽn hàng đợi (event loop queuing delay) khi tải vượt quá khả năng xử lý đồng thời, chứng minh sự cần thiết của việc scale ngang nhiều instance sau Load Balancer.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 189.5 | 217.0 | 223.0 |
| 0.03 (mặc định) | 217.9 | 220.3 | 1691.2 |
| 0.1 | 334.9 | 1693.3 | 1714.0 |

**Nhận xét:** Chỉ số p99 và p95 nhạy nhất với request chậm. Khi `MOCK_SLOW_RATE` tăng từ 0 lên 0.1, latency trung bình chỉ tăng từ 189.5ms lên 334.9ms (vẫn che giấu vấn đề), nhưng p95 đã nhảy vọt từ 217ms lên 1693.3ms. Vì vậy SLO bắt buộc phải đặt theo percentile (p95/p99) thay vì average để bắt đúng trải nghiệm của nhóm người dùng bị chậm.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 56.4 | 108.8 | 112.5 |
| Tổng cost (USD) | $0.000394 | $0.000757 | $0.000781 |
| Cost / câu đúng (USD) | $0.000394 | $0.000036 | $0.000034 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Bổ sung định nghĩa JWT (token có chữ ký số và thời gian hết hạn) vào `KNOWLEDGE_BASE` |
| scaling-03 | cpu, memory, custom metrics | Bổ sung cơ chế Kubernetes HPA (tự động scale theo CPU, memory, custom metrics) vào `KNOWLEDGE_BASE` |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**
Agent v2 tiêu tốn token gấp đôi v1 (112.5 vs 56.4) do bổ sung context truy xuất (retrieval), làm tổng chi phí tăng nhẹ. Tuy nhiên, vì v2 trả lời đúng 100% câu hỏi thay vì 4.35% như v1, **chi phí trên mỗi câu trả lời đúng (Cost / câu đúng)** của v2 giảm hơn 11 lần (từ $0.000394 xuống $0.000034). Điều này chứng minh việc đầu tư thêm chi phí prompt context mang lại hiệu quả kinh tế vượt trội so với câu trả lời sai.

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
