import React from 'react';
import { Zap, Smile, CloudSun, Compass, BookOpen, Moon, Flame } from 'lucide-react';
import type { MoodClass } from '../types';

interface ManualMoodSelectorProps {
  currentMood: MoodClass;
  onSelectMood: (mood: MoodClass) => void;
}

const MOODS: { id: MoodClass; label: string; desc: string; icon: any; color: string; border: string; bg: string }[] = [
  { id: 'energetic', label: 'Energetic', desc: 'High beat & drive', icon: Zap, color: 'text-amber-400', border: 'border-amber-500/30', bg: 'hover:bg-amber-500/15' },
  { id: 'positive', label: 'Positive', desc: 'Cheerful & uplifting', icon: Smile, color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'hover:bg-emerald-500/15' },
  { id: 'calm', label: 'Calm', desc: 'Peaceful & soothing', icon: CloudSun, color: 'text-cyan-400', border: 'border-cyan-500/30', bg: 'hover:bg-cyan-500/15' },
  { id: 'neutral', label: 'Neutral', desc: 'Balanced focus', icon: Compass, color: 'text-purple-400', border: 'border-purple-500/30', bg: 'hover:bg-purple-500/15' },
  { id: 'reflective', label: 'Reflective', desc: 'Introspective & deep', icon: BookOpen, color: 'text-indigo-400', border: 'border-indigo-500/30', bg: 'hover:bg-indigo-500/15' },
  { id: 'low_energy', label: 'Low Energy', desc: 'Gentle & resting', icon: Moon, color: 'text-slate-400', border: 'border-slate-500/30', bg: 'hover:bg-slate-500/15' },
  { id: 'tense', label: 'Tense', desc: 'Stress-relief audio', icon: Flame, color: 'text-rose-400', border: 'border-rose-500/30', bg: 'hover:bg-rose-500/15' },
];

export const ManualMoodSelector: React.FC<ManualMoodSelectorProps> = ({
  currentMood,
  onSelectMood
}) => {
  return (
    <div className="glass-panel rounded-3xl p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Manual Mood Selection (Fallback & Direct Override)
          </h2>
          <p className="text-[11px] text-slate-500">
            Available at all times or when webcam is offline.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 mt-2">
        {MOODS.map((m) => {
          const Icon = m.icon;
          const isSelected = currentMood === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onSelectMood(m.id)}
              className={`p-3 rounded-2xl flex flex-col items-center text-center transition-all duration-200 border ${
                isSelected
                  ? `${m.border} bg-white/10 shadow-lg scale-102 ring-1 ring-purple-500`
                  : `glass-panel-subtle ${m.bg}`
              }`}
            >
              <div className={`p-2 rounded-xl bg-white/5 mb-1.5 ${m.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <span className={`text-xs font-bold ${m.color}`}>
                {m.label}
              </span>
              <span className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">
                {m.desc}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
