from datetime import date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from .database import Base, engine, SessionLocal
from . import models

def get_today_kst():
    return datetime.now(ZoneInfo("Asia/Seoul")).date()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password1 = pwd_context.hash("1111")
password2 = pwd_context.hash("2222")
password3 = pwd_context.hash("3333")


def seed_data(session):
    # 1) 기본 사용자 (비번은 해시 권장: passlib[bcrypt] 등)
    #    예시로는 편의상 평문 → 실제 운영/공유 저장소에는 절대 평문 금지!
    users = [
        {
            "username": "admin1",
            "email": "admin1",
            "password": password1,  # 실제로는 해시필요. 해시완료.
            # created_at은 models에서 server_default=func.now()로 두면 자동
        },
        {
            "username": "admin2",
            "email": "admin2",
            "password": password2,
        },
        {
            "username": "admin3",
            "email": "admin3",
            "password": password3,
        },
    ]

    # 2) 기본 운동종목
    exercises = [
        {"name": "Squat", "description": "Barbell back squat", "muscle_group": "Legs"},
        {"name": "Push Up", "description": "", "muscle_group": "Chest"},
        {"name": "Pull Up", "description": "", "muscle_group": "Back"},
        {"name": "Shoulder Press", "description": "", "muscle_group": "Shoulder"},
        {"name": "Leg Raise", "description": "", "muscle_group": "abdominals"},
        {"name": "Dumbbell Deadlift", "description": "", "muscle_group": "Back"},
        {"name": "Crunch Floor", "description": "", "muscle_group": "abdominals"},
        {"name": "Elbow To Knee", "description": "", "muscle_group": "abdominals"},
        {"name": "Pike Pushup", "description": "", "muscle_group": "Shoulder"},
    ]

    # 중복 방지용 헬퍼
    def get_or_create(model, defaults=None, **kwargs):
        inst = session.query(model).filter_by(**kwargs).one_or_none()
        if inst:
            return inst, False
        params = dict(kwargs)
        if defaults:
            params.update(defaults)
        inst = model(**params)
        session.add(inst)
        return inst, True

    # 사용자 시드
    for u in users:
        get_or_create(models.User, **u)

    # 운동 시드
    for e in exercises:
        get_or_create(models.Exercise, **e)

    session.flush()

    # 3) ExerciseRecord 시드
    admin1 = session.query(models.User).filter_by(email="admin1").first()
    squat = session.query(models.Exercise).filter_by(name="Squat").first()
    push_up = session.query(models.Exercise).filter_by(name="Push Up").first()
    shoulder_press = session.query(models.Exercise).filter_by(name="Shoulder Press").first()
    dumbbell_deadlift = session.query(models.Exercise).filter_by(name="Dumbbell Deadlift").first()

    if admin1 and squat and push_up:
        # Squat 3 sets (1행에 1세트씩)
        for i in range(1, 4):
            session.add(models.ExerciseRecord(
                user_id=admin1.id,
                exercise_id=squat.id,
                date=get_today_kst(),
                sets=i,
                reps=5,
                weight=60.0,
                is_completed=False
            ))

        # Push Up 3 sets
        for i in range(1, 4):
            session.add(models.ExerciseRecord(
                user_id=admin1.id,
                exercise_id=push_up.id,
                date=get_today_kst(),
                sets=i,
                reps=5,
                weight=50.0,
                is_completed=False
            ))

        # Shoulder Press 3 sets
        for i in range(1, 4):
            session.add(models.ExerciseRecord(
                user_id=admin1.id,
                exercise_id=shoulder_press.id,
                date=get_today_kst(),
                sets=i,
                reps=5,
                weight=50.0,
                is_completed=False
            ))

        # Dumbbell Deadlift 3 sets
        for i in range(1, 4):
            session.add(models.ExerciseRecord(
                user_id=admin1.id,
                exercise_id=dumbbell_deadlift.id,
                date=get_today_kst(),
                sets=i,
                reps=5,
                weight=50.0,
                is_completed=False
            ))

    # 4) WeightHistory & PbfHistory 시드 (admin1, 2025-12-05 기준 7일치)
    # 그래프 변화를 잘 보여주기 위해 값을 크게 변동시킴
    import datetime
    base_date = datetime.date(2025, 12, 5)
    
    # 예시: 7일 전부터 하루씩 증가
    # 날짜: D-6, D-5, ..., D-0
    # 몸무게: 70 -> 72 -> 69 -> 73 -> 71 -> 68 -> 70 (들쑥날쑥)
    # 체지방: 20 -> 22 -> 19 -> 23 -> 21 -> 18 -> 20
    
    weights = [70.0, 72.5, 69.0, 73.0, 71.5, 68.0, 70.0]
    pbfs = [20.0, 22.5, 19.0, 23.0, 21.5, 18.0, 20.0]

    if admin1:
        for i in range(7):
            # 6일 전 ~ 0일 전(당일)
            delta = 6 - i
            target_date = base_date - datetime.timedelta(days=delta)
            
            # created_at은 datetime 타입이므로 시간까지 포함해서 생성
            # (여기서는 00:00:00으로 가정하거나 현재 시간 등 적절히)
            # models.TIMESTAMP 타입이므로 datetime 객체 필요
            dt_val = datetime.datetime.combine(target_date, datetime.time(9, 0, 0))

            # WeightHistory
            w_hist = models.WeightHistory(
                user_id=admin1.id,
                weight=weights[i],
                created_at=dt_val
            )
            session.add(w_hist)

            # PbfHistory
            p_hist = models.PbfHistory(
                user_id=admin1.id,
                body_fat_percentage=pbfs[i],
                created_at=dt_val
            )
            session.add(p_hist)

def reset_tables():
    # FK 제약 때문에 드롭/생성 전후로 체크 끄고 켜기(안전)
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

def main():
    print("모든 테이블을 삭제 후 재생성합니다...")
    reset_tables()
    print("시드 데이터 삽입 중...")

    session = SessionLocal()
    try:
        seed_data(session)
        session.commit()
        print("시드 완료")
    except IntegrityError as e:
        session.rollback()
        print(f"시드 중 중복/제약 오류: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # models를 반드시 import 해야 Base에 매핑이 등록됩니다.
    from . import models  # noqa: F401
    main()
