# MoodTune AI — API Contracts Specification

## Health & Diagnostics

### `GET /api/health`
Checks backend readiness, active AI decision provider, database connection, and storage policies.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "app": "MoodTune AI",
  "environment": "development",
  "uptime_seconds": 12.4,
  "ai_providers": {
    "jev": {
      "configured": false,
      "sdk_available": true,
      "model": "typesafe/jev-1.13",
      "fallback_active": true
    },
    "music_provider": {
      "type": "local",
      "status": "active"
    },
    "camera_cv": {
      "status": "ready",
      "storage_policy": "in_memory_only (never persisted to disk/db)"
    }
  }
}
```

## Error Handling Standards
All exceptions return uniform JSON payloads:
```json
{
  "error": "Internal server error | Bad Request | Not Found",
  "message": "Human-readable diagnostic description"
}
```
HTTP Status Codes:
- `200 OK`: Request succeeded.
- `400 Bad Request`: Input validation error.
- `404 Not Found`: Resource or entity missing.
- `500 Internal Server Error`: Server exception with structured log trace.
