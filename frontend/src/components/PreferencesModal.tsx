import React, { useState, useEffect } from 'react';
import { Sliders, X, Check, Save } from 'lucide-react';
import type { UserPreferences } from '../types';
import { api } from '../services/api';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPreferencesUpdated: (prefs: UserPreferences) => void;
}

const ALL_GENRES = [
  { id: 'lofi', label: 'Bollywood Lofi & Acoustic' },
  { id: 'ambient', label: 'Sufi & Peaceful Ambient' },
  { id: 'synthwave', label: 'Bollywood Dance & Energetic' },
  { id: 'upbeat_pop', label: 'Bollywood Pop & Melodic' },
  { id: 'indie_folk', label: 'Hindi Indie & Soulful Folk' },
  { id: 'classical', label: 'Hindustani & Classical Fusion' },
  { id: 'meditation', label: 'Meditative & Spiritual Unwind' },
];

export const PreferencesModal: React.FC<PreferencesModalProps> = ({
  isOpen,
  onClose,
  onPreferencesUpdated
}) => {
  const [prefs, setPrefs] = useState<UserPreferences>({
    preferred_genres: ['lofi', 'ambient', 'synthwave'],
    disliked_genres: [],
    preferred_energy_bias: 0.5,
    transition_sensitivity: 0.6,
    auto_play_on_mood_shift: true
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.getPreferences().then(setPrefs).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleGenre = (genreId: string) => {
    setPrefs((prev) => {
      const exists = prev.preferred_genres.includes(genreId);
      const nextGenres = exists
        ? prev.preferred_genres.filter((g) => g !== genreId)
        : [...prev.preferred_genres, genreId];
      return { ...prev, preferred_genres: nextGenres };
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.updatePreferences(prefs);
      onPreferencesUpdated(updated);
      onClose();
    } catch (err) {
      console.error('Failed to update preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="glass-panel-active rounded-3xl max-w-lg w-full p-6 relative border border-white/10 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white glass-panel-subtle hover:bg-white/10 transition"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Personalization Engine</h3>
            <p className="text-xs text-slate-400">Tailor recommendation characteristics and transition gating</p>
          </div>
        </div>

        {/* Preferred Genres */}
        <div className="my-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
            Preferred Music Genres
          </label>
          <div className="flex flex-wrap gap-2">
            {ALL_GENRES.map((g) => {
              const active = prefs.preferred_genres.includes(g.id);
              return (
                <button
                  key={g.id}
                  onClick={() => toggleGenre(g.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition ${
                    active
                      ? 'bg-purple-600/30 border-purple-500 text-purple-200'
                      : 'glass-panel-subtle border-white/5 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {active && <Check className="w-3.5 h-3.5 text-purple-400" />}
                  <span>{g.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Energy Preference Bias */}
        <div className="my-4">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-slate-400">Preferred Energy Bias</span>
            <span className="font-mono text-purple-300">{Math.round(prefs.preferred_energy_bias * 100)}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={prefs.preferred_energy_bias}
            onChange={(e) => setPrefs({ ...prefs, preferred_energy_bias: parseFloat(e.target.value) })}
            className="w-full accent-purple-500 h-2 rounded-full bg-white/10 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Chill / Low Energy</span>
            <span>Balanced</span>
            <span>High Tempo</span>
          </div>
        </div>

        {/* Transition Sensitivity */}
        <div className="my-4">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold uppercase tracking-wider text-slate-400">Transition Sensitivity</span>
            <span className="font-mono text-indigo-300">{Math.round(prefs.transition_sensitivity * 100)}%</span>
          </div>
          <input
            type="range"
            min={0.2}
            max={1}
            step={0.05}
            value={prefs.transition_sensitivity}
            onChange={(e) => setPrefs({ ...prefs, transition_sensitivity: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 h-2 rounded-full bg-white/10 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Strict Anti-Thrashing (Holds Song)</span>
            <span>Rapid Adaptation</span>
          </div>
        </div>

        {/* Auto Transition Toggle */}
        <div className="p-3 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between my-4">
          <div>
            <div className="text-xs font-semibold text-white">Auto-Switch on Stable Shift</div>
            <div className="text-[11px] text-slate-400">Automatically switch tracks when a sustained mood shift is confirmed.</div>
          </div>
          <input
            type="checkbox"
            checked={prefs.auto_play_on_mood_shift}
            onChange={(e) => setPrefs({ ...prefs, auto_play_on_mood_shift: e.target.checked })}
            className="w-4 h-4 accent-purple-500 rounded cursor-pointer"
          />
        </div>

        {/* Save Controls */}
        <div className="pt-4 border-t border-white/10 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl glass-panel-subtle text-xs text-slate-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 flex items-center gap-1.5 transition"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Apply Preferences'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
