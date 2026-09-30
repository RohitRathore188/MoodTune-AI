import React, { useRef, useEffect, useState } from 'react';
import { 
  Camera, 
  CameraOff, 
  Play, 
  Pause, 
  ShieldCheck, 
  AlertTriangle, 
  Users, 
  UserCheck, 
  Loader2, 
  AlertCircle 
} from 'lucide-react';
import { cameraService } from '../services/cameraService';
import type { 
  CameraServiceState, 
  CameraStatus, 
  FaceStatus 
} from '../services/cameraService';

export const CameraFeed: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [serviceState, setServiceState] = useState<CameraServiceState>(cameraService.getState());

  useEffect(() => {
    const unsubscribe = cameraService.subscribe((newState) => {
      setServiceState(newState);
    });
    return () => unsubscribe();
  }, []);

  const handleToggleCamera = async () => {
    if (serviceState.cameraStatus === 'off' || serviceState.cameraStatus === 'permission_denied' || serviceState.cameraStatus === 'hardware_error') {
      if (videoRef.current) {
        await cameraService.start(videoRef.current);
      }
    } else {
      cameraService.stop();
    }
  };

  const handleTogglePause = () => {
    if (serviceState.cameraStatus === 'active') {
      cameraService.pauseDetection();
    } else if (serviceState.cameraStatus === 'paused') {
      cameraService.resumeDetection();
    }
  };

  // Status badges config
  const renderCameraStatusBadge = (status: CameraStatus) => {
    switch (status) {
      case 'active':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Camera Active
          </span>
        );
      case 'paused':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
            <Pause className="w-3 h-3 text-amber-300" />
            Detection Paused
          </span>
        );
      case 'initializing':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5">
            <Loader2 className="w-3 h-3 animate-spin text-cyan-300" />
            Initializing...
          </span>
        );
      case 'permission_denied':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1.5">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            Permission Denied
          </span>
        );
      case 'hardware_error':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1.5">
            <AlertCircle className="w-3 h-3 text-rose-400" />
            Hardware Error
          </span>
        );
      case 'off':
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30 flex items-center gap-1.5">
            <CameraOff className="w-3 h-3 text-slate-400" />
            Camera Off
          </span>
        );
    }
  };

  const renderFaceStatusBadge = (faceStatus: FaceStatus) => {
    switch (faceStatus) {
      case 'single_face':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
            Face Detected (1)
          </span>
        );
      case 'multiple_faces':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
            <Users className="w-3.5 h-3.5 text-purple-300" />
            Multiple Faces ({serviceState.faceCount})
          </span>
        );
      case 'no_face':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            No Face Detected
          </span>
        );
      case 'processing':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center gap-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
            Processing...
          </span>
        );
      case 'error':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            Error
          </span>
        );
      case 'idle':
      default:
        return null;
    }
  };

  const isStreaming = serviceState.cameraStatus === 'active' || serviceState.cameraStatus === 'paused';

  return (
    <div className="glass-panel rounded-3xl p-5 relative overflow-hidden flex flex-col justify-between">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-3 z-10">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-200 uppercase flex items-center gap-2">
            <span>Vision Sensor Pipeline</span>
            {renderFaceStatusBadge(serviceState.faceStatus)}
          </h2>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {serviceState.statusMessage}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Pause / Resume Button */}
          <button
            onClick={handleTogglePause}
            disabled={!isStreaming}
            className={`p-2 rounded-xl text-xs flex items-center gap-1.5 transition ${
              !isStreaming
                ? 'opacity-40 cursor-not-allowed glass-panel-subtle text-slate-500'
                : serviceState.cameraStatus === 'active'
                ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30'
            }`}
            title={serviceState.cameraStatus === 'active' ? 'Pause Detection Loop' : 'Resume Detection'}
          >
            {serviceState.cameraStatus === 'active' ? (
              <>
                <Pause className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Resume</span>
              </>
            )}
          </button>

          {/* Camera ON / OFF Button */}
          <button
            onClick={handleToggleCamera}
            className={`p-2 rounded-xl text-xs flex items-center gap-1.5 transition ${
              isStreaming
                ? 'bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/30'
                : 'bg-purple-600 hover:bg-purple-500 text-white font-medium shadow-lg shadow-purple-500/25'
            }`}
            title={isStreaming ? 'Turn Camera Off' : 'Turn Camera On'}
          >
            {isStreaming ? (
              <>
                <CameraOff className="w-3.5 h-3.5" />
                <span>Turn Off</span>
              </>
            ) : (
              <>
                <Camera className="w-3.5 h-3.5" />
                <span>Start Camera</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Video Viewport Area */}
      <div className="relative w-full aspect-[4/3] rounded-2xl bg-black/60 overflow-hidden flex items-center justify-center border border-white/5 my-2">
        {/* Hidden video element kept mounted for stream attachment */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-full object-cover transform -scale-x-100 ${
            isStreaming ? 'block' : 'hidden'
          }`}
        />

        {/* Primary Face Bounding Box */}
        {isStreaming && serviceState.primaryFace && (
          <div
            className="absolute border-2 border-purple-400/90 rounded-xl shadow-[0_0_20px_rgba(168,85,247,0.5)] pointer-events-none transition-all duration-200"
            style={{
              top: `${Math.min(80, (serviceState.primaryFace.y / 360) * 100)}%`,
              right: `${Math.min(80, (serviceState.primaryFace.x / 480) * 100)}%`, // mirrored
              width: `${Math.max(15, (serviceState.primaryFace.width / 480) * 100)}%`,
              height: `${Math.max(15, (serviceState.primaryFace.height / 360) * 100)}%`
            }}
          >
            <div className="absolute -top-6 left-0 px-2 py-0.5 bg-purple-600 text-white rounded text-[10px] font-mono tracking-wider font-semibold">
              Primary Face ({Math.round(serviceState.confidence * 100)}%)
            </div>
          </div>
        )}

        {/* Secondary Faces Bounding Boxes (for multiple faces state) */}
        {isStreaming && serviceState.faceCount > 1 && serviceState.allFaces.map((box, i) => {
          if (serviceState.primaryFace && box.x === serviceState.primaryFace.x && box.y === serviceState.primaryFace.y) {
            return null; // already drawn as primary
          }
          return (
            <div
              key={i}
              className="absolute border-2 border-dashed border-slate-400/70 rounded-xl pointer-events-none transition-all duration-200"
              style={{
                top: `${Math.min(80, (box.y / 360) * 100)}%`,
                right: `${Math.min(80, (box.x / 480) * 100)}%`,
                width: `${Math.max(15, (box.width / 480) * 100)}%`,
                height: `${Math.max(15, (box.height / 360) * 100)}%`
              }}
            >
              <div className="absolute -top-5 left-0 px-1.5 py-0.5 bg-slate-700/80 text-slate-300 rounded text-[9px] font-mono">
                Face #{i + 1}
              </div>
            </div>
          );
        })}

        {/* Initializing State Spinner */}
        {serviceState.cameraStatus === 'initializing' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 z-20">
            <Loader2 className="w-10 h-10 text-purple-400 animate-spin mb-3" />
            <span className="text-xs font-semibold text-slate-200">Accessing Camera Stream...</span>
            <span className="text-[11px] text-slate-400 mt-1">Please approve browser permission prompt</span>
          </div>
        )}

        {/* Fallback States (Off, Denied, Error) */}
        {!isStreaming && serviceState.cameraStatus !== 'initializing' && (
          <div className="text-center p-6 text-slate-400 flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center border border-white/5">
              {serviceState.cameraStatus === 'permission_denied' ? (
                <AlertTriangle className="w-7 h-7 text-rose-400" />
              ) : serviceState.cameraStatus === 'hardware_error' ? (
                <AlertCircle className="w-7 h-7 text-rose-400" />
              ) : (
                <CameraOff className="w-7 h-7 text-slate-500" />
              )}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">
                {serviceState.cameraStatus === 'permission_denied'
                  ? 'Camera Permission Blocked'
                  : serviceState.cameraStatus === 'hardware_error'
                  ? 'Camera Hardware Error'
                  : 'Camera Inactive'}
              </p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
                {serviceState.errorMessage ||
                  'Enable camera to activate real-time facial affect estimation, or select any mood manually below.'}
              </p>
            </div>

            {serviceState.cameraStatus !== 'off' && (
              <button
                onClick={handleToggleCamera}
                className="mt-2 px-4 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition active:scale-95"
              >
                Retry Camera
              </button>
            )}
          </div>
        )}

        {/* Live Status Overlay in bottom corner */}
        {isStreaming && (
          <div className="absolute bottom-2 left-2 px-2.5 py-1 rounded-xl bg-black/70 backdrop-blur-md text-[10px] font-mono text-purple-200 border border-white/10 flex items-center gap-2">
            <span>Infer: {serviceState.inferenceTimeMs.toFixed(0)}ms</span>
            <span>•</span>
            <span>{serviceState.faceCount} face(s)</span>
          </div>
        )}
      </div>

      {/* Footer: Camera Status Pill & Privacy Guarantee */}
      <div className="mt-2 pt-3 border-t border-white/5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {renderCameraStatusBadge(serviceState.cameraStatus)}
        </div>
        <div className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>RAM In-Memory Only</span>
        </div>
      </div>
    </div>
  );
};
