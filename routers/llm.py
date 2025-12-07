import os, json, datetime, re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import select
from db_work.models import User, Exercise, ExerciseRecord # 당신의 프로젝트 구조에 맞게 import
from db_work import database
from routers.auth import get_current_user
from rag.embeddings import get_vectorstore


from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

router = APIRouter(prefix="/plan", tags=["plan"])

# ===== LLM (HF Inference API) =====
hf_ep = HuggingFaceEndpoint(
    repo_id=os.getenv("HF_REPO_ID", "Qwen/Qwen2.5-7B-Instruct"),
    task="conversational",
    temperature=0.2,
    max_new_tokens=3000,
)
chat = ChatHuggingFace(llm=hf_ep)

class ExerciseRow(BaseModel):
    exercise_id: int
    date: datetime.date
    sets: int = Field(ge=1, le=50)  # 세트 번호
    reps: int = Field(ge=1, le=200)
    weight: Optional[float] = None

# ===== 프롬프트 =====
PROMPT = ChatPromptTemplate.from_template(
    """당신은 운동 플래너입니다. 사용자 정보를 바탕으로 하루치 운동 계획을 JSON 배열로 생성하세요.

## 출력 형식
반드시 다음과 같은 JSON 배열만 출력하세요:
[
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 1, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 2, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 3, "reps": 12, "weight": 20.0}}
]

## 완전한 출력 예시 (4가지 운동, 총 16개 레코드)
[
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 1, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 2, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 3, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 1, "date": "2024-01-15", "sets": 4, "reps": 12, "weight": 20.0}},
  {{"exercise_id": 4, "date": "2024-01-15", "sets": 1, "reps": 10, "weight": 30.0}},
  {{"exercise_id": 4, "date": "2024-01-15", "sets": 2, "reps": 10, "weight": 30.0}},
  {{"exercise_id": 4, "date": "2024-01-15", "sets": 3, "reps": 10, "weight": 30.0}},
  {{"exercise_id": 4, "date": "2024-01-15", "sets": 4, "reps": 10, "weight": 30.0}},
  {{"exercise_id": 7, "date": "2024-01-15", "sets": 1, "reps": 15, "weight": 0}},
  {{"exercise_id": 7, "date": "2024-01-15", "sets": 2, "reps": 15, "weight": 0}},
  {{"exercise_id": 7, "date": "2024-01-15", "sets": 3, "reps": 15, "weight": 0}},
  {{"exercise_id": 7, "date": "2024-01-15", "sets": 4, "reps": 15, "weight": 0}},
  {{"exercise_id": 8, "date": "2024-01-15", "sets": 1, "reps": 20, "weight": 5.0}},
  {{"exercise_id": 8, "date": "2024-01-15", "sets": 2, "reps": 20, "weight": 5.0}},
  {{"exercise_id": 8, "date": "2024-01-15", "sets": 3, "reps": 20, "weight": 5.0}},
  {{"exercise_id": 8, "date": "2024-01-15", "sets": 4, "reps": 20, "weight": 5.0}}
]

## 운동 구성 규칙
- 정확히 4가지 다른 운동 선택 (아래 카탈로그의 exercise_id만 사용)
- 각 운동: 3-5세트 수행
- sets 필드는 세트 번호 (1부터 시작, 4세트면 sets=1,2,3,4로 4개의 별도 레코드 생성)
- 같은 운동의 모든 세트는 동일한 reps 사용
- 날짜는 반드시 {date} 사용
- weight는 자중 운동이면 0, 기구 운동이면 적절한 무게 설정

## 사용자 정보
- 목표: {user_goal}
- 현재 상태: {recent_height}cm, {recent_weight}kg, 체지방 {recent_pbf}%
- 목표 상태: {goal_height}cm, {goal_weight}kg, 체지방 {goal_pbf}%
- 제약사항: {constraints}

## 최근 운동 이력 (이 패턴을 참고하여 과부하/점진적 증량 적용)
{exercise_history}

## 참고 가이드
{context}

중요: 최근 운동 이력과 참고 가이드를 참고하더라도 반드시 서로 다른 4가지 운동을 포함하는 플랜을 생성하여야 한다.

## 허용 운동 카탈로그 (반드시 이 목록의 exercise_id만 사용)
{catalog_text}

중요: 오직 JSON 배열만 출력하세요. 코드블록(```), 설명, 기타 텍스트 출력 금지. 출력은 [로 시작하고 ]로 끝나야 합니다.
"""
)

