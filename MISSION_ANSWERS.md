# Day 14 Lab — Mission Answers

**Lớp:** K5-L3B  

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`
1. **Hardcoded Secrets:** API key được gán cứng trực tiếp trong source code (`AGENT_API_KEY = "super-secret-key-12345"`), dễ bị lộ khi commit lên Git.
2. **Hardcoded Port / Configuration:** Cổng ứng dụng bị cố định ở port 8000, không đọc từ biến môi trường `PORT` (vi phạm 12-Factor App).
3. **Thiếu Health & Readiness Endpoints:** Không có route `/health` (liveness) và `/ready` (readiness) để orchestrator (Kubernetes, Cloud Run, Docker) kiểm tra trạng thái hoạt động của container.
4. **Bật chế độ Debug trong Production:** `debug=True` làm lộ stack trace và thông tin nhạy cảm của hệ thống khi có ngoại lệ xảy ra.
5. **Stateful Design (Lưu state trong RAM):** Lịch sử hội thoại lưu trong danh sách bộ nhớ tạm thời (`_history = []`), dẫn đến việc mất dữ liệu khi restart app hoặc lỗi đồng bộ khi chạy multi-instance.
6. **Không có Graceful Shutdown:** Ứng dụng ngắt ngang khi nhận SIGTERM, làm hủy hoại các request đang xử lý dở.
7. **Logging dạng Text thô:** Log in ra terminal bằng `print()` hoặc text thông thường, không thể phân tích và truy vấn tập trung bằng các hệ thống observability (ELK, Loki).

### Exercise 1.2: Chạy bản develop

Ví dụ về cấu hình cổng: [Bản develop gán cứng `port=8000`](01-localhost-vs-production/develop/app.py#L52). [Bản production đọc biến `PORT`](01-localhost-vs-production/production/config.py#L18) và [truyền cổng đã đọc cho Uvicorn](01-localhost-vs-production/production/app.py#L197). Nền tảng deploy có thể cấp cổng qua env mà không cần đổi mã nguồn.

App mẫu bind vào loopback, vì vậy hai request được gọi từ bên trong container chạy bản develop.

```text
GET / → HTTP 200
{"message":"Hello! Agent is running on my machine :)"}

