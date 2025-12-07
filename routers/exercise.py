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

router = APIRouter(prefix="/exercise", tags=["exercise"])

class ExerciseRecordOut(BaseModel):
    record_id: int          # ExerciseRecord.id (세트 ID)
    exercise_id: int        # 운동 ID
    exercise_name: str      # Exercise.name
    date: date
    weight: float
    reps: int
    is_completed: bool

    class Config:
        orm_mode = True

@router.get("/records", response_model=List[ExerciseRecordOut])
def get_exercise_records(
    user_id: int, 
    date: date,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_user)
):

    records = (
        db.query(ExerciseRecord)
        .join(Exercise)
        .filter(
            ExerciseRecord.user_id == current_user.id,
            ExerciseRecord.date == date
        )
        .all()
    )

    return [
        ExerciseRecordOut(
            record_id=r.id,
            exercise_id=r.exercise_id,
            exercise_name=r.exercise.name,
            date=r.date,
            weight=r.weight,
            reps=r.reps,
            is_completed=r.is_completed
        )
        for r in records
    ]

class BodyCompositionPointDto(BaseModel):
    measured_at: date
    weight: Optional[float] = None
    body_fat_percentage: Optional[float] = None

class WeeklyBodyCompositionResponse(BaseModel):
    points: List[BodyCompositionPointDto]

@router.get("/body_composition/weekly", response_model=WeeklyBodyCompositionResponse)
def get_weekly_body_composition(
    user_id: int,
    metric: str,  # "weight" or "body_fat"
    days: int = 7,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_user)
):
    from db_work.models import WeightHistory, BodyComposition, PbfHistory
    
    end_date = date.today()
    start_date = end_date - datetime.timedelta(days=days-1)

    points = []

    if metric == "weight":
        # WeightHistory 테이블 조회
        histories = (
            db.query(WeightHistory)
            .filter(
                WeightHistory.user_id == current_user.id,
                WeightHistory.created_at >= start_date,
                WeightHistory.created_at <= datetime.datetime.now() # 오늘까지
            )
            .order_by(WeightHistory.created_at.asc())
            .all()
        )
        
        daily_map = {}
        for h in histories:
            d_key = h.created_at.date()
            daily_map[d_key] = h.weight
            
        sorted_dates = sorted(daily_map.keys())
        for d in sorted_dates:
            points.append(BodyCompositionPointDto(
                measured_at=d,
                weight=daily_map[d],
                body_fat_percentage=None
            ))

    elif metric == "body_fat":
        # PbfHistory 테이블 조회
        histories = (
            db.query(PbfHistory)
            .filter(
                PbfHistory.user_id == current_user.id,
                PbfHistory.created_at >= start_date,
                PbfHistory.created_at <= datetime.datetime.now()
            )
            .order_by(PbfHistory.created_at.asc())
            .all()
        )
        
        daily_map = {}
        for h in histories:
            d_key = h.created_at.date()
            daily_map[d_key] = h.body_fat_percentage
            
        sorted_dates = sorted(daily_map.keys())
        for d in sorted_dates:
            points.append(BodyCompositionPointDto(
                measured_at=d,
                weight=None,
                body_fat_percentage=daily_map[d]
            ))

    return WeeklyBodyCompositionResponse(points=points)

class ExerciseRecordUpdate(BaseModel):
    exercise_time: Optional[int] = None
    rest_time: Optional[int] = None
    is_completed: Optional[bool] = None

@router.patch("/records/{record_id}")
def update_exercise_record(
    record_id: int,
    update_data: ExerciseRecordUpdate,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_user)
):
    # 수정할 대상 레코드 찾기
    record = db.query(ExerciseRecord).filter(ExerciseRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Exercise record not found")
        
    # 권한 확인 (본인의 기록인지) - 선택 사항이지만 권장됨
    if record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this record")

    # 전달된 필드만 업데이트
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    return {"message": "Exercise record updated successfully", "updated_record": update_fields}
