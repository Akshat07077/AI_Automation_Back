import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, password: str) -> User:
    """Create a new user with hashed password."""
    # Check if user already exists
    existing = await get_user_by_username(db, username)
    if existing:
        raise ValueError(f"User '{username}' already exists")
    
    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def verify_user_password(db: AsyncSession, username: str, password: str) -> bool:
    """Verify a user's password."""
    user = await get_user_by_username(db, username)
    if not user:
        return False
    return verify_password(password, user.password_hash)


async def get_all_users(db: AsyncSession) -> list[User]:
    """Get all users (without password hashes)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())
