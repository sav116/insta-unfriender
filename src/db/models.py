from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    tracked_accounts = relationship("TrackedAccount", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, chat_id={self.chat_id}, username={self.username})>"


class TrackedAccount(Base):
    __tablename__ = "tracked_accounts"
    
    id = Column(Integer, primary_key=True)
    instagram_username = Column(String, nullable=False)
    instagram_user_id = Column(String, nullable=True)
    is_private = Column(Boolean, default=False)
    follow_requested = Column(Boolean, default=False)
    last_check = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tracked_accounts")
    followers = relationship("Follower", back_populates="tracked_account", cascade="all, delete-orphan")
    unfollowers = relationship("Unfollower", back_populates="tracked_account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TrackedAccount(id={self.id}, instagram_username={self.instagram_username})>"


class Follower(Base):
    __tablename__ = "followers"
    
    id = Column(Integer, primary_key=True)
    instagram_user_id = Column(String, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    tracked_account_id = Column(Integer, ForeignKey("tracked_accounts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    tracked_account = relationship("TrackedAccount", back_populates="followers")
    
    def __repr__(self):
        return f"<Follower(id={self.id}, username={self.username})>"


class Unfollower(Base):
    __tablename__ = "unfollowers"
    
    id = Column(Integer, primary_key=True)
    instagram_user_id = Column(String, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    tracked_account_id = Column(Integer, ForeignKey("tracked_accounts.id"), nullable=False)
    unfollowed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    tracked_account = relationship("TrackedAccount", back_populates="unfollowers")
    
    def __repr__(self):
        return f"<Unfollower(id={self.id}, username={self.username})>"


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<Settings(key={self.key}, value={self.value})>"


# Initialize database
def init_db():
    database_url = os.getenv("DATABASE_URL", "sqlite:///bot_data.db")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine 