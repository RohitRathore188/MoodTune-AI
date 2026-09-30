import { useState, useEffect, useCallback, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { CameraFeed } from './components/CameraFeed';
import { MoodHUD } from './components/MoodHUD';
import { PlayerCard } from './components/PlayerCard';
import { RecommendationQueue } from './components/RecommendationQueue';
import { MoodTimeline } from './components/MoodTimeline';
import { ManualMoodSelector } from './components/ManualMoodSelector';
import { SettingsModal } from './components/SettingsModal';
import { ObservabilityDrawer } from './components/ObservabilityDrawer';
import { EvaluationDashboard } from './components/EvaluationDashboard';
import { WifiOff, AlertCircle, X } from 'lucide-react';

import { api } from './services/api';
import { audioEngine } from './services/audioEngine';
import { cameraService } from './services/cameraService';
import type {
  MoodClass,
  MoodState,
  Track,
  ScoredTrack,
  UserPreferences,
  FaceDetectionResult
} from './types';

const MOOD_GLOW_COLORS: Record<MoodClass, string> = {
  energetic: 'rgba(245, 158, 11, 0.22)',
  positive: 'rgba(16, 185, 129, 0.20)',
  calm: 'rgba(6, 182, 212, 0.22)',
  neutral: 'rgba(139, 92, 246, 0.22)',
  reflective: 'rgba(99, 102, 241, 0.22)',
  low_energy: 'rgba(100, 116, 139, 0.20)',
  tense: 'rgba(244, 63, 94, 0.22)',
};

export function App() {
  // Sensor & Camera Pipeline State
  const [cameraState, setCameraState] = useState(cameraService.getState());
  const [moodState, setMoodState] = useState<MoodState | null>(null);
  const [dominantExpression, setDominantExpression] = useState<string>('');
  const [lastDetectionResult, setLastDetectionResult] = useState<FaceDetectionResult | null>(null);
  const [history, setHistory] = useState<any[]>([]);

  // Session Duration Timer
  const [sessionStartTime, setSessionStartTime] = useState<number>(Date.now());
  const [sessionDuration, setSessionDuration] = useState<number>(0);

  // Network & System States
  const [isOffline, setIsOffline] = useState<boolean>(!navigator.onLine);
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState<boolean>(false);
  const [isLoadingTrack, setIsLoadingTrack] = useState<boolean>(false);
  const [hasAudioError, setHasAudioError] = useState<boolean>(false);

  // User Preferences
  const [userPrefs, setUserPrefs] = useState<UserPreferences>({
    preferred_genres: ['lofi', 'ambient', 'synthwave'],
    disliked_genres: [],
    preferred_energy_bias: 0.5,
    transition_sensitivity: 0.6,
    auto_play_on_mood_shift: true
  });

  // Music & Playback State
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(180);
  const [volume, setVolume] = useState<number>(0.8);
  const [isLiked, setIsLiked] = useState<boolean>(false);
  const [recommendations, setRecommendations] = useState<ScoredTrack[]>([]);
  const [recommendationReason, setRecommendationReason] = useState<string>('');

  // Modals & Views
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [observabilityOpen, setObservabilityOpen] = useState<boolean>(false);
  const [activeView, setActiveView] = useState<'dashboard' | 'evaluation'>('dashboard');

  // Sync refs for audio callbacks & frame handler
  const currentTrackRef = useRef<Track | null>(null);
  currentTrackRef.current = currentTrack;
  const moodStateRef = useRef<MoodState | null>(null);
  moodStateRef.current = moodState;
  const recommendationsRef = useRef<ScoredTrack[]>([]);
  recommendationsRef.current = recommendations;
  const userPrefsRef = useRef<UserPreferences>(userPrefs);
  userPrefsRef.current = userPrefs;
  const currentTimeRef = useRef<number>(0);
  currentTimeRef.current = currentTime;
  const isAnalyzingFrameRef = useRef<boolean>(false);

  // Subscribe to Camera Service
  useEffect(() => {
    return cameraService.subscribe(setCameraState);
  }, []);

  // Online / Offline Detection
  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      setErrorToast(null);
    };
    const handleOffline = () => {
      setIsOffline(true);
      setErrorToast('Network connection lost. Playing from local cache.');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Live Session Duration Timer
  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
      setSessionDuration(elapsed);
    }, 1000);

    return () => clearInterval(timer);
  }, [sessionStartTime]);

  // Audio Engine Lifecycle
  useEffect(() => {
    audioEngine.onTimeUpdate = (curr, dur) => {
      setCurrentTime(curr);
      if (dur > 0) setDuration(dur);
    };

    audioEngine.onStateChange = (playing) => {
      setIsPlaying(playing);
    };

    audioEngine.onEnded = () => {
      if (currentTrackRef.current) {
        api.recordFeedback(
          currentTrackRef.current.id,
          'complete',
          currentTrackRef.current.duration_seconds,
          moodStateRef.current?.estimated_mood
        ).catch(console.error);
      }
      playNextQueuedTrack();
    };

    audioEngine.setVolume(volume);
  }, []);

  // Next Track Queue Advance
  const playNextQueuedTrack = useCallback(() => {
    const queue = recommendationsRef.current;
    if (queue.length > 0) {
      const next = queue[0].track;
      const reason = queue[0].match_reasons?.join(' • ') || 'Next recommended candidate';
      handlePlayTrack(next, reason);
      setRecommendations((prev) => prev.slice(1));
    }
  }, []);

  const handlePlayTrack = useCallback((track: Track, reason?: string) => {
    setHasAudioError(false);
    setIsLoadingTrack(true);
    setCurrentTrack(track);
    setIsLiked(false);
    if (reason) setRecommendationReason(reason);

    try {
      audioEngine.playTrack(track);
    } catch (err) {
      console.error('Audio playback error:', err);
      setHasAudioError(true);
      setErrorToast('Failed to stream audio file.');
    } finally {
      setIsLoadingTrack(false);
    }
  }, []);

  // Initial Load: Preferences and Music Recommendations
  useEffect(() => {
    async function initCatalog() {
      setIsLoadingRecs(true);
      try {
        const prefs = await api.getPreferences().catch(() => null);
        if (prefs) setUserPrefs(prefs);

        const initialRecs = await api.getRecommendations('neutral', 0.85, undefined, 0, 5);
        setRecommendations(initialRecs.recommendations);
        if (initialRecs.recommendations.length > 0) {
          const first = initialRecs.recommendations[0].track;
          setCurrentTrack(first);
          setRecommendationReason(initialRecs.reasoning_summary);
        }
      } catch (err) {
        console.error('Failed to initialize initial recommendations:', err);
        setErrorToast('Could not reach backend API. Offline fallback active.');
      } finally {
        setIsLoadingRecs(false);
      }
    }
    initCatalog();
  }, []);

  // Real-Time Camera Affect Stream Hookup (Single-Pass Inference via frameAnalyzer)
  useEffect(() => {
    cameraService.frameAnalyzer = async (b64: string): Promise<FaceDetectionResult> => {
      // Throttle affect analysis to prevent API queue buildup
      if (isAnalyzingFrameRef.current) {
        return {
          state: 'processing',
          face_count: 0,
          primary_face: null,
          all_faces: [],
          confidence: 0,
          inference_time_ms: 0,
          status_message: 'Frame analysis in-flight...'
        };
      }
      isAnalyzingFrameRef.current = true;

      try {
        const analysis = await api.analyzeMood(b64, undefined, 'default_session');
        const faceDetected = analysis.face_detection?.detected ?? false;

        const faceResult: FaceDetectionResult = {
          state: faceDetected
            ? (analysis.face_detection.face_count > 1 ? 'multiple_faces' : 'single_face')
            : 'no_face',
          face_count: analysis.face_detection?.face_count ?? 0,
          primary_face: analysis.face_detection?.bounding_box || null,
          all_faces: analysis.face_detection?.bounding_box ? [analysis.face_detection.bounding_box] : [],
          confidence: analysis.face_detection?.confidence ?? 0,
          inference_time_ms: analysis.face_detection?.inference_time_ms ?? 0,
          status_message: faceDetected
            ? `Detected face (${analysis.face_detection.expression_estimate})`
            : 'No face detected in camera viewport',
          expression_estimate: analysis.face_detection?.expression_estimate
        };

        setLastDetectionResult(faceResult);

        // If no face in frame, don't update affect/mood
        if (!faceDetected) {
          return faceResult;
        }

        setMoodState(analysis.mood_state);

        if (analysis.face_detection?.expression_estimate) {
          setDominantExpression(analysis.face_detection.expression_estimate);
        }

        // Add to timeline history
        setHistory((prev) => [
          ...prev.slice(-35),
          {
            timestamp: Date.now(),
            mood: analysis.mood_state.estimated_mood,
            confidence: analysis.mood_state.mood_confidence,
            dominant_emotion: analysis.face_detection?.expression_estimate || 'neutral'
          }
        ]);

        // Auto-Transition Check: only transition if Jev explicitly decided 'transition'
        if (analysis.recommendation_trigger_needed && userPrefsRef.current.auto_play_on_mood_shift) {
          const newRecs = await api.getRecommendations(
            analysis.mood_state.estimated_mood,
            analysis.mood_state.mood_confidence,
            currentTrackRef.current?.id,
            currentTimeRef.current,
            5
          );
          setRecommendations(newRecs.recommendations);
          setRecommendationReason(newRecs.reasoning_summary);

          if (
            newRecs.transition_decision === 'transition' &&
            newRecs.recommendations.length > 0 &&
            newRecs.recommendations[0].track.id !== currentTrackRef.current?.id
          ) {
            handlePlayTrack(newRecs.recommendations[0].track, newRecs.reasoning_summary);
          }
        }

        return faceResult;
      } catch (err) {
        // Silently tolerate single frame drop
        return {
          state: 'error',
          face_count: 0,
          primary_face: null,
          all_faces: [],
          confidence: 0,
          inference_time_ms: 0,
          status_message: 'Frame analysis dropped',
          error_message: String(err)
        };
      } finally {
        isAnalyzingFrameRef.current = false;
      }
    };

    return () => {
      cameraService.frameAnalyzer = undefined;
    };
  }, [handlePlayTrack]);

  // Manual Mood Override Handler
  const handleSelectManualMood = useCallback(async (mood: MoodClass) => {
    try {
      const res = await api.analyzeMood(undefined, mood, 'default_session');
      setMoodState(res.mood_state);
      setDominantExpression(mood);

      setHistory((prev) => [
        ...prev.slice(-35),
        {
          timestamp: Date.now(),
          mood: res.mood_state.estimated_mood,
          confidence: 0.95,
          dominant_emotion: mood
        }
      ]);

      setIsLoadingRecs(true);
      const recs = await api.getRecommendations(
        mood,
        0.95,
        currentTrackRef.current?.id,
        currentTime,
        5,
        true // force transition on manual selection
      );
      setRecommendations(recs.recommendations);
      setRecommendationReason(recs.reasoning_summary);

      if (recs.recommendations.length > 0) {
        handlePlayTrack(recs.recommendations[0].track, recs.reasoning_summary);
      }
    } catch (err) {
      console.error('Failed to apply manual mood override:', err);
      setErrorToast('Failed to apply manual mood.');
    } finally {
      setIsLoadingRecs(false);
    }
  }, [currentTime, handlePlayTrack]);

  // Playback Control Handlers
  const handleTogglePlay = () => {
    if (isPlaying) {
      audioEngine.pause();
    } else {
      audioEngine.resume();
    }
  };

  const handleSkip = () => {
    if (currentTrack) {
      api.recordFeedback(
        currentTrack.id,
        'skip',
        currentTime,
        moodState?.estimated_mood
      ).catch(console.error);
    }
    playNextQueuedTrack();
  };

  const handleLike = () => {
    if (!currentTrack) return;
    const nextState = !isLiked;
    setIsLiked(nextState);
    if (nextState) {
      api.recordFeedback(
        currentTrack.id,
        'like',
        currentTime,
        moodState?.estimated_mood
      ).catch(console.error);
    }
  };

  const activeMood = moodState?.estimated_mood || 'neutral';
  const glowColor = MOOD_GLOW_COLORS[activeMood] || MOOD_GLOW_COLORS.neutral;

  return (
    <div className="relative min-h-screen bg-[#07080c] flex flex-col justify-between overflow-x-hidden selection:bg-purple-500 selection:text-white">
      {/* Dynamic Ambient Glow matching stable mood */}
      <div
        className="ambient-glow -top-32 -left-32 w-96 h-96"
        style={{ backgroundColor: glowColor }}
      />
      <div
        className="ambient-glow top-1/2 -right-32 w-96 h-96"
        style={{ backgroundColor: glowColor }}
      />

      {/* Top Navigation Bar */}
      <Navbar
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenObservability={() => setObservabilityOpen(true)}
        onOpenEvaluation={() => setActiveView(activeView === 'evaluation' ? 'dashboard' : 'evaluation')}
        cameraStatus={cameraState.cameraStatus}
        isOffline={isOffline}
      />

      {/* Offline Alert Banner */}
      {isOffline && (
        <div className="w-full bg-amber-500/15 border-b border-amber-500/25 px-4 py-2.5 text-center text-xs text-amber-300 flex items-center justify-center gap-2 z-30 animate-in fade-in">
          <WifiOff className="w-4 h-4 shrink-0" />
          <span>You are currently in offline mode. Playing cached audio; affect updates will sync once reconnected.</span>
        </div>
      )}

      {/* Non-intrusive Error Toast */}
      {errorToast && (
        <div className="fixed top-20 right-6 z-50 p-3 rounded-2xl glass-panel-active border-rose-500/30 text-rose-300 text-xs flex items-center gap-3 shadow-2xl animate-in slide-in-from-right duration-300">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorToast}</span>
          <button onClick={() => setErrorToast(null)} className="p-1 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Responsive Dashboard or Internal AI Evaluation View */}
      {activeView === 'evaluation' ? (
        <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 space-y-6 z-10 flex-1">
          <EvaluationDashboard onBackToPlayer={() => setActiveView('dashboard')} />
        </main>
      ) : (
        <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 space-y-6 z-10 flex-1">
          {/* CENTER SECTION: Camera Viewport & Affect/Mood HUD */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Live Camera Viewport */}
            <div className="lg:col-span-5 flex flex-col">
              <CameraFeed />
            </div>

            {/* Mood HUD, Visible Expression & Confidence */}
            <div className="lg:col-span-7 flex flex-col">
              <MoodHUD
                moodState={moodState}
                detectionResult={lastDetectionResult}
                isCameraActive={cameraState.cameraStatus === 'active' || cameraState.cameraStatus === 'paused'}
                dominantExpression={dominantExpression}
              />
            </div>
          </div>

          {/* MUSIC PLAYER & RECOMMENDATIONS SECTION */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Active Audio Player Card */}
            <div className="lg:col-span-7 flex flex-col">
              <PlayerCard
                currentTrack={currentTrack}
                isPlaying={isPlaying}
                onTogglePlay={handleTogglePlay}
                onSkip={handleSkip}
                onLike={handleLike}
                isLiked={isLiked}
                currentTime={currentTime}
                duration={duration}
                onSeek={(s) => audioEngine.seek(s)}
                volume={volume}
                onVolumeChange={(v) => {
                  setVolume(v);
                  audioEngine.setVolume(v);
                }}
                recommendationReason={recommendationReason}
                isLoading={isLoadingTrack}
                hasError={hasAudioError}
                onRetry={() => {
                  if (currentTrack) handlePlayTrack(currentTrack);
                }}
              />
            </div>

            {/* Jev Bounded Recommended Next Up Queue */}
            <div className="lg:col-span-5 flex flex-col">
              <RecommendationQueue
                recommendations={recommendations}
                onSelectTrack={(t, r) => {
                  api.recordRecommendationAcceptance().catch(console.error);
                  handlePlayTrack(t, r || 'Selected directly from recommendation queue');
                }}
                currentTrackId={currentTrack?.id}
                isLoading={isLoadingRecs}
              />
            </div>
          </div>

          {/* MOOD TIMELINE & MANUAL FALLBACK SELECTOR */}
          <div className="space-y-6">
            <MoodTimeline 
              history={history} 
              sessionDurationSeconds={sessionDuration} 
            />

            <ManualMoodSelector
              currentMood={activeMood}
              onSelectMood={handleSelectManualMood}
            />
          </div>
        </main>
      )}

      {/* Production Footer */}
      <footer className="w-full border-t border-white/5 py-4 px-6 text-xs text-slate-500 z-10 glass-panel-subtle">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <span>MoodTune AI © 2026 — Production Affect-Adaptive Soundscape Engine</span>
          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            <span>LLM analyzes</span>
            <span>•</span>
            <span className="text-purple-300 font-semibold">Jev decides</span>
            <span>•</span>
            <span>Code executes</span>
          </div>
        </div>
      </footer>

      {/* Unified Settings Modal (Camera, Auto-play, Sensitivity, Privacy, Clear History) */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onPreferencesUpdated={(p) => {
          setUserPrefs(p);
          userPrefsRef.current = p;
        }}
        onHistoryCleared={() => {
          setHistory([]);
          setSessionStartTime(Date.now());
          setSessionDuration(0);
        }}
      />

      {/* Observability Telemetry Drawer */}
      <ObservabilityDrawer
        isOpen={observabilityOpen}
        onClose={() => setObservabilityOpen(false)}
      />
    </div>
  );
}

export default App;

