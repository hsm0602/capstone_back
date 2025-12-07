from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, TIMESTAMP, Boolean, event
from sqlalchemy.orm import relationship
from .database import Base
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    user_goal = Column(String(255))
    recent_state_height = Column(Float)
    recent_state_weight = Column(Float)
    recent_state_pbf = Column(Float)
    goal_state_height = Column(Float)
    goal_state_weight = Column(Float)
    goal_state_pbf = Column(Float)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    exercise_records = relationship("ExerciseRecord", back_populates="user")
    body_compositions = relationship("BodyComposition", back_populates="user")
    weight_histories = relationship("WeightHistory", back_populates="user")
    pbf_histories = relationship("PbfHistory", back_populates="user")
   

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    muscle_group = Column(String(255))

    exercise_records = relationship("ExerciseRecord", back_populates="exercise")

class ExerciseRecord(Base):
    __tablename__ = "exercise_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    date = Column(Date)
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float)
    exercise_time = Column(Integer)  # seconds
    rest_time = Column(Integer)      # seconds
    is_completed = Column(Boolean, default=False)

    user = relationship("User", back_populates="exercise_records")
    exercise = relationship("Exercise", back_populates="exercise_records")

class BodyComposition(Base):
    __tablename__ = "body_compositions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measured_at = Column(Date)
    weight = Column(Float)
    muscle_mass = Column(Float)
    body_fat_percentage = Column(Float)
    bmi = Column(Float)

    user = relationship("User", back_populates="body_compositions")

class WeightHistory(Base):
    __tablename__ = "weight_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    weight = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="weight_histories")

@event.listens_for(User.recent_state_weight, 'set')
def on_weight_change(target, value, oldvalue, initiator):
    # 값이 변경되었을 때만 기록 (초기 설정 포함)
    if value is not None and value != oldvalue:
        target.weight_histories.append(WeightHistory(weight=value))

class PbfHistory(Base):
    __tablename__ = "pbf_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body_fat_percentage = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="pbf_histories")

@event.listens_for(User.recent_state_pbf, 'set')
def on_pbf_change(target, value, oldvalue, initiator):
    # 값이 변경되었을 때만 기록
    if value is not None and value != oldvalue:
        target.pbf_histories.append(PbfHistory(body_fat_percentage=value))
