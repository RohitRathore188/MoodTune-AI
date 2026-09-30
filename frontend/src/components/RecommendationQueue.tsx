import React from 'react';
import { ListMusic, Play, Sparkles, Music } from 'lucide-react';
import type { ScoredTrack, Track } from '../types';

interface RecommendationQueueProps {
  recommendations: ScoredTrack[];
  onSelectTrack: (track: Track, reason?: string) => void;
  currentTrackId?: string;
  isLoading?: boolean;
}

export const RecommendationQueue: React.FC<RecommendationQueueProps> = ({
  recommendations,
  onSelectTrack,
  currentTrackId,
  isLoading = false
}) => {
  return (
    <div className="glass-panel rounded-3xl p-5 flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <ListMusic className="w-4 h-4 text-purple-400" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Jev Recommended Next Up
          </h2>
        </div>
        <span className="text-[10px] text-purple-300 font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20">
          Ranked Candidates
        </span>
      </div>

      {/* Main Content Area */}
      <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1 flex-1">
        {isLoading ? (
          /* Loading Skeletons */
          <div className="space-y-2.5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="p-3 rounded-2xl glass-panel-subtle flex items-center justify-between">
                <div className="flex items-center gap-3 w-full">
                  <div className="w-11 h-11 rounded-xl skeleton-shimmer shrink-0" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-3.5 w-3/4 rounded-md skeleton-shimmer" />
                    <div className="h-3 w-1/2 rounded-md skeleton-shimmer" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : recommendations.length === 0 ? (
          /* Empty State */
          <div className="py-12 px-4 rounded-2xl bg-white/5 border border-white/5 text-center flex flex-col items-center justify-center">
            <Music className="w-8 h-8 text-purple-400/40 mb-2 animate-bounce" />
            <p className="text-xs font-semibold text-slate-300">No Candidates Queued</p>
            <p className="text-[11px] text-slate-500 max-w-xs mt-1">
              Affect engine is analyzing current facial expressions to curate tailored candidates.
            </p>
          </div>
        ) : (
          recommendations.slice(0, 5).map((item) => {
            const isCurrent = item.track.id === currentTrackId;
            const reasonText = item.match_reasons?.length > 0 
              ? item.match_reasons.join(' • ')
              : 'Matches current estimated mood & listening history';

            return (
              <div
                key={item.track.id}
                onClick={() => onSelectTrack(item.track, reasonText)}
                className={`p-2.5 rounded-2xl flex items-center justify-between cursor-pointer transition-all duration-200 group active:scale-[0.98] ${
                  isCurrent
                    ? 'bg-purple-600/25 border border-purple-500/50 shadow-lg shadow-purple-500/15'
                    : 'glass-panel-subtle hover:bg-white/10 hover:border-white/20 border border-white/5'
                }`}
              >
                {/* Track Artwork & Info */}
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="relative w-11 h-11 rounded-xl overflow-hidden shrink-0 bg-zinc-950">
                    <img
                      src={item.track.cover_art_url}
                      alt={item.track.title}
                      className="w-full h-full object-cover group-hover:scale-110 transition duration-300"
                    />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition">
                      <Play className="w-4 h-4 text-white fill-white" />
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <h4 className="text-xs font-bold text-white truncate group-hover:text-purple-200 transition">
                        {item.track.title}
                      </h4>
                      {item.is_exploration && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-0.5">
                          <Sparkles className="w-2.5 h-2.5" /> Explore
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-300 truncate">
                      {item.track.artist} • <span className="capitalize text-slate-400">{item.track.profile.genre}</span>
                    </p>
                    {/* Reason Text */}
                    <p className="text-[10px] text-purple-300/80 truncate mt-0.5 font-medium">
                      {reasonText}
                    </p>
                  </div>
                </div>

                {/* Match Score & Energy */}
                <div className="text-right shrink-0 ml-3">
                  <div className="text-xs font-bold text-emerald-400 font-mono">
                    {Math.round(item.match_score * 100)}%
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {Math.round(item.track.profile.energy * 100)}% eng
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

