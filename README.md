## 디렉토리 구조/설명

```
capstone/
├── main.py # FastAPI를 실행. routers/의 라우터를 묶어줌
├── .env # 환경변수 저장
├── routers/
│   ├── auth.py # 로그인 시 토큰 발급. 회원가입 요청 API
│   ├── exercise.py # 운동 목록 레코드, 신체 정보, 운동 레코드 update 요청 API
│   ├── goal.py # 운동 목표, 현재/목표 신체 정보 update API
│   ├── llm.py # 운동 플랜 생성 API. 쿼리에 대해 벡터DB 유사도 검색하여 증강된 프롬프트를 sllm 모델에 전달
│   └── utils.py # 토큰 생성 알고리즘
├── rag/
│   ├── embeddings.py # 임베딩 모델 선택, Chroma 벡터DB 생성
│   └── indexing.py # docs/의 pdf문서를 읽어 메타데이터 추가, 청크 단위로 나누어 벡터DB 저장
├── docs/
│   └── *.pdf # 운동 관련 pdf 문서
├── data/
│   ├── chroma_plan
│   │   └── chroma.sqlite3 # Chroma DB가 데이터를 저장하는 DB파일
```


## 사용 설명(팀 인원용)
- fastapi 서버 실행

가상환경 켜기: capstone 디렉토리에서 source venv/bin/activate 입력

uvicorn main:app --reload --port 8000 --host 0.0.0.0 입력 -> fastapi 실행.

swagger: 129.154.56.222:8000/docs

- fastapi 실행중인 서버 프로세스 강제 종료(이전에 예상치 못한 종료로 인해 서버가 죽어있을 수 있음)

sudo lsof -i :8000 해서 나오는 프로세스 sudo kill -9 PID


- 데이터베이스 접근 방법

터미널에서 ssh SM 하고

mysql -u capstone -p 입력

0602 입력

show databases;

use capstonedb;

show tables;


- 데이터베이스 테이블 drop, create

python3 -m db_work.reset_tables 입력
- 데이터베이스 테이블 drop, create + 기본 데이터 삽입

python3 -m db_work.reset_and_seed 입력