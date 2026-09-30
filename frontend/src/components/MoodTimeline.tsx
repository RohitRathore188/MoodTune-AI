import React from 'react';
import { History, TrendingUp, Clock, Hourglass } from 'lucide-react';

interface MoodTimelineProps {
  history: Array<{
    timestamp: number;
    mood: string;
    confidence: number;
    dominant_emotion: string;
  }>;
  sessionDurationSeconds?: number;
}

const MOOD_COLOR_MAP: Record<string, string> = {
  energetic: '#f59e0b',
  positive: '#10b981',
  calm: '#06b6d4',
  neutral: '#8b5cf6',
  reflective: '#6366f1',
  low_energy: '#64748b',
  tense: '#f43f5e',
};

export const MoodTimeline: React.FC<MoodTimelineProps> = ({ 
  history,
  sessionDurationSeconds = 0 
}) => {
  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = Math.floor(totalSeconds % 60);
    return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="glass-panel rounded-3xl p-5">
      {/* Header with Title and Session Duration */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-purple-400" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Affect Progression & Mood Timeline
          </h2>
        </div>

        {/* Live Session Duration & Hysteresis Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium glass-panel-subtle text-slate-300 border border-white/5">
            <Clock className="w-3.5 h-3.5 text-purple-300" />
            <span>Session: <strong className="font-mono text-white">{formatDuration(sessionDurationSeconds)}</strong></span>
          </div>

          <div className="hidden sm:flex items-center gap-1 text-[11px] text-slate-400">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            <span>Hysteresis Active</span>
          </div>
        </div>
      </div>

      {history.length === 0 ? (
        /* Empty State */
        <div className="py-8 px-4 rounded-2xl bg-white/5 border border-white/5 text-center flex flex-col items-center justify-center">
          <Hourglass className="w-8 h-8 text-purple-400/40 mb-2 animate-pulse" />
          <p className="text-xs font-medium text-slate-300">Timeline Initializing</p>
          <p className="text-[11px] text-slate-500 max-w-sm mt-1">
            Affect observations will populate continuously as facial expressions are estimated and stabilized.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Continuous Colored Mood Bar */}
          <div className="w-full h-4 rounded-full bg-white/5 flex overflow-hidden p-0.5 border border-white/5">
            {history.slice(-30).map((entry, idx) => (
              <div
                key={idx}
                className="h-full flex-1 transition-all duration-300 hover:opacity-100 hover:scale-y-125"
                style={{
                  backgroundColor: MOOD_COLOR_MAP[entry.mood] || '#8b5cf6',
                  opacity: Math.max(0.4, entry.confidence)
                }}
                title={`${entry.mood.toUpperCase()} • Confidence: ${Math.round(entry.confidence * 100)}%`}
              />
            ))}
          </div>

          {/* Recent Mood Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-[11px]">
            {history.slice(-8).reverse().map((entry, idx) => (
              <div
                key={idx}
                className="px-3 py-1.5 rounded-xl glass-panel-subtle shrink-0 flex items-center gap-2 border border-white/5 hover:border-white/20 transition"
              >
                <span
                  className="w-2 h-2 rounded-full shadow-sm"
                  style={{ backgroundColor: MOOD_COLOR_MAP[entry.mood] || '#8b5cf6' }}
                />
                <span className="capitalize font-semibold text-slate-200">
                  {entry.mood.replace('_', ' ')}
                </span>
                <span className="text-[10px] font-mono text-purple-300 font-medium">
                  {Math.round(entry.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

