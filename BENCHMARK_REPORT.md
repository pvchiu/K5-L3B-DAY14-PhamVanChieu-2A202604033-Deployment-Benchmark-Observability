# Benchmark & Observability Report — Day 14

**Họ tên:** Phạm Văn Chiêu  
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

Trong CI, chạy `eval/run_eval.py` với ngưỡng accuracy và baseline đã chọn. Exit code `1` làm job thất bại nếu accuracy dưới ngưỡng hoặc có regression. Đặt job đó làm kiểm tra bắt buộc để chặn merge khi eval thất bại.

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải: `screenshots/grafana-dashboard.png`
- [x] Một trace chậm trong Jaeger: `screenshots/jaeger-slow-trace.png`
- [x] Một trace lỗi trong Jaeger: `screenshots/jaeger-error-trace.png`
- [x] Trang Alerts của Prometheus với ít nhất 2 alert đang **firing**: `screenshots/prometheus-alert-firing.png`

**Exercise 7.4**

1. Mẫu Prometheus lúc 17:38:00 ngày 26/11/2026 (GMT+7) cho `POST /ask` có p95 **294,23 ms** và trung bình **237,80 ms**. Chênh khoảng **56,43 ms** cho thấy nhóm request chậm có thời gian phản hồi cao hơn mức trung bình. Tile p95 trong ảnh Grafana ở thời điểm chụp hiển thị **293,86 ms**.
2. Cùng mẫu đó, ba replica nhận lần lượt **2,16**, **2,15** và **2,10 req/s**. Tải được phân phối gần đều trên ba replica của lần chạy này.
3. Input khoảng **490,24 token/s**, output khoảng **253,92 token/s**. Agent v2 đưa câu hỏi cùng context truy xuất vào prompt, nên lượng token đầu vào lớn hơn lượng token từ câu trả lời.
4. `GET http://localhost:8080/metrics` trả **HTTP 404**. Nginx chặn đường dẫn này và Prometheus scrape trực tiếp từ agent qua mạng nội bộ Docker.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | Khoảng 74,0 giây | Error rate khoảng 22,36%, vượt ngưỡng 5% |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | Khoảng 134,4 giây | p95 khoảng 1,89 giây, vượt ngưỡng 1 giây |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | Khoảng 144,1 giây | Chi phí ước tính 15,88 USD/giờ, vượt ngưỡng 2 USD/giờ |
| D | `docker pause` 1 instance | `AgentInstanceDown` | Khoảng 40,3 giây | Prometheus ghi `up=0` cho instance bị pause |
| E | `AGENT_VERSION=v1` | So sánh kết quả eval local | Không áp dụng | Quality gate: v1 đúng 1/23, v2 sau khi sửa đúng 23/23 |

Đo lại A và B cùng lúc ngày 26/11/2026. Bắt đầu tính lúc chạy lệnh áp dụng cấu hình lúc 21:04:39, giờ Việt Nam, rồi chạy Locust với 30 users, ramp-up 5 users/giây. API Prometheus được kiểm tra khoảng 2 giây một lần. Ảnh Alerts chụp ở lần chạy trước cho thấy hai alert cùng firing, với error rate khoảng 20,05% và p95 khoảng 1,88 giây.

Ở C, thời gian được tính từ lúc chạy lệnh đổi model lúc 21:06:59, với cùng cấu hình tải. Chi phí là ước tính của mock LLM.

Ở D, thời gian được tính từ lúc chạy `docker pause` lúc 21:09:43. Container vẫn là một target trong Docker DNS nhưng Prometheus không scrape được. Sau khi ghi nhận alert, dùng `docker unpause` để khôi phục replica.

Kiểm thử rule bằng `promtool test rules /p/alert_rules_test.yml` trả về `SUCCESS`.

**Phát hiện regression chất lượng trong production**
Sự cố tụt giảm độ chính xác tri thức (semantic regression) không gây lỗi HTTP hay chậm mạng nên metrics hạ tầng không báo động. Cách phát hiện là chạy định kỳ **Automated Continuous Eval (Quality Gate)** với bộ Golden Dataset trên môi trường staging/canary trước khi rollout, kết hợp thu thập user feedback (thumbs up/down) trong production.

### 4.3 Debug bằng trace

- [Trace chậm](screenshots/jaeger-slow-trace.png): `POST /ask` trả HTTP 200 trong khoảng 1,8 giây. Span con chậm nhất là `chat mock-llm-small`, khoảng 1,7 giây. Log ghi LLM mất **1.673,7 ms**, còn span `agent.retrieve_context` trên ảnh mất **17,4 ms**. ID trên ảnh bắt đầu bằng `0ba9162`.
- [Trace lỗi](screenshots/jaeger-error-trace.png): `POST /ask` trả HTTP 503 trong **124 ms**. Span `chat mock-llm-small` có dấu lỗi đỏ và kéo dài khoảng **102 ms**. Log ghi `Upstream LLM error: 503 Service Unavailable (mock)`. ID trên ảnh bắt đầu bằng `9632d80`.
- Hai ảnh Jaeger và hai dòng log bên dưới khớp theo `trace_id`. Jaeger API trả HTTP 200 khi truy vấn các ID đầy đủ.

```jsonl
{"ts":"2026-11-26T12:43:29.715007+00:00","level":"INFO","service":"observable-agent","instance":"5a1a08cccba7","event":"llm_call","trace_id":"0ba9162a2e8a6642fc775e816def2160","span_id":"0959f406deb0a95c","request_id":"64839ce8605b","model":"mock-llm-small","agent_version":"v2","input_tokens":95,"output_tokens":55,"cost_usd":4.7e-05,"llm_ms":1673.7}
{"ts":"2026-11-26T13:31:19.789196+00:00","level":"INFO","service":"observable-agent","instance":"5a1a08cccba7","event":"llm_error","trace_id":"9632d80ec33254219b8caa863f3c6ee8","span_id":"1445a526010567aa","request_id":"6775c75d5f2d","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling (Locust headless, 100 users, 2 phút)

Số liệu lấy từ dòng `POST /ask` trong hai file CSV đã lưu ở thư mục `benchmark-results/`.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---:|---:|---:|---:|---:|
| 1 | 59,45 | 190 | 250 | 1.700 | 69/7.073 (0,98%) |
| 3 | 59,34 | 190 | 250 | 1.700 | 67/7.062 (0,95%) |

Với mức tải này, tăng từ 1 lên 3 instance giữ p95 ở 250 ms và RPS gần như bằng nhau. p99 vẫn ở 1.700 ms, phù hợp với độ trễ của một số lượt gọi mock LLM. Kết quả ở mức tải này chưa đủ để xác định giới hạn thông lượng của từng cấu hình. Cả hai lượt ghi nhận HTTP 503 ở `/ask` và không có lỗi ở `/health`.

## 6. Kết luận

1. p95 và p99 giúp quan sát tác động của các request chậm mà độ trễ trung bình dễ che khuất.
2. Eval đo chất lượng câu trả lời. Sau khi bổ sung kiến thức, v2 đạt 23/23 câu đúng trong quality gate.
3. Chạy cùng kịch bản trên 1 và 3 instance cho phép so sánh khả năng scale. Ở lượt đo này, p95 và RPS gần như giữ nguyên.

Nếu đưa agent vào production, bổ sung metric tỷ lệ lỗi theo mã HTTP ở Nginx và alert cho lỗi 502/504 để phát hiện sự cố proxy hoặc timeout.
