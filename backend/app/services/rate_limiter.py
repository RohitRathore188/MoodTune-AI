"""In-memory rate limiter for high-frequency computer vision & affect endpoints."""
import time
from collections import deque
from typing import Dict
from fastapi import Request, HTTPException
from ..config import settings


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter per client IP."""
    def __init__(self, max_requests_per_second: int = 10):
        self.max_requests = max_requests_per_second
        self._clients: Dict[str, deque] = {}

    def check(self, client_id: str, limit: int = None) -> bool:
        max_allowed = limit or self.max_requests
        now = time.time()
        window_start = now - 1.0

        if client_id not in self._clients:
            self._clients[client_id] = deque()

        queue = self._clients[client_id]
        # Evict timestamps older than 1 second
        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= max_allowed:
            return False

        queue.append(now)
        return True


rate_limiter = InMemoryRateLimiter(max_requests_per_second=settings.RATE_LIMIT_REQUESTS_PER_SECOND)


async def check_rate_limit(request: Request):
    """FastAPI dependency to throttle heavy vision and mood analysis requests."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests: Camera/affect streaming rate limit exceeded. Please throttle requests."
        )
