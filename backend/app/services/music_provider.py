"""Music Provider Layer (Phase 7).
Defines the abstract MusicProvider interface, the metadata-driven LocalMusicProvider,
and a provider registry allowing future verified third-party providers.

ARCHITECTURE & CONSTRAINTS:
1. Recommendation engine is decoupled from file paths and disk folder structures.
2. Local music is organized purely using structured metadata:
   {
     "id": "...",
     "title": "...",
     "artist": "...",
     "genre": "...",
     "energy": 0.7,
     "valence": 0.8,
     "tempo": 0.75,
     "mood_tags": ["positive", "energetic"]
   }
3. Third-party providers (Spotify, etc.) are NOT integrated until API, authentication,
   and usage constraints are officially verified.
"""
import os
import json
import math
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type

from ..config import settings
from ..schemas.music import Track, MusicProfile, PlaybackState

logger = logging.getLogger("moodtune.music_provider")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "data")
METADATA_FILE = os.path.join(DATA_DIR, "tracks_metadata.json")


class MusicProvider(ABC):
    """Abstract interface for all music providers."""

    @abstractmethod
    async def search(
        self,
        query: Optional[str] = None,
        genre: Optional[str] = None,
        min_energy: Optional[float] = None,
        max_energy: Optional[float] = None,
        limit: int = 10
    ) -> List[Track]:
        """Searches catalog by query, genre, or energy ranges."""
        pass

    @abstractmethod
    async def get_track(self, track_id: str) -> Optional[Track]:
        """Retrieves a single track by unique ID."""
        pass

    @abstractmethod
    async def get_recommendations(
        self,
        target_profile: Optional[MusicProfile] = None,
        mood: Optional[str] = None,
        limit: int = 10
    ) -> List[Track]:
        """Retrieves candidate recommendations matching target profile or mood."""
        pass

    @abstractmethod
    async def play(self, track_id: str, position_seconds: float = 0.0) -> PlaybackState:
        """Starts or updates playback of the specified track."""
        pass

    @abstractmethod
    async def pause(self) -> PlaybackState:
        """Pauses active playback."""
        pass

    @abstractmethod
    async def resume(self) -> PlaybackState:
        """Resumes active playback."""
        pass

    @abstractmethod
    async def skip(
        self,
        current_track_id: Optional[str] = None,
        seconds_played: float = 0.0
    ) -> PlaybackState:
        """Skips the current track and advances to the next track."""
        pass

    @abstractmethod
    def get_playback_state(self) -> PlaybackState:
        """Returns the current playback state."""
        pass

    # Compatibility aliases
    async def search_tracks(self, *args, **kwargs) -> List[Track]:
        return await self.search(*args, **kwargs)

    async def get_candidates_for_profile(self, target_profile: MusicProfile, limit: int = 10) -> List[Track]:
        return await self.get_recommendations(target_profile=target_profile, limit=limit)


# BaseMusicProvider alias for backward compatibility
BaseMusicProvider = MusicProvider


