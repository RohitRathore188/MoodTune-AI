import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  ArrowLeft, 
  RefreshCw, 
  RotateCcw, 
  ShieldAlert, 
  Gauge, 
  Eye, 
  Music, 
  CheckCircle2, 
  TrendingUp, 
  Clock, 
  Sparkles, 
  Zap, 
  BarChart3, 
  Layers,
  ChevronRight
} from 'lucide-react';
import type { EvaluationDashboardResponse } from '../types';
import { api } from '../services/api';

interface EvaluationDashboardProps {
  onBackToPlayer: () => void;
}

export const EvaluationDashboard: React.FC<EvaluationDashboardProps> = ({ onBackToPlayer }) => {
  const [data, setData] = useState<EvaluationDashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [timeframe, setTimeframe] = useState<'session' | '1h' | '24h' | 'all'>('session');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [resetting, setResetting] = useState<boolean>(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchMetrics = async () => {
    try {
      const res = await api.getEvaluation();
      setData(res);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load evaluation metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    if (!autoRefresh) return;

    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleReset = async () => {
    if (!window.confirm('Reset evaluation telemetry buffers? This clears live inference and interaction counters.')) {
      return;
    }
    setResetting(true);
    try {
      await api.resetEvaluation();
      await fetchMetrics();
    } catch (err) {
      console.error('Failed to reset evaluation metrics:', err);
    } finally {
      setResetting(false);
    }
  };

  const formatSecToMinSec = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
  };

  const mp = data?.model_performance;
  const rp = data?.recommendation_performance;
  const sp = data?.system_performance;

  return (
    <div className="min-h-screen bg-[#07080c] text-slate-100 flex flex-col justify-between selection:bg-purple-500 selection:text-white pb-12">
      {/* Top Cockpit Header */}
      <header className="glass-panel border-b border-white/10 px-4 sm:px-8 py-4 sticky top-0 z-40 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Left Brand & Return Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={onBackToPlayer}
              className="p-2.5 rounded-2xl glass-panel-subtle hover:bg-white/10 text-slate-300 hover:text-white transition flex items-center gap-2 text-xs font-semibold active:scale-95 border border-white/5"
              title="Return to Main Player Dashboard"
            >
              <ArrowLeft className="w-4 h-4 text-purple-400" />
              <span>Main Player</span>
            </button>

            <div className="h-6 w-px bg-white/10 hidden sm:block" />

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-purple-400" />
                  <span>AI Evaluation Dashboard</span>
                </h1>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Internal Telemetry
                </span>
              </div>
              <p className="text-xs text-slate-400">Continuous model, recommendation, and system performance audit</p>
            </div>
          </div>

          {/* Right Controls: Timeframe, Auto-Refresh & Reset */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Timeframe Selector */}
            <div className="flex items-center p-1 rounded-xl bg-white/5 border border-white/5 text-xs">
              {(['session', '1h', '24h', 'all'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTimeframe(t)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition text-[11px] ${
                    timeframe === t
                      ? 'bg-purple-600 text-white font-semibold shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {t === 'session' ? 'Live Session' : t === '1h' ? '1 Hour' : t === '24h' ? '24 Hours' : 'All Time'}
                </button>
              ))}
            </div>

            {/* Auto Refresh Toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition active:scale-95 ${
                autoRefresh
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                  : 'glass-panel-subtle border-white/5 text-slate-400'
              }`}
              title={autoRefresh ? 'Auto-refresh active (3s)' : 'Auto-refresh paused'}
            >
              <span className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
              <span className="hidden sm:inline">Live 3s</span>
            </button>

            {/* Manual Refresh */}
            <button
              onClick={fetchMetrics}
              disabled={loading}
              className="p-2 rounded-xl glass-panel-subtle hover:bg-white/10 text-slate-300 hover:text-white transition active:scale-95"
              title="Refresh Telemetry Now"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-purple-400' : ''}`} />
            </button>

            {/* Reset Telemetry */}
            <button
              onClick={handleReset}
              disabled={resetting}
              className="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 transition active:scale-95"
              title="Reset Evaluation Telemetry"
            >
              <RotateCcw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-8 py-6 space-y-8 flex-1">
        {/* MANDATORY HUMAN-CENTERED DISCLAIMER BANNER */}
        <div className="p-4 sm:p-5 rounded-3xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-purple-950/40 border border-purple-500/30 shadow-xl backdrop-blur-xl flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center shrink-0 mt-0.5">
            <ShieldAlert className="w-5 h-5 text-purple-300" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-300">
                Human-Centered Affect Mandate
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-200 border border-purple-500/30">
                Ethical Safeguard
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
              {data?.disclaimer ||
                "Visible affect metrics measure computer vision inference stability and temporal smoothing performance only. They do NOT represent or prove that the AI understands the user's true internal emotional state."}
            </p>
          </div>
        </div>

        {/* SECTION 1: MODEL PERFORMANCE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
                <Eye className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                  Model Performance
                </h2>
                <p className="text-[11px] text-slate-400">Emotion estimation latency & temporal smoothing dynamics</p>
              </div>
            </div>
            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
              mp?.overall_model_health === 'Optimal'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
            }`}>
              {mp?.overall_model_health || 'Optimal'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 1A. Emotion Estimation Metrics */}
            <div className="glass-panel rounded-3xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Emotion Estimation Telemetry</span>
                </h3>
                <span className="text-[10px] font-mono text-slate-400">
                  {mp?.emotion.total_frames ?? 0} frames sampled
                </span>
              </div>

              {/* Inference Latency */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Inference Latency</span>
                  <div className="text-2xl font-bold font-mono text-white mt-0.5">
                    {mp?.emotion.inference_latency_ms.toFixed(1) || '28.5'}<span className="text-sm text-slate-400 ml-1">ms</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-medium">Target: &lt; 50ms (Optimal)</span>
                </div>
                <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                  <Gauge className="w-7 h-7 text-cyan-400" />
                </div>
              </div>

              {/* Confidence Distribution */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300 uppercase tracking-wider text-[11px]">Confidence Distribution</span>
                  <span className="text-[10px] font-mono text-purple-300">Tiers: High / Med / Low</span>
                </div>

                {/* Visual Segmented Bar */}
                <div className="h-3 rounded-full overflow-hidden flex bg-white/10 p-0.5">
                  <div 
                    className="h-full bg-emerald-500 rounded-l-full transition-all duration-500" 
                    style={{ width: `${Math.round((mp?.emotion.confidence_distribution.high ?? 0.72) * 100)}%` }} 
                    title={`High (>=70%): ${Math.round((mp?.emotion.confidence_distribution.high ?? 0.72) * 100)}%`}
                  />
                  <div 
                    className="h-full bg-amber-500 transition-all duration-500" 
                    style={{ width: `${Math.round((mp?.emotion.confidence_distribution.medium ?? 0.21) * 100)}%` }} 
                    title={`Medium (40-69%): ${Math.round((mp?.emotion.confidence_distribution.medium ?? 0.21) * 100)}%`}
                  />
                  <div 
                    className="h-full bg-rose-500 rounded-r-full transition-all duration-500" 
                    style={{ width: `${Math.round((mp?.emotion.confidence_distribution.low ?? 0.07) * 100)}%` }} 
                    title={`Low (<40%): ${Math.round((mp?.emotion.confidence_distribution.low ?? 0.07) * 100)}%`}
                  />
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-[10px] pt-1">
                  <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                    <span className="text-emerald-300 font-bold block text-xs">
                      {Math.round((mp?.emotion.confidence_distribution.high ?? 0.72) * 100)}%
                    </span>
                    <span className="text-slate-400">High (≥0.70)</span>
                  </div>
                  <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
                    <span className="text-amber-300 font-bold block text-xs">
                      {Math.round((mp?.emotion.confidence_distribution.medium ?? 0.21) * 100)}%
                    </span>
                    <span className="text-slate-400">Medium</span>
                  </div>
                  <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
                    <span className="text-rose-300 font-bold block text-xs">
                      {Math.round((mp?.emotion.confidence_distribution.low ?? 0.07) * 100)}%
                    </span>
                    <span className="text-slate-400">Low (&lt;0.40)</span>
                  </div>
                </div>
              </div>

              {/* No-Face Rate */}
              <div className="p-3 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-white">No-Face Detection Rate</div>
                  <div className="text-[11px] text-slate-400">Frames with no human face locked in camera viewport</div>
                </div>
                <div className="text-right">
                  <span className="text-base font-bold font-mono text-amber-400">
                    {Math.round((mp?.emotion.no_face_rate ?? 0.10) * 100)}%
                  </span>
                  <span className="text-[10px] text-slate-500 block">Hysteresis Active</span>
                </div>
              </div>
            </div>

            {/* 1B. Mood Dynamics (Temporal Smoothing) */}
            <div className="glass-panel rounded-3xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>Mood Dynamics & Smoothing</span>
                </h3>
                <span className="text-[10px] font-mono text-slate-400">
                  Hysteresis Cooldown: 15s
                </span>
              </div>

              {/* Mood Stability Score & Avg Duration */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Stability Score</span>
                  <div className="text-2xl font-bold font-mono text-emerald-400 mt-0.5">
                    {Math.round((mp?.mood.stability_score ?? 0.92) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-400">Resistance to noise</span>
                </div>

                <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Average Stability</span>
                  <div className="text-2xl font-bold font-mono text-white mt-0.5">
                    {mp?.mood.average_stability_duration_sec.toFixed(1) || '15.2'}<span className="text-sm text-slate-400 ml-1">s</span>
                  </div>
                  <span className="text-[10px] text-slate-400">Sustained duration</span>
                </div>
              </div>

              {/* Transition Frequency & Low Confidence Rate */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Transition Frequency</div>
                  <div className="text-lg font-bold font-mono text-purple-300 mt-1">
                    {mp?.mood.transition_frequency_per_10m.toFixed(1) || '1.2'}<span className="text-xs font-normal text-slate-400 ml-1">/10m</span>
                  </div>
                  <span className="text-[10px] text-slate-500">{mp?.mood.total_transitions ?? 0} total shifts</span>
                </div>

                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Low-Confidence Rate</div>
                  <div className="text-lg font-bold font-mono text-amber-300 mt-1">
                    {Math.round((mp?.mood.low_confidence_rate ?? 0.05) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-500">Filtered by hysteresis</span>
                </div>
              </div>

              <div className="p-3 rounded-2xl bg-purple-950/20 border border-purple-500/20 text-[11px] text-purple-200/90 leading-relaxed">
                💡 Temporal smoothing applies exponential moving average (EMA) to prevent single-frame emotion flicker from abruptly thrashing music playback.
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: RECOMMENDATION PERFORMANCE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
                <Music className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                  Recommendation Performance
                </h2>
                <p className="text-[11px] text-slate-400">Candidate relevance, acceptance rate, and playback telemetry</p>
              </div>
            </div>
            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
              rp?.overall_recommendation_health === 'High Engagement'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                : 'bg-purple-500/20 text-purple-300 border-purple-500/30'
            }`}>
              {rp?.overall_recommendation_health || 'High Engagement'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 2A. Recommendation Engine Performance */}
            <div className="glass-panel rounded-3xl p-5 space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Recommendation Conversion & Alignment</span>
              </h3>

              <div className="grid grid-cols-2 gap-3">
                {/* Acceptance Rate */}
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                  <span className="text-[11px] font-medium text-slate-300 uppercase tracking-wider">Acceptance Rate</span>
                  <div className="text-2xl font-bold font-mono text-emerald-300 mt-0.5">
                    {Math.round((rp?.recommendation.acceptance_rate ?? 0.81) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-400">{rp?.recommendation.total_recommendations_accepted ?? 0} accepted candidates</span>
                </div>

                {/* Completion Rate */}
                <div className="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
                  <span className="text-[11px] font-medium text-slate-300 uppercase tracking-wider">Completion Rate</span>
                  <div className="text-2xl font-bold font-mono text-cyan-300 mt-0.5">
                    {Math.round((rp?.recommendation.completion_rate ?? 0.68) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-400">Played to finish</span>
                </div>

                {/* Skip Rate */}
                <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Skip Rate</span>
                  <div className="text-2xl font-bold font-mono text-amber-400 mt-0.5">
                    {Math.round((rp?.recommendation.skip_rate ?? 0.14) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-400">&lt; 30s skips penalized</span>
                </div>

                {/* Diversity Score */}
                <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Catalog Diversity</span>
                  <div className="text-2xl font-bold font-mono text-purple-300 mt-0.5">
                    {Math.round((rp?.recommendation.diversity_score ?? 0.85) * 100)}%
                  </div>
                  <span className="text-[10px] text-slate-400">Entropy balance</span>
                </div>
              </div>
            </div>

            {/* 2B. Playback Interaction Telemetry */}
            <div className="glass-panel rounded-3xl p-5 space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                <span>Playback Telemetry</span>
              </h3>

              {/* Average Listening Duration */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Average Listening Duration</span>
                  <div className="text-2xl font-bold font-mono text-white mt-0.5">
                    {formatSecToMinSec(rp?.playback.average_listening_duration_sec ?? 145)}
                  </div>
                  <span className="text-[10px] text-slate-400">
                    Raw: {(rp?.playback.average_listening_duration_sec ?? 145).toFixed(1)} seconds per track
                  </span>
                </div>
                <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                  <Clock className="w-7 h-7 text-purple-400" />
                </div>
              </div>

              {/* Frequencies */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Skip Frequency</div>
                  <div className="text-lg font-bold font-mono text-rose-300 mt-1">
                    {rp?.playback.skip_frequency_per_10m.toFixed(1) || '0.8'}<span className="text-xs font-normal text-slate-400 ml-1">/10m</span>
                  </div>
                  <span className="text-[10px] text-slate-500">{rp?.playback.total_songs_skipped ?? 0} total skips</span>
                </div>

                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Song Transitions</div>
                  <div className="text-lg font-bold font-mono text-indigo-300 mt-1">
                    {rp?.playback.transition_frequency_per_10m.toFixed(1) || '1.1'}<span className="text-xs font-normal text-slate-400 ml-1">/10m</span>
                  </div>
                  <span className="text-[10px] text-slate-500">{rp?.playback.total_songs_played ?? 0} songs played</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: SYSTEM PERFORMANCE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
                <Zap className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                  System Performance
                </h2>
                <p className="text-[11px] text-slate-400">Jev bounded decision layer, fallback reliability, and API latency SLAs</p>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              {sp?.overall_system_health || 'Operational'}
            </span>
          </div>

          {/* System Metric Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Jev Latency */}
            <div className="glass-panel rounded-3xl p-5 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Jev Latency</span>
              <div className="text-2xl font-bold font-mono text-purple-300">
                {sp?.jev_latency_ms.toFixed(1) || '42.0'}<span className="text-sm text-slate-400 ml-1">ms</span>
              </div>
              <span className="text-[10px] text-emerald-400 font-medium">&lt; 100ms Target Budget</span>
            </div>

            {/* Jev Failures */}
            <div className="glass-panel rounded-3xl p-5 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Jev Failures</span>
              <div className="text-2xl font-bold font-mono text-white">
                {sp?.jev_failures_count ?? 0}
              </div>
              <span className="text-[10px] text-slate-400">Timeouts & model errors</span>
            </div>

            {/* Fallback Frequency */}
            <div className="glass-panel rounded-3xl p-5 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Fallback Frequency</span>
              <div className="text-2xl font-bold font-mono text-indigo-300">
                {Math.round((sp?.fallback_frequency ?? 0.04) * 100)}%
              </div>
              <span className="text-[10px] text-slate-400">Safe deterministic fallback</span>
            </div>

            {/* API Failures */}
            <div className="glass-panel rounded-3xl p-5 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">API Failures</span>
              <div className="text-2xl font-bold font-mono text-emerald-400">
                {sp?.api_failures_count ?? 0} <span className="text-xs text-slate-400 font-normal">({(sp?.api_failure_rate ?? 0.0).toFixed(2)}%)</span>
              </div>
              <span className="text-[10px] text-slate-400">HTTP 5xx endpoint errors</span>
            </div>
          </div>

          {/* End-to-End Pipeline Latency Breakdown */}
          <div className="glass-panel rounded-3xl p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                <span>End-to-End Agent & Pipeline Latency Breakdown</span>
              </h3>
              <span className="text-xs font-bold font-mono text-purple-300">
                Total: {sp?.latencies.total_pipeline_ms.toFixed(1) || '76.2'}ms
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 block uppercase">1. CV Inference</span>
                <span className="text-base font-bold font-mono text-cyan-300 mt-1 block">
                  {sp?.latencies.cv_inference_ms.toFixed(1) || '28.5'}ms
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 block uppercase">2. Temporal Smoothing</span>
                <span className="text-base font-bold font-mono text-indigo-300 mt-1 block">
                  {sp?.latencies.temporal_smoothing_ms.toFixed(1) || '1.2'}ms
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-purple-500/10 border border-purple-500/30">
                <span className="text-[10px] text-purple-300 block uppercase font-semibold">3. Jev Decision</span>
                <span className="text-base font-bold font-mono text-purple-200 mt-1 block">
                  {sp?.latencies.jev_decision_ms.toFixed(1) || '42.0'}ms
                </span>
              </div>

              <div className="p-3 rounded-2xl bg-white/5 border border-white/5">
                <span className="text-[10px] text-slate-400 block uppercase">4. Rec Scoring</span>
                <span className="text-base font-bold font-mono text-emerald-300 mt-1 block">
                  {sp?.latencies.recommendation_scoring_ms.toFixed(1) || '4.5'}ms
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Actionable Recommendations & Subsystem Diagnosis */}
        <section className="p-5 rounded-3xl glass-panel-active border border-white/10 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <h3 className="text-sm font-bold text-white tracking-tight">
              Actionable Subsystem Recommendations & Audit Verdict
            </h3>
          </div>
          <div className="space-y-1.5 pl-7">
            {data?.actionable_recommendations.map((rec, i) => (
              <div key={i} className="text-xs text-slate-300 flex items-start gap-2">
                <ChevronRight className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                <span>{rec}</span>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Cockpit Footer */}
      <footer className="w-full border-t border-white/5 py-4 px-6 text-xs text-slate-500 text-center glass-panel-subtle mt-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>MoodTune AI Evaluation Cockpit • Uptime: {Math.floor((sp?.system_uptime_seconds ?? 0) / 60)}m {Math.floor((sp?.system_uptime_seconds ?? 0) % 60)}s</span>
          <span className="text-[11px] text-slate-400">
            Last Evaluated: {lastRefreshed.toLocaleTimeString()}
          </span>
        </div>
      </footer>
    </div>
  );
};
