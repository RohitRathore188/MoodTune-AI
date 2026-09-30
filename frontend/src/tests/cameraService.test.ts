import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CameraService } from '../services/cameraService';

describe('CameraService Real-Time Pipeline (Phase 2)', () => {
  let service: CameraService;
  let mockVideo: HTMLVideoElement;
  let mockStream: MediaStream;

  beforeEach(() => {
    vi.restoreAllMocks();
    service = new CameraService(500);

    mockStream = {
      getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }])
    } as unknown as MediaStream;

    mockVideo = {
      srcObject: null,
      play: vi.fn().mockResolvedValue(undefined),
      videoWidth: 480,
      videoHeight: 360,
      readyState: 4
    } as unknown as HTMLVideoElement;
  });

  afterEach(() => {
    service.stop();
  });

  it('initializes in OFF state with idle face status', () => {
    const state = service.getState();
    expect(state.cameraStatus).toBe('off');
    expect(state.faceStatus).toBe('idle');
    expect(state.faceCount).toBe(0);
    expect(state.primaryFace).toBeNull();
  });

  it('transitions to ACTIVE state when camera permission is granted', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream)
      }
    });

    await service.start(mockVideo);

    const state = service.getState();
    expect(state.cameraStatus).toBe('active');
    expect(mockVideo.srcObject).toBe(mockStream);
    expect(mockVideo.play).toHaveBeenCalled();
  });

  it('handles camera permission denial gracefully (NotAllowedError)', async () => {
    const deniedErr = new Error('Permission denied');
    deniedErr.name = 'NotAllowedError';

    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockRejectedValue(deniedErr)
      }
    });

    await service.start(mockVideo);

    const state = service.getState();
    expect(state.cameraStatus).toBe('permission_denied');
    expect(state.errorMessage).toContain('Camera permission was denied');
  });

  it('handles camera hardware failure (NotFoundError / device busy)', async () => {
    const hwErr = new Error('Camera busy or not found');
    hwErr.name = 'NotFoundError';

    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockRejectedValue(hwErr)
      }
    });

    await service.start(mockVideo);

    const state = service.getState();
    expect(state.cameraStatus).toBe('hardware_error');
    expect(state.errorMessage).toContain('Camera hardware error');
  });

  it('supports pause and resume detection while maintaining camera preview', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream)
      }
    });

    await service.start(mockVideo);
    expect(service.getState().cameraStatus).toBe('active');

    service.pauseDetection();
    expect(service.getState().cameraStatus).toBe('paused');
    expect(service.getState().statusMessage).toContain('Detection paused');

    service.resumeDetection();
    expect(service.getState().cameraStatus).toBe('active');
  });

  it('stops video tracks and returns to OFF when stop() is called', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream)
      }
    });

    await service.start(mockVideo);
    service.stop();

    const state = service.getState();
    expect(state.cameraStatus).toBe('off');
    expect(mockVideo.srcObject).toBeNull();
  });
});