class LocalMusicProvider(MusicProvider):
    """
    Metadata-driven Local Music Provider.
    Organizes tracks purely using audio and emotional metadata, decoupled from file paths.
    """

    def __init__(self, metadata_path: Optional[str] = None):
        self.metadata_path = metadata_path or METADATA_FILE
        self._catalog: List[Track] = []
        self._playback_state = PlaybackState()
        self._load_catalog()

    def _load_catalog(self):
        """Loads track catalog from metadata JSON or default fallback."""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tracks = []
                for item in data:
                    profile = MusicProfile(
                        genre=item.get("genre", "lofi"),
                        energy=float(item.get("energy", 0.5)),
                        valence=float(item.get("valence", 0.5)),
                        tempo=float(item.get("tempo", 0.5)),
                        danceability=float(item.get("danceability", 0.5)),
                        instrumental=float(item.get("instrumental", 0.0)),
                        mood_tags=item.get("mood_tags", [])
                    )
                    track = Track(
                        id=item["id"],
                        title=item["title"],
                        artist=item["artist"],
                        album=item.get("album", "MoodTune Curated"),
                        duration_seconds=int(item.get("duration_seconds", 180)),
                        audio_url=item.get("audio_url", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"),
                        cover_art_url=item.get("cover_art_url", "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400&q=80"),
                        profile=profile,
                        provider="local"
                    )
                    tracks.append(track)
                self._catalog = tracks
                logger.info(f"Loaded {len(self._catalog)} tracks from metadata at {self.metadata_path}")
                return
            except Exception as e:
                logger.error(f"Error loading tracks metadata from {self.metadata_path}: {e}")

        # Fallback default catalog
        self._catalog = self._build_default_catalog()

    def _build_default_catalog(self) -> List[Track]:
        return [
            Track(
                id="trk_upbeat_01",
                title="Chaiyya Chaiyya",
                artist="Sukhwinder Singh, Sapna Awasthi",
                album="Dil Se (A.R. Rahman)",
                duration_seconds=210,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                cover_art_url="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=400&q=80",
                profile=MusicProfile(
                    genre="synthwave",
                    energy=0.88,
                    valence=0.82,
                    tempo=0.75,
                    danceability=0.85,
                    instrumental=0.0,
                    mood_tags=["positive", "energetic", "celebration", "classic_bollywood"]
                )
            ),
            Track(
                id="trk_upbeat_02",
                title="Gallan Goodiyaan",
                artist="Shankar Mahadevan, Yashita Sharma",
                album="Dil Dhadakne Do",
                duration_seconds=185,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
                cover_art_url="https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&q=80",
                profile=MusicProfile(
                    genre="upbeat_pop",
                    energy=0.78,
                    valence=0.92,
                    tempo=0.70,
                    danceability=0.80,
                    instrumental=0.0,
                    mood_tags=["positive", "uplifting", "party", "joy"]
                )
            ),
            Track(
                id="trk_upbeat_03",
                title="Ghungroo",
                artist="Arijit Singh, Shilpa Rao, Vishal-Shekhar",
                album="War",
                duration_seconds=198,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
                cover_art_url="https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=400&q=80",
                profile=MusicProfile(
                    genre="synthwave",
                    energy=0.92,
                    valence=0.75,
                    tempo=0.82,
                    danceability=0.90,
                    instrumental=0.0,
                    mood_tags=["energetic", "dance", "modern_bollywood", "vibrant"]
                )
            ),
            Track(
                id="trk_calm_01",
                title="Kun Faya Kun",
                artist="A.R. Rahman, Mohit Chauhan, Javed Ali",
                album="Rockstar",
                duration_seconds=240,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
                cover_art_url="https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=400&q=80",
                profile=MusicProfile(
                    genre="ambient",
                    energy=0.22,
                    valence=0.65,
                    tempo=0.30,
                    danceability=0.20,
                    instrumental=0.0,
                    mood_tags=["calm", "relaxing", "sufi", "peace", "spiritual"]
                )
            ),
            Track(
                id="trk_calm_02",
                title="Iktara",
                artist="Amit Trivedi, Kavita Seth",
                album="Wake Up Sid",
                duration_seconds=172,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
                cover_art_url="https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=400&q=80",
                profile=MusicProfile(
                    genre="lofi",
                    energy=0.35,
                    valence=0.60,
                    tempo=0.42,
                    danceability=0.50,
                    instrumental=0.0,
                    mood_tags=["calm", "study", "cozy", "mellow"]
                )
            ),
            Track(
                id="trk_neutral_01",
                title="Safarnama",
                artist="Lucky Ali, A.R. Rahman",
                album="Tamasha",
                duration_seconds=195,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3",
                cover_art_url="https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=400&q=80",
                profile=MusicProfile(
                    genre="lofi",
                    energy=0.45,
                    valence=0.50,
                    tempo=0.45,
                    danceability=0.50,
                    instrumental=0.0,
                    mood_tags=["neutral", "focus", "work", "balance"]
                )
            ),
            Track(
                id="trk_reflective_01",
                title="Kabira",
                artist="Tochi Raina, Rekha Bhardwaj, Pritam",
                album="Yeh Jawaani Hai Deewani",
                duration_seconds=215,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3",
                cover_art_url="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80",
                profile=MusicProfile(
                    genre="indie_folk",
                    energy=0.38,
                    valence=0.45,
                    tempo=0.42,
                    danceability=0.35,
                    instrumental=0.0,
                    mood_tags=["reflective", "folk", "deep", "gentle", "soulful"]
                )
            ),
            Track(
                id="trk_low_01",
                title="Phir Le Aya Dil",
                artist="Arijit Singh, Pritam",
                album="Barfi!",
                duration_seconds=260,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-11.mp3",
                cover_art_url="https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&q=80",
                profile=MusicProfile(
                    genre="ambient",
                    energy=0.20,
                    valence=0.30,
                    tempo=0.28,
                    danceability=0.18,
                    instrumental=0.0,
                    mood_tags=["low_energy", "comfort", "soothing", "ghazal", "emotional"]
                )
            ),
            Track(
                id="trk_tense_01",
                title="Maula Mere Maula",
                artist="Roop Kumar Rathod, Mithoon",
                album="Anwar",
                duration_seconds=280,
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3",
                cover_art_url="https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=400&q=80",
                profile=MusicProfile(
                    genre="meditation",
                    energy=0.18,
                    valence=0.50,
                    tempo=0.22,
                    danceability=0.12,
                    instrumental=0.0,
                    mood_tags=["tense", "soothing", "de-stress", "unwind", "breathe"]
                )
            )
        ]

    async def get_track(self, track_id: str) -> Optional[Track]:
        for track in self._catalog:
            if track.id == track_id:
                return track
        return None

    async def search(
        self,
        query: Optional[str] = None,
        genre: Optional[str] = None,
        min_energy: Optional[float] = None,
        max_energy: Optional[float] = None,
        limit: int = 10
    ) -> List[Track]:
        results = self._catalog

        if query:
            q = query.lower()
            results = [
                t for t in results
                if q in t.title.lower() or q in t.artist.lower() or any(q in tag.lower() for tag in t.profile.mood_tags)
            ]

        if genre:
            g = genre.lower()
            results = [t for t in results if t.profile.genre.lower() == g]

        if min_energy is not None:
            results = [t for t in results if t.profile.energy >= min_energy]

        if max_energy is not None:
            results = [t for t in results if t.profile.energy <= max_energy]

        return results[:limit]

    async def get_recommendations(
        self,
        target_profile: Optional[MusicProfile] = None,
        mood: Optional[str] = None,
        limit: int = 10
    ) -> List[Track]:
        """
        Retrieves candidate tracks ranked by Euclidean distance to target audio profile
        or by mood tags.
        """
        if target_profile is None:
            target_energy = 0.5
            target_valence = 0.5
            target_tempo = 0.5
            target_dance = 0.5
            target_genre = ""
        else:
            target_energy = target_profile.energy
            target_valence = target_profile.valence
            target_tempo = target_profile.tempo
            target_dance = target_profile.danceability
            target_genre = target_profile.genre.lower()

        scored_candidates = []
        for track in self._catalog:
            p = track.profile
            energy_diff = p.energy - target_energy
            valence_diff = p.valence - target_valence
            tempo_diff = p.tempo - target_tempo
            dance_diff = p.danceability - target_dance
            genre_bonus = -0.25 if target_genre and p.genre.lower() == target_genre else 0.0

            mood_bonus = 0.0
            if mood and any(mood.lower() in tag.lower() for tag in p.mood_tags):
                mood_bonus = -0.30

            distance = math.sqrt(
                (energy_diff ** 2) * 1.5 +
                (valence_diff ** 2) * 1.2 +
                (tempo_diff ** 2) * 0.8 +
                (dance_diff ** 2) * 0.5
            ) + genre_bonus + mood_bonus

            scored_candidates.append((track, distance))

        scored_candidates.sort(key=lambda item: item[1])
        return [item[0] for item in scored_candidates[:limit]]

    async def play(self, track_id: str, position_seconds: float = 0.0) -> PlaybackState:
        track = await self.get_track(track_id)
        if track:
            self._playback_state.current_track = track
            self._playback_state.is_playing = True
            self._playback_state.position_seconds = max(0.0, position_seconds)
            logger.info(f"Playback started: {track.title} by {track.artist} at {self._playback_state.position_seconds}s")
        else:
            logger.warning(f"Track {track_id} not found in catalog for playback")
        return self._playback_state

    async def pause(self) -> PlaybackState:
        self._playback_state.is_playing = False
        logger.info(f"Playback paused at {self._playback_state.position_seconds}s")
        return self._playback_state

    async def resume(self) -> PlaybackState:
        if self._playback_state.current_track:
            self._playback_state.is_playing = True
            logger.info(f"Playback resumed: {self._playback_state.current_track.title}")
        return self._playback_state

    async def skip(
        self,
        current_track_id: Optional[str] = None,
        seconds_played: float = 0.0
    ) -> PlaybackState:
        logger.info(f"Skipping track {current_track_id} after {seconds_played}s")
        # Find next candidate in catalog that is different from current
        next_track = None
        for track in self._catalog:
            if current_track_id is None or track.id != current_track_id:
                next_track = track
                break
        if next_track:
            self._playback_state.current_track = next_track
            self._playback_state.is_playing = True
            self._playback_state.position_seconds = 0.0
        return self._playback_state

    def get_playback_state(self) -> PlaybackState:
        return self._playback_state


class UnverifiedThirdPartyMusicProvider(MusicProvider):
    """
    Template for future third-party providers (Spotify, YouTube Music, etc.).
    Adheres strictly to the architectural constraint:
    Never integrate until third-party API, authentication, and usage rules are officially verified.
    """
    def __init__(self, provider_name: str = "spotify"):
        self.provider_name = provider_name

    async def search(self, *args, **kwargs) -> List[Track]:
        raise NotImplementedError(
            f"{self.provider_name.capitalize()} provider API and authentication rules have not yet been verified. "
            "Use LocalMusicProvider."
        )

    async def get_track(self, track_id: str) -> Optional[Track]:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    async def get_recommendations(self, *args, **kwargs) -> List[Track]:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    async def play(self, *args, **kwargs) -> PlaybackState:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    async def pause(self) -> PlaybackState:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    async def resume(self) -> PlaybackState:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    async def skip(self, *args, **kwargs) -> PlaybackState:
        raise NotImplementedError(f"{self.provider_name.capitalize()} provider not verified.")

    def get_playback_state(self) -> PlaybackState:
        return PlaybackState()


class MusicProviderRegistry:
    """Registry allowing future providers without modifying recommendation logic."""

    def __init__(self):
        self._providers: Dict[str, Type[MusicProvider]] = {
            "local": LocalMusicProvider,
            "spotify_unverified": UnverifiedThirdPartyMusicProvider
        }
        self._active_instances: Dict[str, MusicProvider] = {}

    def register(self, name: str, provider_cls: Type[MusicProvider]):
        self._providers[name.lower()] = provider_cls

    def get_provider(self, name: Optional[str] = None) -> MusicProvider:
        provider_name = (name or getattr(settings, "MUSIC_PROVIDER_TYPE", "local")).lower()
        if provider_name not in self._active_instances:
            provider_cls = self._providers.get(provider_name, LocalMusicProvider)
            self._active_instances[provider_name] = provider_cls()
        return self._active_instances[provider_name]


provider_registry = MusicProviderRegistry()


def get_music_provider() -> MusicProvider:
    return provider_registry.get_provider()


music_provider = get_music_provider()
