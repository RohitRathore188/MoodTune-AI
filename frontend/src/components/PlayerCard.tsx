import React, { useState } from 'react';
import { Play, Pause, SkipForward, Heart, Volume2, VolumeX, Disc, AlertCircle, RefreshCw } from 'lucide-react';
import type { Track } from '../types';

interface PlayerCardProps {
  currentTrack: Track | null;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onSkip: () => void;
  onLike: () => void;
  isLiked: boolean;
  currentTime: number;
  duration: number;
  onSeek: (seconds: number) => void;
  volume: number;
  onVolumeChange: (val: number) => void;
  recommendationReason?: string;
  isLoading?: boolean;
  hasError?: boolean;
  onRetry?: () => void;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({
  currentTrack,
  isPlaying,
  onTogglePlay,
  onSkip,
  onLike,
  isLiked,
  currentTime,
  duration,
  onSeek,
  volume,
  onVolumeChange,
  recommendationReason,
  isLoading = false,
  hasError = false,
  onRetry
}) => {
  const [previousVolume, setPreviousVolume] = useState<number>(0.8);

  const formatTime = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const progressPercent = duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;

  const handleToggleMute = () => {
    if (volume > 0) {
      setPreviousVolume(volume);
      onVolumeChange(0);
    } else {
      onVolumeChange(previousVolume || 0.8);
    }
  };

  // Loading State
  if (isLoading) {
    return (
      <div className="glass-panel rounded-3xl p-6 flex flex-col justify-between min-h-[360px]">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-2xl skeleton-shimmer shrink-0" />
          <div className="flex-1 w-full space-y-3">
            <div className="h-4 w-28 rounded-lg skeleton-shimmer" />
            <div className="h-7 w-48 rounded-lg skeleton-shimmer" />
            <div className="h-4 w-36 rounded-lg skeleton-shimmer" />
            <div className="h-10 w-full rounded-xl skeleton-shimmer mt-4" />
          </div>
        </div>
        <div className="w-full mt-6 space-y-2">
          <div className="h-2 w-full rounded-full skeleton-shimmer" />
          <div className="h-12 w-full rounded-2xl skeleton-shimmer mt-4" />
        </div>
      </div>
    );
  }

  // Error State
  if (hasError) {
    return (
      <div className="glass-panel rounded-3xl p-8 flex flex-col items-center justify-center min-h-[360px] text-center">
        <div className="w-14 h-14 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center mb-3 border border-rose-500/30">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h3 className="text-base font-bold text-white">Audio Stream Unavailable</h3>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          The selected audio file could not be loaded. You can retry playing or skip to the next recommended song.
        </p>
        <div className="flex items-center gap-3 mt-5">
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white flex items-center gap-1.5 transition active:scale-95"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          )}
          <button
            onClick={onSkip}
            className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-semibold text-white flex items-center gap-1.5 transition shadow-lg shadow-purple-500/20 active:scale-95"
          >
            <SkipForward className="w-3.5 h-3.5" />
            <span>Next Track</span>
          </button>
        </div>
      </div>
    );
  }

  // Empty State
  if (!currentTrack) {
    return (
      <div className="glass-panel rounded-3xl p-8 flex flex-col items-center justify-center min-h-[360px] text-center">
        <Disc className="w-16 h-16 text-purple-400/40 animate-spin-slow mb-4" />
        <h3 className="text-lg font-semibold text-slate-200">Ready to Play</h3>
        <p className="text-xs text-slate-400 max-w-sm mt-1 leading-relaxed">
          Facial affect detection will automatically curate music tailored to your estimated mood, or select any song from recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel-active rounded-3xl p-6 relative overflow-hidden flex flex-col justify-between shadow-2xl">
      {/* Top track details & vinyl visual */}
      <div className="flex flex-col sm:flex-row items-center gap-6">
        {/* Vinyl & Cover Art Stack */}
        <div className="relative group shrink-0">
          <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-2xl overflow-hidden shadow-2xl border border-white/10 relative z-10 bg-zinc-950">
            <img
              src={currentTrack.cover_art_url}
              alt={currentTrack.title}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
          </div>

          {/* Spinning Vinyl Record behind artwork */}
          <div
            className={`absolute top-0 -right-4 sm:-right-8 w-32 h-32 sm:w-40 sm:h-40 rounded-full bg-gradient-to-tr from-black via-zinc-900 to-black border-4 border-zinc-800 shadow-2xl flex items-center justify-center transition-all duration-700 z-0 ${
              isPlaying ? 'animate-spin-slow translate-x-3 sm:translate-x-6' : 'translate-x-0'
            }`}
          >
            {/* Center label */}
            <div className="w-12 h-12 rounded-full border-2 border-purple-500/40 bg-zinc-900 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-purple-400" />
            </div>
          </div>
        </div>

        {/* Track Title, Artist, & Soundwave */}
        <div className="flex-1 w-full text-center sm:text-left mt-2 sm:mt-0">
          <div className="flex items-center justify-center sm:justify-start gap-2 mb-2 flex-wrap">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {currentTrack.profile.genre}
            </span>
            <span className="text-[10px] text-slate-400">
              Energy: {Math.round(currentTrack.profile.energy * 100)}%
            </span>
            <span className="text-[10px] text-slate-400">
              Valence: {Math.round(currentTrack.profile.valence * 100)}%
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight line-clamp-1">
            {currentTrack.title}
          </h2>
          <p className="text-sm font-medium text-slate-300 mt-0.5 line-clamp-1">
            {currentTrack.artist} • <span className="text-slate-400">{currentTrack.album}</span>
          </p>

          {/* Equalizer Soundwave Reaction */}
          <div className="flex items-center justify-center sm:justify-start gap-1 h-6 mt-3">
            {[35, 70, 25, 95, 65, 30, 85, 45, 90, 40].map((h, i) => (
              <span
                key={i}
                className="w-1 bg-purple-400/80 rounded-full transition-all duration-300"
                style={{
                  height: isPlaying ? `${Math.max(4, (h * (0.5 + Math.random() * 0.5)) / 4)}px` : '4px'
                }}
              />
            ))}
            <span className="text-[10px] text-purple-300 ml-2 font-mono font-semibold">
              {isPlaying ? 'PLAYING' : 'PAUSED'}
            </span>
          </div>

          {/* Recommendation Rationale Pill */}
          {recommendationReason && (
            <p className="text-[11px] text-purple-200/90 mt-3 p-2.5 rounded-xl bg-purple-950/30 border border-purple-500/20 leading-relaxed text-left line-clamp-2">
              💡 {recommendationReason}
            </p>
          )}
        </div>
      </div>

      {/* Timeline Seek Bar */}
      <div className="w-full mt-6">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1.5">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
        <div
          className="relative w-full h-2 rounded-full bg-white/10 cursor-pointer overflow-hidden group"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const clickPos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            onSeek(clickPos * duration);
          }}
        >
          <div
            className="h-full bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400 rounded-full transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Main Playback Controls */}
      <div className="flex items-center justify-between mt-5 pt-3 border-t border-white/10">
        {/* Like Button */}
        <button
          onClick={onLike}
          className={`p-3 rounded-2xl glass-panel-subtle hover:bg-white/10 transition active:scale-95 ${
            isLiked ? 'text-rose-500 bg-rose-500/10 border-rose-500/30' : 'text-slate-400'
          }`}
          title={isLiked ? 'Liked' : 'Like Song'}
        >
          <Heart className={`w-5 h-5 ${isLiked ? 'fill-rose-500' : ''}`} />
        </button>

        {/* Center: Play/Pause and Next/Skip */}
        <div className="flex items-center gap-4">
          <button
            onClick={onTogglePlay}
            className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 text-white flex items-center justify-center shadow-lg shadow-purple-500/30 hover:scale-105 active:scale-95 transition"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-6 h-6 fill-white" /> : <Play className="w-6 h-6 fill-white ml-0.5" />}
          </button>

          <button
            onClick={onSkip}
            className="p-3 rounded-2xl glass-panel-subtle text-slate-300 hover:text-white hover:bg-white/10 transition active:scale-95"
            title="Next Track"
          >
            <SkipForward className="w-5 h-5" />
          </button>
        </div>

        {/* Volume Controls with Mute Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleMute}
            className="p-1.5 text-slate-400 hover:text-white transition"
            title={volume === 0 ? 'Unmute' : 'Mute'}
          >
            {volume === 0 ? (
              <VolumeX className="w-4 h-4 text-rose-400" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>

          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
            className="w-16 sm:w-20 accent-purple-500 h-1.5 rounded-full bg-white/20 cursor-pointer"
            title={`Volume: ${Math.round(volume * 100)}%`}
          />
        </div>
      </div>
    </div>
  );
};

