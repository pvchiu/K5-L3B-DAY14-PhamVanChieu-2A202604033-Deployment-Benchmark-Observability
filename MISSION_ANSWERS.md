# Day 14 Lab — Mission Answers

**Họ và tên:** Phạm Văn Chiêu  
**Mã số sinh viên:** 2A202604033  
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
- **Develop image (Single-stage, full Python):** ~1020 MB
- **Production image (Multi-stage, slim):** 238 MB (đo thực tế bằng `check_production_ready.py`)
- **Chênh lệch giảm dung lượng:** ~76.7% (giúp tiết kiệm băng thông và tăng tốc độ deploy/cold-start đáng kể).

### Exercise 2.4: Sơ đồ Service Stack và Kết quả qua Nginx
- Sơ đồ: `Client -> Nginx (Reverse Proxy / Load Balancer port 80) -> Agent 1 / Agent 2 / Agent 3 -> Redis (State/Session)`
- Gọi API qua Nginx: Request phân phối đều giữa các instance (Load balancing round-robin) và trả về HTTP 200 kèm `instance_id` khác nhau.

---

## Part 3: Cloud Deployment

### Exercise 3.1 & 3.2: So sánh Railway vs Render
- **Railway (`railway.toml`):**
  - Cấu hình gọn gàng, hỗ trợ khai báo builder (`DOCKERFILE`), chỉ định healthcheck path (`/health`) và chính sách tự động restart.
  - Tích hợp sẵn Redis plugin kết nối mạng nội bộ private rất nhanh.
- **Render (`render.yaml`):**
  - Hỗ trợ mô hình Blueprint Infrastructure-as-Code (IaC) khai báo đồng thời Web Service và Redis/Postgres.
  - Hỗ trợ quản lý secret an toàn (`generateValue: true` hoặc `sync: false`), không ghi lộ secret trên git.

### Exercise 3.3: Mô tả Pipeline CI/CD trên Google Cloud Run
Đọc từ `cloudbuild.yaml` và `service.yaml`:
1. **Build Step:** Cloud Build kích hoạt khi có commit, sử dụng Docker build multi-stage đóng gói agent thành container image.
2. **Push Step:** Image được đẩy lên Google Artifact Registry (hoặc Container Registry) có gắn tag commit SHA.
3. **Deploy Step:** Cloud Build gọi lệnh `gcloud run services replace service.yaml` để cập nhật revision mới trên Cloud Run với cơ chế Zero-Downtime, tự động scale to zero khi không có request và scale out khi tải tăng.

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
   - Khi chạy 3 instances agent, request của cùng 1 user được phân phối tới instance ngẫu nhiên. Nhờ lưu trữ rate limit và session state trên Redis dùng chung, người dùng không bao giờ bị mất ngữ cảnh hay bypass được giới hạn tốc độ.

---

## Part 6: Final Project Deliverable Checklist

Output từ script chấm tự động `python check_production_ready.py`:
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
- **Công cụ sử dụng:** Antigravity AI Assistant.
- **Nội dung hỏi:**
  - Hướng dẫn cấu hình môi trường WSL2 / Docker trên Windows 11.
  - Phân tích yêu cầu và kiến trúc chuẩn 12 tiêu chí Production-ready AI Agent.
  - Thiết kế cấu trúc JSON Formatter logging, cơ chế Rate Limiting và Cost Guard trên Redis.
- **Tự kiểm tra và hiệu chỉnh:**
  - Tự chạy script kiểm tra `python check_production_ready.py` để xác minh từng tiêu chí.
  - Tự deploy và kiểm chứng 4 lệnh curl trên Cloud công khai.
