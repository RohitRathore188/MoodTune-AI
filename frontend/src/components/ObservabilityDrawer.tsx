import React, { useState, useEffect } from 'react';
import { Activity, X, Gauge, Cpu, CheckCircle2 } from 'lucide-react';
import type { SystemHealthMetrics } from '../types';
import { api } from '../services/api';

interface ObservabilityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ObservabilityDrawer: React.FC<ObservabilityDrawerProps> = ({
  isOpen,
  onClose
}) => {
  const [metricsData, setMetricsData] = useState<{
    metrics: SystemHealthMetrics;
    recommendation_health_status: string;
    actionable_recommendations: string[];
  } | null>(null);

  useEffect(() => {
    if (isOpen) {
      api.getMetrics().then(setMetricsData).catch(console.error);
      const interval = setInterval(() => {
        api.getMetrics().then(setMetricsData).catch(console.error);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const m = metricsData?.metrics;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="glass-panel-active rounded-3xl max-w-xl w-full p-6 relative border border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white glass-panel-subtle hover:bg-white/10 transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-2xl bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">System Observability & Jev Traces</h3>
            <p className="text-xs text-slate-400">Live latency telemetry, agent contracts, and recommendation health</p>
          </div>
        </div>

        {/* Pipeline Architecture Principle */}
        <div className="p-3.5 rounded-2xl bg-purple-950/30 border border-purple-500/20 text-xs text-purple-200 mb-4">
          <div className="font-semibold text-white mb-1 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>Architecture Separation of Responsibilities</span>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-2 text-center text-[10px]">
            <div className="p-2 rounded-xl bg-white/5">
              <span className="font-bold text-cyan-300 block">LLM</span>
              <span className="text-slate-400">Creates & Reasons</span>
            </div>
            <div className="p-2 rounded-xl bg-purple-500/20 border border-purple-500/30">
              <span className="font-bold text-purple-300 block">Jev</span>
              <span className="text-slate-300">Decides & Bounds</span>
            </div>
            <div className="p-2 rounded-xl bg-white/5">
              <span className="font-bold text-emerald-300 block">Code</span>
              <span className="text-slate-400">Acts & Plays</span>
            </div>
          </div>
        </div>

        {/* Latency Telemetry */}
        <div className="my-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-purple-400" />
            <span>End-to-End Latency Breakdown</span>
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="p-3 rounded-2xl glass-panel-subtle">
              <div className="text-[10px] text-slate-400">CV Inference</div>
              <div className="text-sm font-bold text-white mt-1">
                {m?.latencies?.cv_inference_ms.toFixed(1) || '32.0'}ms
              </div>
            </div>
            <div className="p-3 rounded-2xl glass-panel-subtle">
              <div className="text-[10px] text-slate-400">Smoothing EMA</div>
              <div className="text-sm font-bold text-white mt-1">
                {m?.latencies?.temporal_smoothing_ms.toFixed(1) || '1.2'}ms
              </div>
            </div>
            <div className="p-3 rounded-2xl glass-panel-subtle border border-purple-500/30 bg-purple-500/10">
              <div className="text-[10px] text-purple-300">Jev System One</div>
              <div className="text-sm font-bold text-purple-200 mt-1">
                {m?.latencies?.jev_decision_ms.toFixed(1) || '45.0'}ms
              </div>
            </div>
            <div className="p-3 rounded-2xl glass-panel-subtle">
              <div className="text-[10px] text-slate-400">Rec Ranking</div>
              <div className="text-sm font-bold text-white mt-1">
                {m?.latencies?.recommendation_scoring_ms.toFixed(1) || '4.5'}ms
              </div>
            </div>
          </div>
        </div>

        {/* Operational Reliability & Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 my-4 text-xs">
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Total Frames</span>
            <span className="text-base font-bold text-white mt-0.5 block">{m?.total_frames_analyzed ?? 0}</span>
          </div>
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Faces Detected</span>
            <span className="text-base font-bold text-white mt-0.5 block">{m?.faces_detected_count ?? 0}</span>
          </div>
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Skip Rate</span>
            <span className="text-base font-bold text-emerald-400 mt-0.5 block">
              {Math.round((m?.skip_rate ?? 0) * 100)}%
            </span>
          </div>
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Jev Calls</span>
            <span className="text-base font-bold text-purple-300 mt-0.5 block">{m?.jev_calls_count ?? 0}</span>
          </div>
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Fallback Decisions</span>
            <span className="text-base font-bold text-slate-300 mt-0.5 block">{m?.fallback_decisions_count ?? 0}</span>
          </div>
          <div className="p-3 rounded-2xl glass-panel-subtle">
            <span className="text-slate-400 block text-[10px]">Music Provider</span>
            <span className="text-xs font-semibold text-white mt-1 block truncate">
              {m?.active_music_provider || 'Local Provider'}
            </span>
          </div>
        </div>

        {/* Health Evaluation Verdict */}
        <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between text-xs mt-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <div>
              <div className="font-semibold text-white">System Status: {metricsData?.recommendation_health_status || 'Optimal'}</div>
              <div className="text-[11px] text-slate-400">
                {metricsData?.actionable_recommendations.length
                  ? metricsData.actionable_recommendations.join(', ')
                  : 'All bounded agent contracts executing within SLAs.'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
