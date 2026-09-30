import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  X, 
  Check, 
  Save, 
  Camera, 
  CameraOff, 
  ShieldCheck, 
  Trash2, 
  CheckCircle2, 
  Lock, 
  SlidersHorizontal, 
  AlertTriangle 
} from 'lucide-react';
import type { UserPreferences } from '../types';
import { api } from '../services/api';
import { cameraService } from '../services/cameraService';
import type { CameraServiceState } from '../services/cameraService';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPreferencesUpdated: (prefs: UserPreferences) => void;
  onHistoryCleared: () => void;
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

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onPreferencesUpdated,
  onHistoryCleared
}) => {
  const [activeTab, setActiveTab] = useState<'playback' | 'camera' | 'privacy'>('playback');
  const [prefs, setPrefs] = useState<UserPreferences>({
    preferred_genres: ['lofi', 'ambient', 'synthwave'],
    disliked_genres: [],
    preferred_energy_bias: 0.5,
    transition_sensitivity: 0.6,
    auto_play_on_mood_shift: true
  });
  const [cameraState, setCameraState] = useState<CameraServiceState>(cameraService.getState());
  const [saving, setSaving] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearedNotice, setClearedNotice] = useState(false);

  useEffect(() => {
    return cameraService.subscribe(setCameraState);
  }, []);

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

  const handleClearHistory = async () => {
    setClearing(true);
    try {
      await api.clearHistory();
      setClearedNotice(true);
      onHistoryCleared();
      setTimeout(() => setClearedNotice(false), 3500);
    } catch (err) {
      console.error('Failed to clear history:', err);
    } finally {
      setClearing(false);
    }
  };

  const isCameraOn = cameraState.cameraStatus === 'active' || cameraState.cameraStatus === 'paused';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel-active rounded-3xl max-w-xl w-full p-6 relative border border-white/10 shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white glass-panel-subtle hover:bg-white/10 transition active:scale-95"
          title="Close Settings"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5 shrink-0">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 text-white flex items-center justify-center shadow-lg shadow-purple-500/25">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">System Settings</h3>
            <p className="text-xs text-slate-400">Configure playback behavior, sensor permissions, and privacy guarantees</p>
          </div>
        </div>

        {/* iOS-Style Segmented Navigation Tabs */}
        <div className="grid grid-cols-3 gap-1 p-1 bg-white/5 rounded-2xl border border-white/5 mb-5 shrink-0">
          <button
            onClick={() => setActiveTab('playback')}
            className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
              activeTab === 'playback'
                ? 'bg-purple-600/30 text-purple-200 shadow border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Playback</span>
          </button>

          <button
            onClick={() => setActiveTab('camera')}
            className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
              activeTab === 'camera'
                ? 'bg-purple-600/30 text-purple-200 shadow border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Camera</span>
          </button>

          <button
            onClick={() => setActiveTab('privacy')}
            className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
              activeTab === 'privacy'
                ? 'bg-purple-600/30 text-purple-200 shadow border border-purple-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Privacy</span>
          </button>
        </div>

        {/* Scrollable Tab Content Area */}
        <div className="overflow-y-auto pr-1 space-y-5 flex-1">
          {/* TAB 1: PLAYBACK & TRANSITIONS */}
          {activeTab === 'playback' && (
            <div className="space-y-4">
              {/* Auto-play Toggle */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">Auto-Play on Mood Shift</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Automatically transition to matching songs when a sustained mood shift is confirmed.
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0 ml-4">
                  <input
                    type="checkbox"
                    checked={prefs.auto_play_on_mood_shift}
                    onChange={(e) => setPrefs({ ...prefs, auto_play_on_mood_shift: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>

              {/* Transition Sensitivity */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold uppercase tracking-wider text-slate-300">
                    Transition Sensitivity
                  </span>
                  <span className="font-mono text-indigo-300 font-bold">
                    {Math.round(prefs.transition_sensitivity * 100)}%
                  </span>
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
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Strict Anti-Thrashing (Holds Song)</span>
                  <span>Balanced</span>
                  <span>Rapid Adaptation</span>
                </div>
              </div>

              {/* Preferred Energy Bias */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold uppercase tracking-wider text-slate-300">
                    Preferred Energy Bias
                  </span>
                  <span className="font-mono text-purple-300 font-bold">
                    {Math.round(prefs.preferred_energy_bias * 100)}%
                  </span>
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
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span>Chill / Ambient</span>
                  <span>Neutral</span>
                  <span>High Energy</span>
                </div>
              </div>

              {/* Preferred Genres */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                  Favorite Genres
                </label>
                <div className="flex flex-wrap gap-2">
                  {ALL_GENRES.map((g) => {
                    const active = prefs.preferred_genres.includes(g.id);
                    return (
                      <button
                        key={g.id}
                        type="button"
                        onClick={() => toggleGenre(g.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition active:scale-95 ${
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
            </div>
          )}

          {/* TAB 2: CAMERA PERMISSIONS & SENSOR CONTROLS */}
          {activeTab === 'camera' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">Browser Camera Permission</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {cameraState.cameraStatus === 'active'
                      ? 'Camera permission granted and active.'
                      : cameraState.cameraStatus === 'paused'
                      ? 'Camera streaming with detection paused.'
                      : cameraState.cameraStatus === 'permission_denied'
                      ? 'Permission denied. Click icon in URL bar to enable.'
                      : 'Camera is currently turned off.'}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1.5 ${
                    isCameraOn ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${isCameraOn ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
                    {cameraState.cameraStatus.toUpperCase()}
                  </span>
                </div>
              </div>

              {/* Action: Turn Camera On / Off */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/5 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="text-xs text-slate-300">
                  Toggle live webcam pipeline to capture visible facial expressions in RAM.
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (isCameraOn) {
                      cameraService.stop();
                    } else {
                      // Trigger camera on document video element
                      const vid = document.querySelector('video');
                      if (vid) cameraService.start(vid);
                    }
                  }}
                  className={`w-full sm:w-auto px-4 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition active:scale-95 ${
                    isCameraOn
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30'
                      : 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/20'
                  }`}
                >
                  {isCameraOn ? (
                    <>
                      <CameraOff className="w-4 h-4" />
                      <span>Stop Camera</span>
                    </>
                  ) : (
                    <>
                      <Camera className="w-4 h-4" />
                      <span>Start Camera</span>
                    </>
                  )}
                </button>
              </div>

              {/* Guidance card if permission denied */}
              {cameraState.cameraStatus === 'permission_denied' && (
                <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                  <div>
                    <span className="font-semibold">Permission Required:</span>
                    <p className="mt-0.5 text-rose-200/80">
                      Your browser blocked camera access. Click the lock or camera icon in your browser's address bar, choose "Allow", and reload or restart camera.
                    </p>
                  </div>
                </div>
              )}

              <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5 text-[11px] text-slate-400 space-y-1">
                <div className="font-semibold text-slate-300">Zero-Storage Guarantee:</div>
                <p>
                  Camera frames are converted to temporary arrays in RAM, evaluated for facial expressions, and immediately freed. No images are saved to disk or databases.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: PRIVACY & HISTORY CLEAR */}
          {activeTab === 'privacy' && (
            <div className="space-y-4">
              <div className="space-y-3 text-xs text-slate-300">
                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5">
                  <Lock className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Strict In-Memory Camera Pipeline:</span>
                    <p className="text-slate-400 mt-0.5">
                      Frames exist purely in volatile memory during facial analysis and are deallocated immediately. Raw video frames are never written to persistent disk or databases.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Human-Centered Affect Terminology:</span>
                    <p className="text-slate-400 mt-0.5">
                      We refer to our signals as an "estimated facial expression", acknowledging that cameras cannot detect internal emotional truth.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">Prohibited Sensitive Inferences:</span>
                    <p className="text-slate-400 mt-0.5">
                      MoodTune AI strictly never attempts to infer or persist race, religion, political beliefs, health, or other sensitive demographic characteristics.
                    </p>
                  </div>
                </div>
              </div>

              {/* Clear History Action */}
              <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/20 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-semibold text-white">Clear Ephemeral History</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Purge all in-memory mood progression timestamps and interaction logs from the active session.
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleClearHistory}
                  disabled={clearing}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center justify-center gap-2 transition active:scale-95"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{clearing ? 'Clearing...' : 'Clear History'}</span>
                </button>
              </div>

              {clearedNotice && (
                <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Session history has been purged from memory and server cache.</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="pt-4 border-t border-white/10 flex items-center justify-end gap-3 mt-4 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl glass-panel-subtle text-xs font-medium text-slate-300 hover:text-white transition active:scale-95"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 flex items-center gap-1.5 transition active:scale-95"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
