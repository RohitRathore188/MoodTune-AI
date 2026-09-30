"""Playback Manager (Phase 8: Intelligent Playback).
Responsible for:
- play, pause, resume, skip
- queue management
- next track selection
- intelligent transition management

CRITICAL PRINCIPLES:
1. Mood changes must NOT immediately change the song.
2. Anti-thrashing guardrails:
   - Mood stability check (minimum stable duration and confidence threshold)
   - Transition cooldown enforcement (prevents rapid/frequent switching)
   - Track progress evaluation (allows song to develop before interruption)
   - Compatibility scoring (if song is still compatible with new mood, CONTINUE)
   - User interaction override (manual pause suppresses automatic transition)
3. Bounded Jev Decision:
   - Uses JevSystemOne / JevDecisionService to decide transition action ("continue", "transition", "retrieve_new_candidates").
"""
import time
import logging
from typing import List, Optional, Dict, Any

from ..config import settings
from ..schemas.music import Track, PlaybackState, TransitionDecisionResult, MusicProfile
from ..services.music_provider import music_provider, MusicProvider
from ..services.jev_service import jev_decision_service, JevDecisionService
from ..services.personalization_service import personalization_service, PersonalizationService

logger = logging.getLogger("moodtune.playback_manager")

# Controlled mood targets for acoustic compatibility scoring
MOOD_TARGET_FEATURES: Dict[str, Dict[str, Any]] = {
    "energetic": {
        "target_energy": 0.88,
        "target_valence": 0.80,
        "tags": ["energetic", "positive", "workout", "night", "rush"]
    },
    "positive": {
        "target_energy": 0.75,
        "target_valence": 0.85,
        "tags": ["positive", "uplifting", "summer", "joy"]
    },
    "calm": {
        "target_energy": 0.25,
        "target_valence": 0.65,
        "tags": ["calm", "relaxing", "nature", "peace", "study", "cozy"]
    },
    "neutral": {
        "target_energy": 0.45,
        "target_valence": 0.50,
        "tags": ["neutral", "focus", "work", "balance"]
    },
    "reflective": {
        "target_energy": 0.35,
        "target_valence": 0.40,
        "tags": ["reflective", "acoustic", "deep", "gentle"]
    },
    "low_energy": {
        "target_energy": 0.20,
        "target_valence": 0.30,
        "tags": ["low_energy", "comfort", "soothing", "slow"]
    },
    "tense": {
        "target_energy": 0.18,
        "target_valence": 0.55,
        "tags": ["tense", "soothing", "de-stress", "breathe", "calm"]
    }
}


