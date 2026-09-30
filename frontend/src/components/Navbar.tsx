import React from 'react';
import { Sparkles, Shield, Sliders, Activity, WifiOff, CameraOff, Pause, AlertTriangle } from 'lucide-react';
import type { CameraStatus } from '../services/cameraService';

interface NavbarProps {
  onOpenSettings: () => void;
  onOpenObservability: () => void;
  onOpenEvaluation?: () => void;
  cameraStatus: CameraStatus;
  isOffline?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenSettings,
  onOpenObservability,
  onOpenEvaluation,
  cameraStatus,
  isOffline = false
}) => {
  const renderCameraBadge = () => {
    switch (cameraStatus) {
      case 'active':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">Camera Active</span>
            <span className="sm:hidden">Active</span>
          </div>
        );
      case 'paused':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-xs font-medium">
            <Pause className="w-3 h-3 text-amber-300" />
            <span className="hidden sm:inline">Detection Paused</span>
            <span className="sm:hidden">Paused</span>
          </div>
        );
      case 'permission_denied':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30 text-xs font-medium">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            <span className="hidden sm:inline">Permission Denied</span>
            <span className="sm:hidden">Denied</span>
          </div>
        );
      case 'hardware_error':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30 text-xs font-medium">
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            <span className="hidden sm:inline">Hardware Error</span>
            <span className="sm:hidden">Error</span>
          </div>
        );
      case 'initializing':
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>Initializing...</span>
          </div>
        );
      case 'off':
      default:
        return (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-500/15 text-slate-400 border border-slate-500/30 text-xs font-medium">
            <CameraOff className="w-3 h-3 text-slate-400" />
            <span className="hidden sm:inline">Camera Off</span>
            <span className="sm:hidden">Off</span>
          </div>
        );
    }
  };

  return (
    <header className="w-full glass-panel border-b border-white/10 px-4 sm:px-6 py-3.5 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/25">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-purple-300 tracking-tight">
                MoodTune AI
              </h1>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 hidden xs:inline">
                System One
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Your mood. Your music.</p>
          </div>
        </div>

        {/* Center: Camera Status Badge & Offline Indicator */}
        <div className="flex items-center gap-2.5">
          {isOffline && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium animate-pulse">
              <WifiOff className="w-3.5 h-3.5" />
              <span>Offline Mode</span>
            </div>
          )}

          {renderCameraBadge()}

          {/* Ephemeral Privacy Guarantee Tag */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full glass-panel-subtle text-[11px] text-purple-300 border border-white/5">
            <Shield className="w-3 h-3 text-emerald-400" />
            <span>RAM Only</span>
          </div>
        </div>

        {/* Right Action Controls */}
        <div className="flex items-center gap-2">
          {onOpenEvaluation && (
            <button
              onClick={onOpenEvaluation}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-cyan-300 hover:text-white bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 transition active:scale-95 shadow-sm"
              title="Open Internal AI Evaluation Dashboard"
            >
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>AI Evaluation</span>
            </button>
          )}

          <button
            onClick={onOpenObservability}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white glass-panel-subtle hover:bg-white/10 transition active:scale-95"
            title="Observability Telemetry & Jev Traces"
          >
            <Activity className="w-4 h-4 text-purple-400" />
            <span className="hidden md:inline">Observability</span>
          </button>

          <button
            onClick={onOpenSettings}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 shadow-lg shadow-purple-500/15 transition active:scale-95"
            title="Open System Settings"
          >
            <Sliders className="w-4 h-4 text-purple-300" />
            <span>Settings</span>
          </button>
        </div>
      </div>
    </header>
  );
};