def build_exercise_history(
    db: Session,
    user_id: int,
    days: int = 7,
) -> str:
    """
    최근 N일(기본 7일)의 운동 기록을 LLM이 보기 좋게 텍스트로 변환.
    """
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days)

    q = (
        db.query(ExerciseRecord, Exercise)
        .join(Exercise, ExerciseRecord.exercise_id == Exercise.id)
        .filter(ExerciseRecord.user_id == user_id)
        .filter(ExerciseRecord.date >= start_date)
        .order_by(ExerciseRecord.date.desc(), ExerciseRecord.sets.asc())
    )

    rows = q.all()
    if not rows:
        return f"최근 {days}일간 운동 기록이 없습니다."

    lines = []
    for rec, ex in rows:
        lines.append(f"{rec.date} | {ex.name} | set {rec.sets} | {rec.reps} reps | {rec.weight or 0} kg")
    
    return "\n".join(lines)
    
    
def build_rag_context(query: str, k: int = 5) -> str:
    vs = get_vectorstore()
    try:
        docs = vs.similarity_search(query, k=k)
    except Exception:
        return ""

    if not docs:
        return ""

    chunks = []
    for d in docs:
        title = d.metadata.get("title") if d.metadata else None
        prefix = f"[{title}] " if title else ""
        chunks.append(f"- {prefix}{d.page_content}")

    return "\n".join(chunks)


def build_catalog_text(db: Session) -> str:
    """
    Exercise 테이블에서 LLM이 고를 수 있는 운동 목록을 'id | name | alias들' 형태로 제공
    LLM은 오직 여기 있는 id만 사용하게 됨.
    """
    rows = db.execute(select(Exercise.id, Exercise.name, Exercise.muscle_group)).all()
    # 필요하면 muscle_group, equipment, 별칭 등 추가
    lines = [f"{r.id} | {r.name} | {r.muscle_group}" for r in rows]
    # 너무 길면 상위 N개, 또는 조건 필터링(헬스장/홈트 등)
    return "\n".join(lines)

def extract_json_array(text: str) -> str:
    # 코드블록 제거
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "")
    text = text.strip()

    # 첫 '[' 찾기
    start = text.find('[')
    if start == -1:
        return ""

    # 문자열 상태 추적하며 최외곽 배열 닫힘 탐색
    in_str = False
    esc = False
    depth = 0
    end = None
    for i, ch in enumerate(text[start:], start=start):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    if end is None:
        # 닫힘 누락 → 보수
        candidate = text[start:]
        # 배열 끝에 붙은 불필요한 꼬리(로그의 "..." 등) 제거
        candidate = re.sub(r"\s*\.\.\.\s*$", "", candidate)
        # 닫는 대괄호 개수 보충
        opens = candidate.count('[')
        closes = candidate.count(']')
        if opens > closes:
            # 닫기 전에 trailing comma 제거
            candidate = re.sub(r",\s*$", "", candidate)
            candidate = candidate + (']' * (opens - closes))
        return candidate.strip()
    return text[start:end].strip()

def normalize_list_of_dicts(obj):
    if isinstance(obj, dict):
        obj = [obj]
    if not isinstance(obj, list):
        raise HTTPException(status_code=422, detail="Invalid LLM JSON: top-level must be array or object")
    norm = []
    for i, item in enumerate(obj):
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail=f"Invalid LLM JSON: item[{i}] is string, not object")
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail=f"Invalid LLM JSON: item[{i}] must be object")
        norm.append(item)
    return norm

