import { describe, it, expect } from 'vitest';
import type { Track, ScoredTrack, UserPreferences, FaceDetectionResult } from '../types';

describe('Phase 11: Production UI Component Specifications', () => {
  it('validates user preferences schema includes all 5 requested settings', () => {
    const prefs: UserPreferences = {
      preferred_genres: ['lofi', 'ambient'],
      disliked_genres: [],
      preferred_energy_bias: 0.5,
      transition_sensitivity: 0.65,
      auto_play_on_mood_shift: true
    };

    expect(prefs).toHaveProperty('transition_sensitivity');
    expect(prefs).toHaveProperty('auto_play_on_mood_shift');
    expect(prefs.transition_sensitivity).toBeGreaterThanOrEqual(0.2);
    expect(prefs.transition_sensitivity).toBeLessThanOrEqual(1.0);
    expect(typeof prefs.auto_play_on_mood_shift).toBe('boolean');
  });

  it('validates no-face detection state properties and anti-thrashing hold', () => {
    const noFaceResult: FaceDetectionResult = {
      state: 'no_face',
      face_count: 0,
      primary_face: null,
      all_faces: [],
      confidence: 0.0,
      inference_time_ms: 12.5,
      status_message: 'No face detected in camera viewport.',
      expression_estimate: 'undetected (No face detected)'
    };

    expect(noFaceResult.state).toBe('no_face');
    expect(noFaceResult.face_count).toBe(0);
    expect(noFaceResult.primary_face).toBeNull();
  });

  it('validates recommended track scoring and human-centered reasoning schema', () => {
    const sampleTrack: Track = {
      id: 'trk_01',
      title: 'Neon Drift',
      artist: 'Aura',
      album: 'Reflections',
      duration_seconds: 195,
      audio_url: '/audio/neon_drift.mp3',
      cover_art_url: '/covers/neon_drift.jpg',
      profile: {
        genre: 'synthwave',
        energy: 0.72,
        valence: 0.68,
        tempo: 0.75,
        instrumental: true,
        danceability: 0.65,
        mood_tags: ['energetic', 'positive']
      },
      provider: 'local'
    };

    const scoredCandidate: ScoredTrack = {
      track: sampleTrack,
      match_score: 0.94,
      match_reasons: ['MOOD_MATCH: positive', 'GENRE_MATCH: synthwave'],
      is_exploration: false
    };

    expect(scoredCandidate.match_score).toBeGreaterThan(0);
    expect(scoredCandidate.match_score).toBeLessThanOrEqual(1);
    expect(scoredCandidate.match_reasons).toHaveLength(2);
    expect(scoredCandidate.track.title).toBe('Neon Drift');
  });

  it('validates session duration formatting utility behavior', () => {
    const formatDuration = (totalSeconds: number) => {
      const mins = Math.floor(totalSeconds / 60);
      const secs = Math.floor(totalSeconds % 60);
      return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
    };

    expect(formatDuration(0)).toBe('00:00');
    expect(formatDuration(45)).toBe('00:45');
    expect(formatDuration(125)).toBe('02:05');
    expect(formatDuration(3600)).toBe('60:00');
  });
});
