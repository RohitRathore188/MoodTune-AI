export type MoodClass = 
  | 'energetic'
  | 'positive'
  | 'calm'
  | 'neutral'
  | 'reflective'
  | 'low_energy'
  | 'tense';

export interface EmotionProbabilities {
  happy: number;
  neutral: number;
  surprise: number;
  sad: number;
  angry: number;
  fear: number;
  disgust: number;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type FaceDetectionState =
  | 'no_face'
  | 'single_face'
  | 'multiple_faces'
  | 'processing'
  | 'error';

export interface FaceDetectionResult {
  state: FaceDetectionState;
  face_count: number;
  primary_face: BoundingBox | null;
  all_faces: BoundingBox[];
  confidence: number;
  inference_time_ms: number;
  status_message: string;
  error_message?: string | null;
  expression_estimate?: string;
  detected?: boolean;
  bounding_box?: BoundingBox | null;
}

export interface FaceEmotionResult {
  detected: boolean;
  face_count: number;
  bounding_box: BoundingBox | null;
  expression_estimate: string;
  emotion_probabilities: EmotionProbabilities;
  confidence: number;
  inference_time_ms: number;
}

export interface MoodState {
  estimated_mood: MoodClass;
  mood_confidence: number;
  smoothed_emotion_probabilities: EmotionProbabilities;
  is_stable: boolean;
  stable_duration_seconds: number;
  previous_mood: MoodClass | null;
  transition_occurred: boolean;
}

export interface MoodAnalysisResponse {
  face_detection: FaceEmotionResult;
  mood_state: MoodState;
  explanation: string;
  recommendation_trigger_needed: boolean;
}

export interface MusicProfile {
  genre: string;
  energy: number;
  valence: number;
  tempo: number;
  instrumental: boolean;
  danceability: number;
  mood_tags: string[];
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  duration_seconds: number;
  audio_url: string;
  cover_art_url: string;
  profile: MusicProfile;
  provider: string;
}

export interface ScoredTrack {
  track: Track;
  match_score: number;
  match_reasons: string[];
  is_exploration: boolean;
}

export interface DecisionResultItem {
  value: string;
  confidence: number;
  probabilities?: Record<string, number>;
}

export interface JevDecisionBundle {
  mood: DecisionResultItem;
  energy: DecisionResultItem;
  transition: DecisionResultItem;
  strategy: DecisionResultItem;
  confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW';
  decision_source: string;
  latency_ms: number;
}

export interface RecommendationResponse {
  recommendations: ScoredTrack[];
  target_profile: MusicProfile;
  jev_decision: JevDecisionBundle;
  transition_decision: string;
  reasoning_summary: string;
  evaluation_confidence: number;
}

export interface UserPreferences {
  preferred_genres: string[];
  disliked_genres: string[];
  preferred_energy_bias: number;
  transition_sensitivity: number;
  auto_play_on_mood_shift: boolean;
}

export interface SystemHealthMetrics {
  uptime_seconds: number;
  total_frames_analyzed: number;
  faces_detected_count: number;
  jev_calls_count: number;
  fallback_decisions_count: number;
  songs_played_count: number;
  songs_skipped_count: number;
  skip_rate: number;
  average_mood_stability_duration_sec: number;
  current_mood: string;
  latencies: {
    cv_inference_ms: number;
    temporal_smoothing_ms: number;
    jev_decision_ms: number;
    recommendation_scoring_ms: number;
    total_pipeline_ms: number;
  };
  active_music_provider: string;
}

export interface ConfidenceDistribution {
  high: number;
  medium: number;
  low: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface EmotionMetrics {
  inference_latency_ms: number;
  confidence_distribution: ConfidenceDistribution;
  no_face_rate: number;
  total_frames: number;
  no_face_frames: number;
}

export interface MoodMetrics {
  stability_score: number;
  average_stability_duration_sec: number;
  transition_frequency_per_10m: number;
  total_transitions: number;
  low_confidence_rate: number;
}

export interface ModelPerformanceMetrics {
  emotion: EmotionMetrics;
  mood: MoodMetrics;
  overall_model_health: string;
}

export interface RecommendationEngineMetrics {
  acceptance_rate: number;
  skip_rate: number;
  completion_rate: number;
  diversity_score: number;
  total_recommendations_shown: number;
  total_recommendations_accepted: number;
}

export interface PlaybackMetrics {
  average_listening_duration_sec: number;
  skip_frequency_per_10m: number;
  transition_frequency_per_10m: number;
  total_songs_played: number;
  total_songs_skipped: number;
  total_songs_completed: number;
}

export interface RecommendationPerformanceMetrics {
  recommendation: RecommendationEngineMetrics;
  playback: PlaybackMetrics;
  overall_recommendation_health: string;
}

export interface SystemPerformanceMetrics {
  jev_latency_ms: number;
  jev_failures_count: number;
  jev_success_count: number;
  fallback_frequency: number;
  fallback_count: number;
  api_failures_count: number;
  api_total_calls: number;
  api_failure_rate: number;
  latencies: {
    cv_inference_ms: number;
    temporal_smoothing_ms: number;
    jev_decision_ms: number;
    recommendation_scoring_ms: number;
    total_pipeline_ms: number;
  };
  system_uptime_seconds: number;
  overall_system_health: string;
}

export interface EvaluationDashboardResponse {
  model_performance: ModelPerformanceMetrics;
  recommendation_performance: RecommendationPerformanceMetrics;
  system_performance: SystemPerformanceMetrics;
  disclaimer: string;
  evaluation_timestamp: number;
  health_verdict: string;
  actionable_recommendations: string[];
}

