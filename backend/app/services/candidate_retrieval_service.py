"""Candidate Retrieval Service (Phase 6: Music Recommendation Engine).
Retrieves candidate tracks from the catalog / provider based on target music profile,
exploration strategy, and user preference filters (e.g. disliked genres).
"""
import logging
from typing import List, Optional, Set

from ..schemas.music import Track, MusicProfile, UserPreferenceSchema
from .music_provider import music_provider, BaseMusicProvider

logger = logging.getLogger("moodtune.candidate_retrieval")


class CandidateRetrievalService:
    def __init__(self, provider: Optional[BaseMusicProvider] = None):
        self.provider = provider or music_provider

    async def retrieve_candidates(
        self,
        target_profile: MusicProfile,
        user_preferences: Optional[UserPreferenceSchema] = None,
        is_exploration: bool = False,
        limit: int = 15
    ) -> List[Track]:
        """
        Retrieves a candidate pool of tracks matching target profile attributes
        while filtering out disliked genres and injecting diversity.
        """
        disliked_genres: Set[str] = set()
        if user_preferences and user_preferences.disliked_genres:
            disliked_genres = {g.lower() for g in user_preferences.disliked_genres}

        # 1. Fetch primary acoustic candidates from provider
        base_limit = max(10, limit * 2)
        raw_candidates = await self.provider.get_candidates_for_profile(
            target_profile=target_profile,
            limit=base_limit
        )

        # 2. Filter out disliked genres
        filtered = [
            t for t in raw_candidates
            if t.profile.genre.lower() not in disliked_genres
        ]

        # 3. If exploration is requested or candidate pool is small, inject diversity tracks
        if is_exploration or len(filtered) < limit:
            # Query complementary genres or alternative preferred genres
            alt_candidates = await self.provider.search_tracks(
                min_energy=max(0.0, target_profile.energy - 0.25),
                max_energy=min(1.0, target_profile.energy + 0.25),
                limit=10
            )
            existing_ids = {t.id for t in filtered}
            for alt in alt_candidates:
                if alt.id not in existing_ids and alt.profile.genre.lower() not in disliked_genres:
                    filtered.append(alt)
                    existing_ids.add(alt.id)

        logger.debug(f"Retrieved {len(filtered)} candidate tracks for profile genre={target_profile.genre}")
        return filtered[:limit]


candidate_retrieval_service = CandidateRetrievalService()
