"""SQLAlchemy ORM Entities for MoodTune AI."""
import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, default="User")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    sessions = relationship("MoodSession", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    playback_events = relationship("PlaybackEvent", back_populates="user", cascade="all, delete-orphan")


class MoodSession(Base):
    __tablename__ = "mood_sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    initial_mood = Column(String, nullable=True)
    final_mood = Column(String, nullable=True)
    total_frames = Column(Integer, default=0)

    user = relationship("User", back_populates="sessions")
    observations = relationship("MoodObservation", back_populates="session", cascade="all, delete-orphan")


class MoodObservation(Base):
    __tablename__ = "mood_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("mood_sessions.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Human-centered: Estimated mood, not true internal state
    estimated_mood = Column(String, index=True)
    confidence = Column(Float)
    emotion_probabilities = Column(JSON)  # Dict[str, float]
    is_stable = Column(Boolean, default=False)
    
    # Strict Privacy: RAW CAMERA FRAMES ARE NEVER STORED HERE!

    session = relationship("MoodSession", back_populates="observations")


class TrackEntity(Base):
    __tablename__ = "tracks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    artist = Column(String)
    album = Column(String)
    duration_seconds = Column(Integer)
    audio_url = Column(String)
    cover_art_url = Column(String)
    provider = Column(String, default="local")
    
    # Music profile attributes
    genre = Column(String, index=True)
    energy = Column(Float)
    valence = Column(Float)
    tempo = Column(Float)
    instrumental = Column(Boolean, default=False)
    danceability = Column(Float)
    mood_tags = Column(JSON)  # List[str]


class PlaybackEvent(Base):
    __tablename__ = "playback_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    track_id = Column(String, ForeignKey("tracks.id"), index=True)
    event_type = Column(String)  # play, pause, resume, skip, complete
    seconds_played = Column(Float, default=0.0)
    mood_at_event = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="playback_events")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, index=True)
    preferred_genres = Column(JSON, default=list)  # list of strings
    disliked_genres = Column(JSON, default=list)
    preferred_energy_bias = Column(Float, default=0.5)
    transition_sensitivity = Column(Float, default=0.6)
    auto_play_on_mood_shift = Column(Boolean, default=True)
    mood_genre_affinity = Column(JSON, default=dict)  # {"positive": {"pop": 0.8, ...}}
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class RecommendationEntity(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    estimated_mood = Column(String)
    strategy = Column(String)
    jev_confidence = Column(Float)
    suggested_track_ids = Column(JSON)  # List[str]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    feedback = relationship("RecommendationFeedback", back_populates="recommendation", cascade="all, delete-orphan")


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String, ForeignKey("recommendations.id"), index=True)
    track_id = Column(String, ForeignKey("tracks.id"))
    feedback_type = Column(String)  # like, dislike, skip, complete
    seconds_played = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    recommendation = relationship("RecommendationEntity", back_populates="feedback")
