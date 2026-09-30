import { api } from './api';
import type { FaceDetectionResult, BoundingBox } from '../types';

export type CameraStatus =
  | 'off'
  | 'initializing'
  | 'active'
  | 'paused'
  | 'permission_denied'
  | 'hardware_error';

export type FaceStatus =
  | 'idle'
  | 'no_face'
  | 'single_face'
  | 'multiple_faces'
  | 'processing'
  | 'error';

export interface CameraServiceState {
  cameraStatus: CameraStatus;
  faceStatus: FaceStatus;
  faceCount: number;
  primaryFace: BoundingBox | null;
  allFaces: BoundingBox[];
  confidence: number;
  inferenceTimeMs: number;
  errorMessage: string | null;
  statusMessage: string;
}

export class CameraService {
  private stream: MediaStream | null = null;
  private videoEl: HTMLVideoElement | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private loopIntervalId: any = null;
  private isProcessingFrame: boolean = false;
  private sampleIntervalMs: number = 1200;

  private state: CameraServiceState = {
    cameraStatus: 'off',
    faceStatus: 'idle',
    faceCount: 0,
    primaryFace: null,
    allFaces: [],
    confidence: 0,
    inferenceTimeMs: 0,
    errorMessage: null,
    statusMessage: 'Camera is currently off.'
  };

  private listeners: Set<(state: CameraServiceState) => void> = new Set();
  public onFrameCaptured?: (b64: string, faceResult: FaceDetectionResult) => void;
  public frameAnalyzer?: (b64: string) => Promise<FaceDetectionResult>;

  constructor(sampleIntervalMs: number = 1200) {
    this.sampleIntervalMs = sampleIntervalMs;
    if (typeof document !== 'undefined') {
      this.canvas = document.createElement('canvas');
    }
  }

  public subscribe(listener: (state: CameraServiceState) => void): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  private notify() {
    const currentState = this.getState();
    this.listeners.forEach((fn) => fn(currentState));
  }

  public getState(): CameraServiceState {
    return { ...this.state };
  }

