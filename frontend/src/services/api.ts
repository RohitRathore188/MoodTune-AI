import type { 
  MoodAnalysisResponse, 
  RecommendationResponse, 
  Track, 
  UserPreferences,
  SystemHealthMetrics,
  MoodClass,
  FaceDetectionResult,
  EvaluationDashboardResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const api = {
  async detectFaces(imageBase64: string): Promise<FaceDetectionResult> {
    const res = await fetch(`${API_BASE}/camera/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: imageBase64,
        timestamp: Date.now() / 1000
      })
    });
    if (!res.ok) throw new Error(`Face detection failed: ${res.statusText}`);
    return res.json();
  },

  async getCameraStatus() {
    const res = await fetch(`${API_BASE}/camera/status`);
    if (!res.ok) throw new Error('Failed to fetch camera status');
    return res.json();
  },
  async analyzeMood(
    imageBase64?: string,
    manualOverride?: MoodClass,
    sessionId: string = 'default_session'
  ): Promise<MoodAnalysisResponse> {
    const res = await fetch(`${API_BASE}/mood/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: imageBase64,
        manual_mood_override: manualOverride,
        session_id: sessionId,
        timestamp: Date.now() / 1000
      })
    });
    if (!res.ok) throw new Error(`Mood analysis failed: ${res.statusText}`);
    return res.json();
  },

  async getRecommendations(
    mood: MoodClass,
    confidence: number = 0.85,
    currentSongId?: string,
    secondsPlayed: number = 0,
    limit: number = 5,
    forceTransition: boolean = false
  ): Promise<RecommendationResponse> {
    const params = new URLSearchParams({
      mood,
      confidence: confidence.toString(),
      seconds_played: secondsPlayed.toString(),
      limit: limit.toString(),
      force_transition: forceTransition.toString()
    });
    if (currentSongId) params.append('current_song_id', currentSongId);

    const res = await fetch(`${API_BASE}/recommendations?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to fetch recommendations: ${res.statusText}`);
    return res.json();
  },

  async recordFeedback(
    trackId: string,
    feedbackType: 'like' | 'dislike' | 'skip' | 'complete',
    secondsPlayed: number,
    moodAtTime?: string
  ): Promise<void> {
    await fetch(`${API_BASE}/recommendations/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        track_id: trackId,
        feedback_type: feedbackType,
        seconds_played: secondsPlayed,
        mood_at_time: moodAtTime
      })
    });
  },

  async getTracks(): Promise<Track[]> {
    const res = await fetch(`${API_BASE}/music/tracks`);
    if (!res.ok) throw new Error('Failed to load tracks');
    return res.json();
  },

  async getPreferences(): Promise<UserPreferences> {
    const res = await fetch(`${API_BASE}/preferences`);
    if (!res.ok) throw new Error('Failed to load preferences');
    return res.json();
  },

  async updatePreferences(prefs: UserPreferences): Promise<UserPreferences> {
    const res = await fetch(`${API_BASE}/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs)
    });
    if (!res.ok) throw new Error('Failed to update preferences');
    return res.json();
  },

  async getHistory(sessionId: string = 'default_session') {
    const res = await fetch(`${API_BASE}/history?session_id=${sessionId}`);
    if (!res.ok) return { history: [] };
    return res.json();
  },

  async clearHistory(sessionId: string = 'default_session') {
    const res = await fetch(`${API_BASE}/history/clear?session_id=${sessionId}`, {
      method: 'POST'
    });
    return res.json();
  },

  async getMetrics(): Promise<{ metrics: SystemHealthMetrics; recommendation_health_status: string; actionable_recommendations: string[] }> {
    const res = await fetch(`${API_BASE}/metrics`);
    if (!res.ok) throw new Error('Failed to load metrics');
    return res.json();
  },

  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  async getEvaluation(): Promise<EvaluationDashboardResponse> {
    const res = await fetch(`${API_BASE}/evaluation`);
    if (!res.ok) throw new Error('Failed to load evaluation metrics');
    return res.json();
  },

  async resetEvaluation(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/evaluation/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset evaluation metrics');
    return res.json();
  },

  async recordRecommendationAcceptance(): Promise<{ status: string; acceptance_rate: number }> {
    const res = await fetch(`${API_BASE}/evaluation/record-acceptance`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to record recommendation acceptance');
    return res.json();
  }
};
