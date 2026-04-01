from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
# from database import Base
from .database import Base  # Add the dot here

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    videos = relationship("Video", back_populates="owner")
    alerts = relationship("Alert", back_populates="owner")

class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="pending")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="videos")
    detections = relationship("Detection", back_populates="video")

class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    timestamp_sec = Column(Float, nullable=False)
    object_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    bounding_box = Column(String, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    video = relationship("Video", back_populates="detections")
    alerts = relationship("Alert", back_populates="detection")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=True)
    alert_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="alerts")
    detection = relationship("Detection", back_populates="alerts")