@router.post("/generate-and-save")
def generate_and_save(
    user_id: int,
    date: str,
    constraints: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_user)
):
    # 0) 유저 정보 조회
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1) 카탈로그 생성 (이름→ID 매핑을 LLM에 알려주기 위함)
    catalog_text = build_catalog_text(db)
    if not catalog_text.strip():
        raise HTTPException(status_code=400, detail="Exercise catalog is empty.")

    history = build_exercise_history(db, user_id=current_user.id)

    rag_query = (
        f"운동 목표: {user.user_goal or 'General Fitness'}, "
        f"현재 상태: {user.recent_state_height or 0}cm, {user.recent_state_weight or 0}kg, PBF {user.recent_state_pbf or 0}%, "
        f"목표 상태: {user.goal_state_height or 0}cm, {user.goal_state_weight or 0}kg, PBF {user.goal_state_pbf or 0}%, "
        f"제약사항: {constraints or (user.constraints if hasattr(user, 'constraints') else 'None')}"
    )
    rag_context = build_rag_context(rag_query, k=5)

    chain = PROMPT | chat | StrOutputParser()

    # 2) LLM 호출
    text = chain.invoke({
        "user_goal": user.user_goal or "General Fitness",
        "recent_height": user.recent_state_height or 0,
        "recent_weight": user.recent_state_weight or 0,
        "recent_pbf": user.recent_state_pbf or 0,
        "goal_height": user.goal_state_height or 0,
        "goal_weight": user.goal_state_weight or 0,
        "goal_pbf": user.goal_state_pbf or 0,
        "constraints": constraints or "None",
        "date": date,
        "catalog_text": catalog_text,
        "exercise_history": history,
        "context": rag_context,
    })

    # 2-1) 빈 응답 가드
    if not isinstance(text, str):
        # 혹시 메시지 객체 등으로 올 경우 문자열화
        text = getattr(text, "content", "") or str(text)

    if not text or not text.strip():
        raise HTTPException(status_code=502, detail="LLM returned empty output")

    # 2-2) JSON 배열만 뽑아내기
    clean = extract_json_array(text)
    if not clean:
        # 디버깅용으로 일부만 로그 남기고 에러
        snippet = (text[:300] + "...") if len(text) > 300 else text
        raise HTTPException(status_code=422, detail=f"Invalid LLM JSON: cannot locate top-level array. sample={snippet}")

    # 3) JSON 파싱 + 검증
    try:
        obj = json.loads(clean)
    except json.JSONDecodeError:
        # 마지막 방어: 끝에 ']' 하나 더 붙여 재시도 (일부 케이스 대비)
        try:
            obj = json.loads(re.sub(r",\s*$", "", clean) + "]")
        except Exception as e2:
            raise HTTPException(status_code=422, detail=f"Invalid LLM JSON: {e2}")
    obj = normalize_list_of_dicts(obj)  # 정규화 추가
    rows = [ExerciseRow(**item) for item in obj]

    # 4) exercise_id 유효성(카탈로그 제한) 검증
    valid_ids = {r[0] for r in db.execute(select(Exercise.id)).all()}
    for r in rows:
        if r.exercise_id not in valid_ids:
            raise HTTPException(status_code=422, detail=f"Unknown exercise_id: {r.exercise_id}")

    # (선택) 날짜 검증
    target_date = datetime.date.fromisoformat(date)
    for r in rows:
        if r.date != target_date:
            raise HTTPException(status_code=422, detail=f"date mismatch: {r.date} != {target_date}")

    # 5) DB 저장 (bulk)
    # sets는 '세트 번호' 그대로 저장
    new_records = [
        ExerciseRecord(
            user_id=user_id,
            exercise_id=r.exercise_id,
            date=r.date,
            sets=r.sets,        # 세트 '개수'가 아니라 '몇 번째 세트'인지
            reps=r.reps,
            weight=r.weight,
            # exercise_time/rest_time/is_completed은 나중에 프론트에서 PATCH
        )
        for r in rows
    ]
    db.bulk_save_objects(new_records)
    db.commit()

    return {"inserted": len(new_records)}