POST /ask?question=Hello → HTTP 200
{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

### Exercise 1.3: Comparison table

| Tiêu chí | Develop | Production | Tại sao quan trọng? |
|---|---|---|---|
| Cấu hình & Secret | Gán cứng trong code | Đọc từ Environment Variables (`os.getenv`) | Bảo mật secret, linh hoạt đổi config theo từng môi trường dev/staging/prod mà không cần build lại code |
| Health Check | Không có | Có `/health` (liveness) và `/ready` (readiness) | Giúp Load Balancer tự động ngắt tải tới container lỗi và tự khởi động lại khi crash |
| Quản lý State | Lưu trong RAM bộ nhớ | Lưu tập trung trong Redis | Đảm bảo kiến trúc Stateless để có thể scale ngang nhiều instances |
| Xử lý tắt ứng dụng | Tắt đột ngột (Hard kill) | Graceful Shutdown (bắt SIGTERM) | Đảm bảo xử lý trọn vẹn request đang chạy, đóng kết nối DB sạch sẽ trước khi thoát |
| Logging | `print()` text thông thường | Structured JSON logging | Cho phép ingest, filter, alert tự động trên Datadog, CloudWatch, Grafana Loki |

---

## Part 2: Docker & Containerization

### Exercise 2.1: Dockerfile Questions
1. **Base image:** Sử dụng `python:3.11-slim` (hoặc alpine) để giảm thiểu kích thước và loại bỏ các gói build không cần thiết.
2. **Working directory:** Đặt thư mục làm việc chuẩn là `/app` để cô lập mã nguồn.
3. **Thứ tự layer caching:** `COPY requirements.txt .` và `RUN pip install ...` được đặt trước `COPY . .`. Khi thay đổi source code, Docker tái sử dụng cache của layer cài thư viện, giúp build cực nhanh.
4. **Bảo mật Non-root user:** Chạy ứng dụng dưới quyền user không có đặc quyền (`appuser`) thay vì `root`, ngăn chặn nguy cơ leo thang đặc quyền khi container bị tấn công.

### Exercise 2.3: Image size comparison
Build hai image từ gốc repo với Dockerfile tương ứng rồi đo bằng `docker image inspect`.

| Image | Kích thước |
|---|---:|
| Develop, single-stage | 1.667,79 MB |
| Production, multi-stage | 239,84 MB |

Image production nhỏ hơn khoảng **85,62%**. Stage builder giữ compiler và công cụ build, còn runtime dùng base slim và copy các dependency đã cài.

### Exercise 2.4: Sơ đồ Service Stack và Kết quả qua Nginx
- Sơ đồ: `Client → Nginx → Agent → Redis (state) và Qdrant (vector store)`.
- Kiểm tra image develop: `GET /health` trả HTTP 200 với `{"status":"ok","uptime_seconds":2.8,"container":true}`.
- Kiểm tra stack production qua Nginx trên cổng local 18102: `GET /health` trả HTTP 200, `status=ok`, `version=2.0.0`. `POST /ask` với câu hỏi `Explain microservices` trả HTTP 200 và câu trả lời mock.

---

## Part 3: Cloud Deployment

### Exercise 3.1 & 3.2: So sánh Railway vs Render

- URL public trên Railway: https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app
- **Railway (`railway.toml`):**
  - Cấu hình gọn gàng, hỗ trợ khai báo builder (`DOCKERFILE`), chỉ định healthcheck path (`/health`) và chính sách tự động restart.
  - Tích hợp sẵn Redis plugin kết nối mạng nội bộ private rất nhanh.
- **Render (`render.yaml`):**
  - Hỗ trợ mô hình Blueprint Infrastructure-as-Code (IaC) khai báo đồng thời Web Service và Redis/Postgres.
  - Hỗ trợ quản lý secret an toàn (`generateValue: true` hoặc `sync: false`), không ghi lộ secret trên git.

### Exercise 3.3: Mô tả Pipeline CI/CD trên Google Cloud Run
Đọc từ `cloudbuild.yaml` và `service.yaml`:
1. Bước `test` cài dependencies và chạy kiểm tra trước khi build.
2. Bước `build` tạo Docker image với hai tag `$COMMIT_SHA` và `latest`.
3. Bước `push` đẩy image lên Container Registry. Bước `deploy` gọi `gcloud run deploy` với image gắn tag commit để Cloud Run tạo revision mới.
4. `service.yaml` mô tả cấu hình service, gồm container và thiết lập tài nguyên, scale.

---

## Part 4: API Security

### Exercise 4.1 – 4.3: Kết quả kiểm tra Authentication & Rate Limiting (cURL Output)

1. **Thiếu API Key (HTTP 401):**
```text
HTTP/1.1 401 Unauthorized
content-type: application/json
{"detail": "Invalid or missing API key"}
```

2. **API Key hợp lệ (HTTP 200):**
```text
HTTP/1.1 200 OK
content-type: application/json
{"question": "Hello", "answer": "Mock LLM answer for: Hello"}
```

3. **Vượt Rate Limit 10 req/phút (HTTP 429):**
```text
HTTP/1.1 429 Too Many Requests
retry-after: 60
content-type: application/json
{"detail": "Rate limit exceeded"}
```

**Kết quả chạy lại hai app mẫu qua HTTP trên Ubuntu WSL**

```text
Develop     POST /ask thiếu API key                → 401
Develop     POST /ask có API key hợp lệ            → 200
Production  POST /ask thiếu JWT                    → 401
Production  POST /auth/token với tài khoản demo    → 200
Production  POST /ask với JWT, request 1–10        → 200
Production  POST /ask với JWT, request 11–12       → 429
```

### Exercise 4.4: Thiết kế Cost Guard bảo vệ ngân sách
- Sử dụng Redis để cộng dồn chi phí token (`cost_guard:total_cost_usd`) sau mỗi lần gọi LLM.
- Trước khi gọi LLM, hàm `check_budget()` kiểm tra tổng chi phí hiện tại. Nếu vượt ngưỡng `DAILY_BUDGET_USD` (hoặc `MONTHLY_BUDGET_USD`), chặn ngay lập tức và trả về mã lỗi **HTTP 402 Payment Required** (hoặc Budget Exceeded), giúp ngăn chặn sự cố cạn kiệt ngân sách do vòng lặp vô tận hoặc tấn công DoS chi phí.

---

## Part 5: Scaling & Reliability

### Exercise 5.1 – 5.5: Phân tích và Thực nghiệm

1. **Liveness (`/health`) vs Readiness (`/ready`):**
   - `/health`: Báo hiệu tiến trình app còn sống. Luôn trả 200 khi container đang chạy (dù Redis tạm thời mất kết nối). Nếu endpoint này chết, orchestrator sẽ kill và restart container.
   - `/ready`: Báo hiệu agent đã sẵn sàng nhận traffic phục vụ người dùng (phải kết nối được Redis). Nếu mất kết nối Redis, `/ready` trả 503 để Load Balancer tạm thời không chuyển request tới instance này.

2. **Stateless với Redis:**
   - Chạy kịch bản `test_stateless.py` trên stack Part 5 với ba replica. Dùng cổng local 18105 trong lần kiểm tra để tránh trùng cổng 8080 với stack observability.

```text
Total requests: 5
Instances used: {'instance-39b6db', 'instance-9c8c05', 'instance-9cc32d'}
Total messages: 10
Session history preserved across all instances via Redis!
```

   - Ba instance phục vụ cùng một session. Redis dùng chung giữ đủ năm câu hỏi và năm câu trả lời.

3. **Graceful Shutdown (SIGTERM):**
   - Khi nhận SIGTERM (ví dụ từ `docker stop` hoặc rolling update), agent sử dụng cơ chế `lifespan` của FastAPI để hoàn tất tất cả request đang xử lý dở trước khi thoát. Uvicorn forward SIGTERM vào ứng dụng thông qua PID 1 (cú pháp `exec uvicorn ...` trong Dockerfile CMD đảm bảo điều này).
   - Thực nghiệm: Gửi request tốn thời gian (giả lập slow LLM) rồi ngay lập tức gửi SIGTERM → request vẫn trả 200, không bị ngắt giữa chừng.

4. **Rate Limiting bằng Redis Sliding Window:**
   - Mỗi API key có một Sorted Set trong Redis (`rate_limit:<key>`). Mỗi request được ghi với timestamp, các entry cũ hơn 60 giây bị xóa (`ZREMRANGEBYSCORE`). Khi count ≥ limit → 429 kèm header `Retry-After: 60`.
   - Kết quả kiểm tra: Sau đúng 10 request hợp lệ trong 60 giây, request thứ 11 trả `HTTP 429 Too Many Requests`.

5. **Cost Guard:**
   - Redis lưu tổng chi phí tích lũy theo key `cost_guard:total_cost_usd` bằng `INCRBYFLOAT`. Mỗi request gọi LLM ước tính số token (input_tokens/1000 × price_in + output_tokens/1000 × price_out) rồi cộng vào tổng. Khi tổng vượt `DAILY_BUDGET_USD` → chặn ngay bằng HTTP 402, không gọi LLM thêm.
   - Điều này ngăn vòng lặp vô tận hoặc tấn công "prompt flooding" tiêu tốn toàn bộ ngân sách API trong thời gian ngắn.

---

## Part 6: Final Project Deliverable Checklist

Kiểm tra lại ngày 26/11/2026 bằng `python3 check_production_ready.py` trong Ubuntu WSL có Docker. Kết quả bản hiện tại:
```text
================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

---

## Mục Khai Báo Sử Dụng AI (AI Log — theo RULES.md)
- **Công cụ sử dụng:** Antigravity AI Assistant và Codex.
- **Hỗ trợ của Codex:** Đối chiếu log Railway và Docker, sửa đường dẫn thư viện Python trong Dockerfile Part 7, tổng hợp bảng scaling từ CSV và rà soát ba tài liệu nộp.
- **Bằng chứng kiểm tra:** Người làm bài chạy lại stack sau khi sửa Dockerfile và ghi nhận ba agent healthy, gọi thử bốn endpoint Railway, chạy Locust và chụp ảnh Grafana, Jaeger, Prometheus. Các số scaling được đối chiếu với CSV.
- **Rà soát bổ sung:** Codex chạy mẫu Part 1, đo image và gọi qua Nginx Part 2, chạy lại bài stateless Part 5 và script chấm Part 6 trên máy local. Mốc alert được đối chiếu với lịch sử Prometheus và trace được đối chiếu với log JSON của agent.
- **Kiểm tra cuối:** Codex chạy lại HTTP test API key/JWT của Part 4, truy vấn mẫu Prometheus để trả lời Exercise 7.4 và đối chiếu ảnh deploy với các mã HTTP đã xác nhận.
- **Nội dung hỏi:**
  - Hướng dẫn cấu hình môi trường WSL2 / Docker trên Windows 11.
  - Phân tích yêu cầu và kiến trúc chuẩn 12 tiêu chí Production-ready AI Agent.
  - Thiết kế cấu trúc JSON Formatter logging, cơ chế Rate Limiting và Cost Guard trên Redis.
- **Tự kiểm tra và hiệu chỉnh:**
  - Tự chạy script kiểm tra `python check_production_ready.py` để xác minh từng tiêu chí.
  - Tự deploy và kiểm chứng 4 lệnh curl trên Cloud công khai.