  public async start(videoElement: HTMLVideoElement): Promise<void> {
    if (this.stream) {
      this.stop();
    }
    this.videoEl = videoElement;
    this.state.cameraStatus = 'initializing';
    this.state.errorMessage = null;
    this.state.statusMessage = 'Requesting camera permissions...';
    this.notify();

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('MediaDevices API not supported in this browser.');
      }

      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 480 },
          height: { ideal: 360 },
          facingMode: 'user'
        },
        audio: false
      });

      this.videoEl.srcObject = this.stream;
      await this.videoEl.play();

      this.state.cameraStatus = 'active';
      this.state.statusMessage = 'Camera active. Frame analysis running.';
      this.notify();

      this.startProcessingLoop();
    } catch (err: any) {
      this.stop();
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        this.state.cameraStatus = 'permission_denied';
        this.state.errorMessage = 'Camera permission was denied. Please allow camera access in browser settings.';
        this.state.statusMessage = 'Permission Denied.';
      } else if (
        err.name === 'NotFoundError' ||
        err.name === 'DevicesNotFoundError' ||
        err.name === 'NotReadableError' ||
        err.name === 'TrackStartError'
      ) {
        this.state.cameraStatus = 'hardware_error';
        this.state.errorMessage = 'Camera hardware error or device already in use by another app.';
        this.state.statusMessage = 'Hardware Error.';
      } else {
        this.state.cameraStatus = 'hardware_error';
        this.state.errorMessage = err.message || 'Unknown camera error.';
        this.state.statusMessage = 'Camera failed to start.';
      }
      this.notify();
    }
  }

  public stop(): void {
    this.stopProcessingLoop();
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.videoEl) {
      this.videoEl.srcObject = null;
    }
    this.state.cameraStatus = 'off';
    this.state.faceStatus = 'idle';
    this.state.faceCount = 0;
    this.state.primaryFace = null;
    this.state.allFaces = [];
    this.state.statusMessage = 'Camera is turned off.';
    this.notify();
  }

  public pauseDetection(): void {
    if (this.state.cameraStatus === 'active') {
      this.state.cameraStatus = 'paused';
      this.state.statusMessage = 'Detection paused. Preview still streaming.';
      this.notify();
    }
  }

  public resumeDetection(): void {
    if (this.state.cameraStatus === 'paused') {
      this.state.cameraStatus = 'active';
      this.state.statusMessage = 'Detection resumed.';
      this.notify();
    }
  }

  /**
   * Optimized sampling loop:
   * 1. Throttles frame captures to sampleIntervalMs (not every frame).
   * 2. Skips processing if document is hidden / tab switched.
   * 3. Drops frame if previous inference is still in-flight.
   * 4. Downsamples offscreen canvas to lightweight resolution.
   */
  private startProcessingLoop(): void {
    this.stopProcessingLoop();
    this.loopIntervalId = setInterval(async () => {
      if (this.state.cameraStatus !== 'active') return;
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;
      if (this.isProcessingFrame) return; // Drop frame to prevent queue buildup
      if (!this.videoEl || this.videoEl.readyState < 2) return;

      await this.processCurrentFrame();
    }, this.sampleIntervalMs);
  }

  private stopProcessingLoop(): void {
    if (this.loopIntervalId) {
      clearInterval(this.loopIntervalId);
      this.loopIntervalId = null;
    }
    this.isProcessingFrame = false;
  }

  private async processCurrentFrame(): Promise<void> {
    if (!this.videoEl || !this.canvas) return;

    this.isProcessingFrame = true;
    this.state.faceStatus = 'processing';
    this.notify();

    try {
      const vWidth = this.videoEl.videoWidth || 480;
      const vHeight = this.videoEl.videoHeight || 360;

      // Downsample for optimized transmission
      const targetWidth = 360;
      const targetHeight = Math.round((vHeight / vWidth) * targetWidth);

      this.canvas.width = targetWidth;
      this.canvas.height = targetHeight;
      const ctx = this.canvas.getContext('2d');
      if (!ctx) return;

      ctx.drawImage(this.videoEl, 0, 0, targetWidth, targetHeight);
      const b64 = this.canvas.toDataURL('image/jpeg', 0.65);

      let result: FaceDetectionResult;
      if (this.frameAnalyzer) {
        result = await this.frameAnalyzer(b64);
      } else {
        result = await api.detectFaces(b64);
        if (this.onFrameCaptured) {
          this.onFrameCaptured(b64, result);
        }
      }

      // Map scale back if needed
      const scaleX = vWidth / targetWidth;
      const scaleY = vHeight / targetHeight;

      const scaleBox = (b: BoundingBox): BoundingBox => ({
        x: Math.round(b.x * scaleX),
        y: Math.round(b.y * scaleY),
        width: Math.round(b.width * scaleX),
        height: Math.round(b.height * scaleY)
      });

      const scaledPrimary = result.primary_face ? scaleBox(result.primary_face) : null;
      const scaledAll = (result.all_faces || []).map(scaleBox);

      this.state.faceStatus = result.state as FaceStatus;
      this.state.faceCount = result.face_count;
      this.state.primaryFace = scaledPrimary;
      this.state.allFaces = scaledAll;
      this.state.confidence = result.confidence;
      this.state.inferenceTimeMs = result.inference_time_ms;
      this.state.statusMessage = result.status_message;
      this.state.errorMessage = result.error_message || null;
    } catch (err: any) {
      this.state.faceStatus = 'error';
      this.state.errorMessage = err.message || 'Detection request failed.';
      this.state.statusMessage = 'Detection communication error.';
    } finally {
      this.isProcessingFrame = false;
      this.notify();
    }
  }
}

export const cameraService = new CameraService(1200);
