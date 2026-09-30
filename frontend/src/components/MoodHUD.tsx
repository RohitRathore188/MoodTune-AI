import React from 'react';
import { Eye, Clock, Info, CheckCircle2, UserX, Sparkles } from 'lucide-react';
import type { MoodState, FaceDetectionResult, MoodClass } from '../types';

interface MoodHUDProps {
  moodState: MoodState | null;
  detectionResult?: FaceDetectionResult | null;
  isCameraActive?: boolean;
  isLoading?: boolean;
  dominantExpression?: string;
}

const MOOD_THEMES: Record<MoodClass, { label: string; color: string; border: string; bg: string }> = {
  energetic: { label: 'Energetic', color: 'text-amber-400', border: 'border-amber-500/40', bg: 'bg-amber-500/15' },
  positive: { label: 'Positive', color: 'text-emerald-400', border: 'border-emerald-500/40', bg: 'bg-emerald-500/15' },
  calm: { label: 'Calm', color: 'text-cyan-400', border: 'border-cyan-500/40', bg: 'bg-cyan-500/15' },
  neutral: { label: 'Neutral', color: 'text-purple-400', border: 'border-purple-500/40', bg: 'bg-purple-500/15' },
  reflective: { label: 'Reflective', color: 'text-indigo-400', border: 'border-indigo-500/40', bg: 'bg-indigo-500/15' },
  low_energy: { label: 'Low Energy', color: 'text-slate-400', border: 'border-slate-500/40', bg: 'bg-slate-500/15' },
  tense: { label: 'Tense', color: 'text-rose-400', border: 'border-rose-500/40', bg: 'bg-rose-500/15' },
};

export const MoodHUD: React.FC<MoodHUDProps> = ({ 
  moodState,
  detectionResult,
  isCameraActive = false,
  isLoading = false,
  dominantExpression
}) => {
  const currentMood = moodState?.estimated_mood || 'neutral';
  const theme = MOOD_THEMES[currentMood] || MOOD_THEMES.neutral;
  const confidence = moodState?.mood_confidence ?? 0.85;
  const isStable = moodState?.is_stable ?? true;
  const duration = moodState?.stable_duration_seconds || 0;

  const isNoFace = isCameraActive && detectionResult?.state === 'no_face';

  if (isLoading) {
    return (
      <div className="glass-panel rounded-3xl p-5 flex flex-col justify-between min-h-[300px]">
        <div className="flex items-center justify-between mb-4">
          <div className="h-4 w-32 rounded-lg skeleton-shimmer" />
          <div className="h-6 w-20 rounded-full skeleton-shimmer" />
        </div>
        <div className="grid grid-cols-2 gap-4 my-2">
          <div className="h-28 rounded-2xl skeleton-shimmer" />
          <div className="h-28 rounded-2xl skeleton-shimmer" />
        </div>
        <div className="h-14 rounded-2xl skeleton-shimmer mt-3" />
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-3xl p-5 flex flex-col justify-between h-full">
      {/* HUD Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-purple-400" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Visible Affect & Mood HUD
          </h2>
        </div>

        {/* Stable Duration Pill */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium glass-panel-subtle text-slate-300 border border-white/5">
          <Clock className="w-3.5 h-3.5 text-purple-300" />
          <span>Stable {duration.toFixed(1)}s</span>
        </div>
      </div>

      {/* Explicit No-Face Guidance Card */}
      {isNoFace && (
        <div className="mb-3 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex items-start gap-3 animate-in fade-in">
          <UserX className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-semibold text-amber-300">No face in camera frame:</span>
            <p className="text-amber-200/80 mt-0.5 leading-relaxed">
              Temporal hysteresis is holding your previous mood state safely. Music playback continues uninterrupted without abrupt thrashing.
            </p>
          </div>
        </div>
      )}

      {/* Main Mood Badge & Confidence Meter */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-2">
        {/* Estimated Mood */}
        <div className={`p-4 rounded-2xl border ${theme.border} ${theme.bg} backdrop-blur-md flex flex-col justify-center transition-all duration-500`}>
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
              Current Mood
            </span>
            {dominantExpression && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-slate-300 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5 text-purple-300" />
                {dominantExpression}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 mt-1.5">
            <span className={`text-2xl font-bold tracking-tight ${theme.color}`}>
              {theme.label}
            </span>
            {isStable && (
              <span title="Mood state stabilized">
                <CheckCircle2 className={`w-4 h-4 ${theme.color}`} />
              </span>
            )}
          </div>

          <span className="text-[10px] text-slate-400 mt-1">
            Controlled Vocabulary • Anti-Thrashing Guard
          </span>
        </div>

        {/* Mood Confidence Meter */}
        <div className="p-4 rounded-2xl glass-panel-subtle flex flex-col justify-center border border-white/5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
              Affect Confidence
            </span>
            <span className="text-sm font-bold font-mono text-white">
              {Math.round(confidence * 100)}%
            </span>
          </div>

          <div className="w-full bg-white/10 rounded-full h-2.5 mt-2.5 overflow-hidden p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                confidence >= 0.70 ? 'bg-gradient-to-r from-emerald-500 to-cyan-400' :
                confidence >= 0.40 ? 'bg-gradient-to-r from-amber-500 to-yellow-400' : 'bg-gradient-to-r from-rose-500 to-orange-400'
              }`}
              style={{ width: `${Math.round(confidence * 100)}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
            <span>
              {confidence >= 0.70 ? 'High Confidence (Direct Jev)' :
               confidence >= 0.40 ? 'Medium Confidence (Blended)' : 'Safe Fallback Mode'}
            </span>
            <span className="font-mono text-slate-500">Tier {confidence >= 0.70 ? 'A' : confidence >= 0.40 ? 'B' : 'C'}</span>
          </div>
        </div>
      </div>

      {/* Estimated Expression Probabilities Breakdown Mini Bars */}
      {moodState?.smoothed_emotion_probabilities && (
        <div className="mt-2 pt-3 border-t border-white/5">
          <div className="text-[11px] font-medium text-slate-300 mb-2 flex items-center justify-between">
            <span>Estimated Visible Facial Expression</span>
            <span className="text-[10px] text-purple-300 font-mono">Smoothed EMA</span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
            {Object.entries(moodState.smoothed_emotion_probabilities)
              .filter(([k]) => ['happy', 'neutral', 'sad', 'angry'].includes(k))
              .map(([emotion, prob]) => (
                <div key={emotion} className="p-2 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition">
                  <div className="text-slate-400 capitalize">{emotion === 'happy' ? 'Smiling' : emotion}</div>
                  <div className="font-bold text-slate-200 mt-0.5 font-mono">
                    {Math.round(Number(prob) * 100)}%
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Human-Centered Phrasing Notice */}
      <div className="mt-3 pt-3 border-t border-white/5 flex items-start gap-2 text-[11px] text-slate-400 leading-tight">
        <Info className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
        <span>
          Facial expression is an estimate of visible affect, never a claim of internal emotional truth.
        </span>
      </div>
    </div>
  );
};