class PlaybackManager:
    """Intelligent Playback and Transition Manager."""

    def __init__(
        self,
        provider: Optional[MusicProvider] = None,
        jev: Optional[JevDecisionService] = None,
        personalization: Optional[PersonalizationService] = None
    ):
        self.provider = provider or music_provider
        self.jev = jev or jev_decision_service
        self.personalization = personalization or personalization_service

        self.queue: List[Track] = []
        self.history: List[Track] = []
        self.manual_pause: bool = False
        self.last_transition_timestamp: float = 0.0
        self.recent_transitions: List[float] = []
        self.user_interactions: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Core Playback Controls
    # -------------------------------------------------------------------------

    async def play(self, track_id: Optional[str] = None, position_seconds: float = 0.0) -> PlaybackState:
        """Starts playback of the given track or resumes the current/next track."""
        self.manual_pause = False
        self._record_user_action("play", {"track_id": track_id, "position_seconds": position_seconds})

        if track_id:
            # If track is in queue, remove it so it's not queued twice
            self.remove_from_queue(track_id)
            state = await self.provider.play(track_id, position_seconds=position_seconds)
            self._update_transition_time()
            return self._enrich_playback_state(state)

        # No track_id provided: resume active or start from queue
        current_state = self.provider.get_playback_state()
        if current_state.current_track:
            state = await self.provider.resume()
            return self._enrich_playback_state(state)

        # If no active track, advance to next in queue
        next_track = await self.next_track(reason="play_start")
        if next_track:
            return self.get_playback_state()

        return self._enrich_playback_state(self.provider.get_playback_state())

    async def pause(self) -> PlaybackState:
        """Manually pauses playback. Sets manual_pause flag to suppress auto-transitions."""
        self.manual_pause = True
        self._record_user_action("pause")
        state = await self.provider.pause()
        logger.info("Manual pause activated; automatic transitions will be suppressed.")
        return self._enrich_playback_state(state)

    async def resume(self) -> PlaybackState:
        """Manually resumes playback. Clears manual_pause flag."""
        self.manual_pause = False
        self._record_user_action("resume")
        state = await self.provider.resume()
        logger.info("Manual resume activated.")
        return self._enrich_playback_state(state)

    async def skip(self, reason: str = "user_skip") -> PlaybackState:
        """
        Explicit user skip:
        - Bypasses mood stability and compatibility checks
        - Penalizes current track in personalization service
        - Immediately advances to the next track in queue
        """
        current_state = self.provider.get_playback_state()
        cur_track = current_state.current_track
        if cur_track:
            self.personalization.record_interaction(
                user_id="default_user",
                track=cur_track,
                feedback_type="skip",
                seconds_played=current_state.position_seconds
            )
            logger.info(f"Recorded user skip penalty for track '{cur_track.title}' (ID: {cur_track.id})")

        self.manual_pause = False
        self._record_user_action("user_skip", {"previous_track_id": cur_track.id if cur_track else None})
        self._update_transition_time()

        await self.next_track(reason=reason)
        return self.get_playback_state()

    # -------------------------------------------------------------------------
    # Queue Management
    # -------------------------------------------------------------------------

    def get_queue(self) -> List[Track]:
        """Returns the current upcoming track queue."""
        return list(self.queue)

    def add_to_queue(self, track: Track, prepend: bool = False):
        """Adds a track to the queue, avoiding immediate duplicates."""
        if any(t.id == track.id for t in self.queue):
            return
        if prepend:
            self.queue.insert(0, track)
        else:
            self.queue.append(track)
        logger.info(f"Added track '{track.title}' to queue (queue size: {len(self.queue)})")

    def set_queue(self, tracks: List[Track]):
        """Sets the upcoming queue."""
        self.queue = list(tracks)
        logger.info(f"Updated queue with {len(self.queue)} tracks.")

    def remove_from_queue(self, track_id: str) -> Optional[Track]:
        """Removes a track from the queue by ID."""
        for i, t in enumerate(self.queue):
            if t.id == track_id:
                removed = self.queue.pop(i)
                return removed
        return None

    def clear_queue(self):
        """Empties the upcoming queue."""
        self.queue.clear()

    async def replenish_queue(self, target_mood: Optional[str] = None, limit: int = 5) -> List[Track]:
        """Replenishes the queue with candidate recommendations matching mood or catalog."""
        candidates = await self.provider.get_recommendations(mood=target_mood, limit=limit)
        existing_ids = {t.id for t in self.queue}
        current_state = self.provider.get_playback_state()
        if current_state.current_track:
            existing_ids.add(current_state.current_track.id)

        added = []
        for track in candidates:
            if track.id not in existing_ids:
                self.queue.append(track)
                existing_ids.add(track.id)
                added.append(track)

        logger.info(f"Replenished queue with {len(added)} tracks for mood '{target_mood}'.")
        return added

    async def next_track(self, reason: str = "queue_advance") -> Optional[Track]:
        """
        Advances to the next track in the queue.
        If queue is empty, auto-replenishes from the provider.
        """
        if not self.queue:
            await self.replenish_queue()

        if not self.queue:
            logger.warning("Queue is empty and catalog returned no candidates.")
            return None

        next_trk = self.queue.pop(0)
        current_state = self.provider.get_playback_state()
        if current_state.current_track:
            self.history.append(current_state.current_track)

        await self.provider.play(next_trk.id, position_seconds=0.0)
        self._update_transition_time()
        logger.info(f"Advanced to next track '{next_trk.title}' by '{next_trk.artist}' (reason: {reason})")
        return next_trk

    # -------------------------------------------------------------------------
    # Track Compatibility Calculation
    # -------------------------------------------------------------------------

    def calculate_compatibility(self, track: Track, mood: str) -> float:
        """
        Calculates compatibility [0.0, 1.0] between a track's audio profile and target mood.
        Used to ensure that if current song is still compatible with a new mood,
        we CONTINUE rather than abruptly cutting off the song.
        """
        mood_key = mood.lower()
        target = MOOD_TARGET_FEATURES.get(mood_key, MOOD_TARGET_FEATURES["neutral"])

        target_energy = target["target_energy"]
        target_valence = target["target_valence"]
        expected_tags = target["tags"]

        p = track.profile
        energy_diff = abs(p.energy - target_energy)
        valence_diff = abs(p.valence - target_valence)

        # Tag overlap check
        has_matching_tag = any(
            t.lower() in expected_tags or mood_key in t.lower()
            for t in p.mood_tags
        )

        # Base acoustic similarity
        base_score = 1.0 - (energy_diff * 0.60 + valence_diff * 0.40)

        # Bonus for mood tag match
        if has_matching_tag:
            base_score += 0.15

        # Penalty if energy is strongly discordant (> 0.40 diff) and no tag match
        if energy_diff > 0.40 and not has_matching_tag:
            base_score -= 0.15

        return round(max(0.0, min(1.0, base_score)), 3)

    # -------------------------------------------------------------------------
    # Transition Management (Intelligent Decision Engine)
    # -------------------------------------------------------------------------

    async def evaluate_transition(
        self,
        current_mood: str,
        mood_confidence: float = 0.85,
        mood_stability: float = 5.0,  # stable_for_seconds
        is_stable: bool = True,
        current_track_progress: Optional[float] = None,
        current_track_compatibility: Optional[float] = None,
        user_interaction: Optional[Dict[str, Any]] = None,
        recent_transitions: Optional[List[float]] = None,
        auto_execute: bool = True
    ) -> TransitionDecisionResult:
        """
        Decides whether to transition playback based on:
        - current mood
        - mood confidence
        - mood stability
        - current track progress
        - current track compatibility
        - user interaction
        - recent transitions (cooldown)
        - Jev bounded decision

        IMPORTANT: Mood changes must NOT immediately change the song!
        """
        current_state = self.provider.get_playback_state()
        current_track = current_state.current_track

        # 1. No track currently active -> start initial playback
        if not current_track:
            next_trk = self.queue[0] if self.queue else None
            executed = False
            if auto_execute and self.queue:
                next_trk = await self.next_track(reason="initial_playback")
                executed = True
            return TransitionDecisionResult(
                action="transition",
                reason="No track currently active. Starting playback.",
                current_track=None,
                next_track=next_trk,
                compatibility_score=0.0,
                is_compatible=False,
                transition_executed=executed
            )

        # 2. User Interaction: Manual pause check
        is_manually_paused = self.manual_pause or (
            user_interaction and user_interaction.get("manual_pause", False)
        ) or not current_state.is_playing

        if is_manually_paused:
            logger.info("Transition evaluation: manual pause active; holding current song.")
            return TransitionDecisionResult(
                action="continue",
                reason="Manual pause active; automatic transition suppressed.",
                current_track=current_track,
                next_track=None,
                compatibility_score=1.0,
                is_compatible=True,
                transition_executed=False
            )

        # 3. Mood Stability Check: Unstable mood MUST NOT change song
        min_stable_duration = getattr(settings, "MOOD_MIN_STABLE_DURATION", 3.0)
        confidence_threshold = getattr(settings, "MOOD_CONFIDENCE_THRESHOLD", 0.60)

        if not is_stable or mood_stability < min_stable_duration or mood_confidence < confidence_threshold:
            reason = (
                f"Mood is unstable (stable for {mood_stability:.1f}s < {min_stable_duration:.1f}s threshold, "
                f"confidence={mood_confidence:.2f} vs {confidence_threshold:.2f}). Holding current song."
            )
            logger.info(f"Transition evaluation: {reason}")
            return TransitionDecisionResult(
                action="continue",
                reason=reason,
                current_track=current_track,
                next_track=None,
                compatibility_score=1.0,
                is_compatible=True,
                transition_executed=False
            )

        # 4. Transition Cooldown Check: Avoid frequent switching / thrashing
        now = time.time()
        cooldown_duration = getattr(settings, "TRANSITION_COOLDOWN_SECONDS", 30.0)
        elapsed_since_last = now - self.last_transition_timestamp
        cooldown_remaining = max(0.0, cooldown_duration - elapsed_since_last)

        if cooldown_remaining > 0.0:
            reason = (
                f"In transition cooldown ({cooldown_remaining:.1f}s remaining of {cooldown_duration:.0f}s); "
                "preventing frequent switching."
            )
            logger.info(f"Transition evaluation: {reason}")
            return TransitionDecisionResult(
                action="continue",
                reason=reason,
                current_track=current_track,
                next_track=None,
                compatibility_score=1.0,
                is_compatible=True,
                cooldown_remaining_seconds=round(cooldown_remaining, 1),
                transition_executed=False
            )

        # 5. Track Compatibility Check
        comp_threshold = getattr(settings, "COMPATIBILITY_THRESHOLD", 0.55)
        if current_track_compatibility is not None:
            comp_score = current_track_compatibility
        else:
            comp_score = self.calculate_compatibility(current_track, current_mood)

        is_compatible = comp_score >= comp_threshold

        # If current song is still compatible with the new mood: CONTINUE
        if is_compatible:
            reason = (
                f"Current song '{current_track.title}' is still compatible with mood '{current_mood}' "
                f"(compatibility score {comp_score:.2f} >= {comp_threshold:.2f}). Continuing playback."
            )
            logger.info(f"Transition evaluation: {reason}")
            return TransitionDecisionResult(
                action="continue",
                reason=reason,
                current_track=current_track,
                next_track=None,
                compatibility_score=comp_score,
                is_compatible=True,
                transition_executed=False
            )

        # 6. Current Track Progress Check
        progress = current_track_progress if current_track_progress is not None else current_state.position_seconds
        duration = float(current_track.duration_seconds)
        play_ratio = progress / max(1.0, duration)
        min_play_sec = getattr(settings, "MIN_PLAY_SECONDS_BEFORE_TRANSITION", 30)
        force_ratio = getattr(settings, "FORCE_TRANSITION_PLAY_RATIO", 0.85)

        # Song is incompatible, but has it played enough unless strongly discordant?
        strongly_incompatible = comp_score < 0.40
        if progress < min_play_sec and play_ratio < force_ratio and not strongly_incompatible:
            reason = (
                f"Current song is incompatible ({comp_score:.2f}), but progress is young "
                f"({progress:.0f}s < {min_play_sec}s min threshold). Holding current song."
            )
            logger.info(f"Transition evaluation: {reason}")
            return TransitionDecisionResult(
                action="continue",
                reason=reason,
                current_track=current_track,
                next_track=None,
                compatibility_score=comp_score,
                is_compatible=False,
                transition_executed=False
            )

        # 7. Bounded Jev Transition Decision
        recent_skips_count = len([t for t in self.recent_transitions if (now - t) < 300])
        jev_state = {
            "smoothed_mood": current_mood,
            "mood_confidence": mood_confidence,
            "current_song": {
                "id": current_track.id,
                "title": current_track.title,
                "genre": current_track.profile.genre,
                "energy": current_track.profile.energy,
                "seconds_played": progress,
                "duration": duration
            },
            "seconds_played": progress,
            "recent_skips": recent_skips_count
        }

        jev_bundle = self.jev.decide(jev_state)
        jev_transition_choice = getattr(jev_bundle.transition, "value", "continue")

        if jev_transition_choice == "continue":
            return TransitionDecisionResult(
                action="continue",
                reason="Jev decision layer determined to continue current playback.",
                current_track=current_track,
                next_track=None,
                compatibility_score=comp_score,
                is_compatible=is_compatible,
                jev_decision=jev_transition_choice,
                transition_executed=False
            )

        if jev_transition_choice == "retrieve_new_candidates":
            await self.replenish_queue(target_mood=current_mood)
            return TransitionDecisionResult(
                action="replenish_queue",
                reason="Jev decision: retrieved new candidates for queue replenishment.",
                current_track=current_track,
                next_track=self.queue[0] if self.queue else None,
                compatibility_score=comp_score,
                is_compatible=is_compatible,
                jev_decision=jev_transition_choice,
                transition_executed=False
            )

        # 8. All conditions met: Mood stable, cooldown elapsed, song strongly incompatible, Jev confirms transition
        next_trk = self.queue[0] if self.queue else None
        executed = False
        if auto_execute:
            next_trk = await self.next_track(reason=f"mood_transition_{current_mood}")
            executed = True

        reason = (
            f"Transition approved: mood '{current_mood}' remained stable ({mood_stability:.1f}s), "
            f"and current song '{current_track.title}' is strongly incompatible (score={comp_score:.2f})."
        )
        logger.info(f"Transition evaluation: {reason}")
        return TransitionDecisionResult(
            action="transition",
            reason=reason,
            current_track=current_track,
            next_track=next_trk,
            compatibility_score=comp_score,
            is_compatible=False,
            jev_decision=jev_transition_choice,
            transition_executed=executed
        )

    # -------------------------------------------------------------------------
    # State Helpers
    # -------------------------------------------------------------------------

    def get_playback_state(self) -> PlaybackState:
        """Returns current playback state enriched with queue and manual_pause."""
        provider_state = self.provider.get_playback_state()
        return self._enrich_playback_state(provider_state)

    def _enrich_playback_state(self, state: PlaybackState) -> PlaybackState:
        """Enriches the provider PlaybackState with queue and playback manager metadata."""
        return PlaybackState(
            current_track=state.current_track,
            is_playing=state.is_playing,
            position_seconds=state.position_seconds,
            volume=state.volume,
            repeat_mode=state.repeat_mode,
            shuffle=state.shuffle,
            queue=list(self.queue),
            manual_pause=self.manual_pause,
            last_transition_timestamp=self.last_transition_timestamp
        )

    def _update_transition_time(self):
        """Records a transition timestamp and cleans old transition records."""
        now = time.time()
        self.last_transition_timestamp = now
        self.recent_transitions.append(now)
        # Keep only transitions within the last 10 minutes
        self.recent_transitions = [t for t in self.recent_transitions if (now - t) < 600]

    def _record_user_action(self, action: str, details: Optional[Dict[str, Any]] = None):
        """Logs user interactions for observability and state tracking."""
        record = {
            "action": action,
            "timestamp": time.time(),
            "details": details or {}
        }
        self.user_interactions.append(record)
        if len(self.user_interactions) > 50:
            self.user_interactions.pop(0)


# Global singleton instance
playback_manager = PlaybackManager()
