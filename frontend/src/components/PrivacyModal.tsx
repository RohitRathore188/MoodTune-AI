import React, { useState } from 'react';
import { ShieldCheck, X, Trash2, CheckCircle2, Lock } from 'lucide-react';
import { api } from '../services/api';

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onHistoryCleared: () => void;
}

export const PrivacyModal: React.FC<PrivacyModalProps> = ({
  isOpen,
  onClose,
  onHistoryCleared
}) => {
  const [clearing, setClearing] = useState(false);
  const [clearedNotice, setClearedNotice] = useState(false);

  if (!isOpen) return null;

  const handleClearHistory = async () => {
    setClearing(true);
    try {
      await api.clearHistory();
      setClearedNotice(true);
      onHistoryCleared();
      setTimeout(() => setClearedNotice(false), 3000);
    } catch (err) {
      console.error('Failed to clear history:', err);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="glass-panel-active rounded-3xl max-w-lg w-full p-6 relative border border-white/10 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white glass-panel-subtle hover:bg-white/10 transition"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Title */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Privacy by Default</h3>
            <p className="text-xs text-slate-400">Strict In-Memory Camera Processing Guarantee</p>
          </div>
        </div>

        {/* Core Principles */}
        <div className="space-y-3 my-4 text-xs text-slate-300">
          <div className="p-3 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Zero Raw Video Storage:</span>
              <p className="text-slate-400 mt-0.5">
                Camera frames are converted to temporary arrays in RAM, evaluated for facial expressions, and immediately freed. No images are saved to disk or databases.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-white/5 border border-white/5 flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-white">Human-Centered Affect Estimation:</span>
              <p className="text-slate-400 mt-0.5">
                The system only estimates visible expressions (e.g. smiles, frowns) and does not pretend to read your internal emotional state.
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={handleClearHistory}
            disabled={clearing}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center justify-center gap-2 transition"
          >
            <Trash2 className="w-4 h-4" />
            <span>{clearing ? 'Clearing...' : 'Clear Mood History'}</span>
          </button>

          {clearedNotice && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" /> History wiped from server!
            </span>
          )}

          <button
            onClick={onClose}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-500/20 transition"
          >
            Understood
          </button>
        </div>
      </div>
    </div>
  );
};
