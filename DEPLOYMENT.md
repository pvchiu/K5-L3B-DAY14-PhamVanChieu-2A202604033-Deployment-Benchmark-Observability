# Deployment Information — Day 14

## Public URL
https://k5-day14-agent-production.up.railway.app

## Platform
Railway (hoặc Render)

## Test Commands

### 1. Health Check
```bash
curl https://k5-day14-agent-production.up.railway.app/health
# Expected: {"status": "ok"}
```

### 2. Readiness Check
```bash
curl https://k5-day14-agent-production.up.railway.app/ready
# Expected: {"status": "ready"}
```

### 3. API Test (Without Key — 401 Expected)
```bash
curl -i -X POST https://k5-day14-agent-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
# Expected HTTP 401 Unauthorized
```

### 4. API Test (With Key — 200 Expected)
```bash
curl -i -X POST https://k5-day14-agent-production.up.railway.app/ask \
  -H "X-API-Key: YOUR_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is deployment?"}'
# Expected HTTP 200 OK
```

## Environment Variables Set on Platform
- `PORT`: 8000
- `ENVIRONMENT`: production
- `AGENT_API_KEY`: [Configured via Platform Environment Variables]
- `REDIS_URL`: redis://default:password@host:port
- `RATE_LIMIT_PER_MINUTE`: 10
- `DAILY_BUDGET_USD`: 10.0

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
