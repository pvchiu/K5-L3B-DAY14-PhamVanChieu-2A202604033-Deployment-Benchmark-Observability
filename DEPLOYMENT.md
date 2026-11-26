# Deployment Information — Day 14

## Public URL
https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app

## Platform
Railway

## Test Commands

### 1. Health Check
```bash
curl https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app/health
# Expected: {"status": "ok"}
```

### 2. Readiness Check
```bash
curl https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app/ready
# Expected: {"status": "ready"}
```

### 3. API Test (Without Key — 401 Expected)
```bash
curl -i -X POST https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
# Expected HTTP 401 Unauthorized
```

### 4. API Test (With Key — 200 Expected)
```bash
curl -i -X POST https://k5-l3b-day14-phamvanchieu-2a202604033-deployment-production.up.railway.app/ask \
  -H "X-API-Key: YOUR_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
# Expected HTTP 200 OK
```

## Environment Variables Set on Platform
- `PORT`: cổng lắng nghe quan sát trong Deploy Logs là `8080`, khớp Target Port của domain.
- `ENVIRONMENT`: production
- `AGENT_API_KEY`: [Configured via Platform Environment Variables]
- `REDIS_URL`: đã cấu hình trên Railway. Kiểm tra `/ready` trả HTTP 200.
- `RATE_LIMIT_PER_MINUTE`: 10
- `DAILY_BUDGET_USD`: 10.0

## Kết quả đã xác nhận

| Kiểm tra | HTTP |
|---|---:|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` thiếu key | 401 |
| `POST /ask` có key hợp lệ | 200 |

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running và Deploy Logs của cả bốn kiểm tra](screenshots/running.png)
- [Kết quả POST /ask có key, HTTP 200](screenshots/test.png)
- [Kết quả GET /health, HTTP 200](screenshots/test3.png)
- [Kết quả GET /ready, HTTP 200](screenshots/test4.png)
