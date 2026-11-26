"""
Cost guard (tiêu chí 8).
"""
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

REDIS_COST_KEY = "cost_guard:total_cost_usd"


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    try:
        val = r.get(REDIS_COST_KEY)
        total = float(val) if val else 0.0
        if total >= settings.daily_budget_usd:
            raise HTTPException(status_code=402, detail="Budget exceeded")
    except HTTPException:
        raise
    except Exception:
        pass


def record_cost(input_tokens: int = 15, output_tokens: int = 25) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = (input_tokens / 1000.0 * PRICE_INPUT_PER_1K) + (output_tokens / 1000.0 * PRICE_OUTPUT_PER_1K)
    if cost <= 0:
        cost = 0.00001
    try:
        r.incrbyfloat(REDIS_COST_KEY, cost)
    except Exception:
        pass
    return cost
