"""Database connection and initialization."""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
import datetime
from sqlalchemy import select, delete
from .models import Base, User, UserPreference, MoodSession, MoodObservation

logger = logging.getLogger("moodtune.database")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"timeout": 30}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    """FastAPI dependency for obtaining async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def purge_expired_sessions(session: AsyncSession, retention_days: int = 7) -> int:
    """
    Enforces privacy data minimization and storage limitation policy (GDPR/CCPA compliant).
    Permanently deletes mood observations and sessions older than retention_days.
    """
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
    try:
        stmt = delete(MoodSession).where(MoodSession.started_at < cutoff)
        result = await session.execute(stmt)
        await session.commit()
        deleted_count = result.rowcount or 0
        if deleted_count > 0:
            logger.info(f"Purged {deleted_count} expired mood session(s) older than {retention_days} days.")
        return deleted_count
    except Exception as e:
        logger.error(f"Error purging expired mood sessions: {e}")
        await session.rollback()
        return 0


async def init_db():
    """Initializes tables, seeds default user/preferences, and enforces data minimization."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Ensure default user and preferences exist
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == "default_user"))
        user = res.scalar_one_or_none()
        if not user:
            user = User(id="default_user", username="MoodTune Listener")
            session.add(user)
            pref = UserPreference(
                user_id="default_user",
                preferred_genres=["lofi", "ambient", "synthwave", "classical"],
                preferred_energy_bias=0.5,
                transition_sensitivity=0.6,
                mood_genre_affinity={
                    "positive": {"upbeat_pop": 0.9, "synthwave": 0.8},
                    "calm": {"ambient": 0.9, "lofi": 0.8},
                    "energetic": {"synthwave": 0.95, "upbeat_pop": 0.85},
                    "neutral": {"lofi": 0.85, "indie_folk": 0.75},
                    "reflective": {"indie_folk": 0.9, "classical": 0.85},
                    "low_energy": {"ambient": 0.8, "lofi": 0.85},
                    "tense": {"ambient": 0.95, "meditation": 0.9}
                }
            )
            session.add(pref)
            await session.commit()
            logger.info("Initialized default user and preference profile.")

        # Enforce automated privacy retention cleanup on startup
        await purge_expired_sessions(session, retention_days=settings.RETENTION_DAYS_MOOD_HISTORY)
