# reset_tables.py
from .database import Base, engine
from . import models  # 반드시 import 해야 Base가 테이블들을 인식함

print("모든 테이블을 삭제하고 다시 생성합니다...")

# 모든 테이블 드롭 (순서대로 안전하게 삭제)
Base.metadata.drop_all(bind=engine)
print("모든 테이블이 삭제되었습니다.")

# 모든 테이블 재생성
Base.metadata.create_all(bind=engine)
print("모든 테이블이 새로 생성되었습니다.")
