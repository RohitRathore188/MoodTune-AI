import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../services/api';

describe('Frontend API Client - Foundation Test', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches health diagnostics successfully', async () => {
    const mockHealth = {
      status: 'healthy',
      app: 'MoodTune AI',
      environment: 'development',
      uptime_seconds: 42.0,
      ai_providers: {
        jev: { configured: false, sdk_available: true, model: 'typesafe/jev-1.13', fallback_active: true },
        music_provider: { type: 'local', status: 'active' },
        camera_cv: { status: 'ready', storage_policy: 'in_memory_only (never persisted to disk/db)' }
      }
    };

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth
    }));

    const health = await api.getHealth();
    expect(health.status).toBe('healthy');
    expect(health.app).toBe('MoodTune AI');
    expect(health.ai_providers.camera_cv.storage_policy).toContain('in_memory_only');
    expect(fetch).toHaveBeenCalled();
  });

  it('handles backend communication failures gracefully', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      statusText: 'Service Unavailable'
    }));

    await expect(api.getPreferences()).rejects.toThrow('Failed to load preferences');
  });
});
