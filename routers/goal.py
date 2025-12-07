import os, json, datetime, re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import select
from db_work.models import User, Exercise, ExerciseRecord # 당신의 프로젝트 구조에 맞게 import
from db_work import database
from datetime import date
from routers.auth import get_current_user

router = APIRouter(prefix="/goal", tags=["goal"])

@router.patch("/me")
def register_goal(
  user_id: int, 
  goal: str, 
  db: Session = Depends(database.get_db),
  current_user: User = Depends(get_current_user)
):
  user = db.query(User).filter(User.id == current_user.id).first()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  user.user_goal = goal
  db.commit()
  db.refresh(user)

  return {"message": "Goal updated", "goal": user.user_goal}

@router.patch("/recent_state")
def register_recent_state(
  user_id: int, 
  height: float, 
  weight: float, 
  pbf: float, 
  db: Session = Depends(database.get_db),
  current_user: User = Depends(get_current_user)
):
  user = db.query(User).filter(User.id == current_user.id).first()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  user.recent_state_height = height
  user.recent_state_weight = weight
  user.recent_state_pbf = pbf
  db.commit()
  db.refresh(user)

  return {"message": "Recent state updated"}

@router.patch("/goal_state")
def register_goal_state(
  user_id: int, 
  height: float, 
  weight: float, 
  pbf: float, 
  db: Session = Depends(database.get_db),
  current_user: User = Depends(get_current_user)
):
  user = db.query(User).filter(User.id == current_user.id).first()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  user.goal_state_height = height
  user.goal_state_weight = weight
  user.goal_state_pbf = pbf
  db.commit()
  db.refresh(user)

  return {"message": "Goal state updated"}