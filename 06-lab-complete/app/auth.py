"""
API Key authentication (tiêu chí 6).
"""
from fastapi import Header, HTTPException
from app.config import settings


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Dependency cho FastAPI — dùng trong /ask: Depends(verify_api_key)."""
    if not x_api_key or x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
