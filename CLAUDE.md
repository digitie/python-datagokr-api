# CLAUDE.md — 프로젝트 컨텍스트

이 파일은 에이전트(Antigravity 등)가 매 세션 시작 시 자동으로 읽어 프로젝트 상태를 파악하는 문서다.
프로젝트 규칙은 `AGENTS.md`에, 상세 매뉴얼은 `SKILL.md`에 정의되어 있다.
이 파일은 **현재 상태**와 **세션 간 연속성**에 집중한다.

## 프로젝트 현황 (2026-05-31)

Pydantic v2와 httpx 기반의 공공데이터포털(data.go.kr) Typed Python 클라이언트.
현재 TripMate가 필요로 하는 표준데이터 API(박물관, 주차장, 관광지, 문화축제) 및 부가 OpenAPI(댐 수문, 농업기상)가 구현 완료된 상태이며, WSL 가상환경 하에 Ruff 린터, Mypy 타입 체커, Pytest 테스트 스위트가 깨끗하게 통과되는 안정화 수준을 유지하고 있다.

### 현재 작업

- (없음) — maplibre-vworld-js 프로젝트 스타일 및 MCP 설정을 가져와 적용하고 PR 작성 및 머지/리모트 푸시 수행 중.

### 잔존 기술 부채

- (없음 — 신규 부채 발견 시 `docs/tasks.md` 혹은 관련 이슈로 관리)

### 브랜치 정리

- `chore/adopt-vworld-style-and-mcp` — 현재 작업 중인 브랜치.

## 에이전트 환경 및 CodeGraph

- 모든 에이전트(Antigravity, Claude, Codex)는 단일 작업공간인 `F:\dev\python-datagokr-api`를 직접 이용한다.
- 작업 시작 시 `git switch -c agent/<topic> main`으로 feature 브랜치를 딴다.
- CodeGraph는 루트 디렉토리에서 `codegraph sync`를 주기적으로 실행하여 최신 구조 정보를 동기화한다.
- MCP 설정은 `.gemini/mcp.json` 및 루트의 `antigravity.json`, `claude.json`, `codex.json`, `.codex/config.toml`에 각각 정리되어 있다.

## 로컬 개발 환경

```
F:\dev\python-datagokr-api\
├── src/
│   └── datagokr/
│       ├── services/       # OpenAPI 서비스 레이어 (standard.py, openapi.py)
│       ├── client.py       # DataGoKrClient 엔트리포인트
│       ├── config.py       # 환경 설정 및 서비스 키 관리
│       ├── exceptions.py   # 에러 정의
│       ├── models.py       # Pydantic v2 데이터 모델 정의
│       └── transport.py    # httpx 통신 레이어
├── tests/
│   ├── integration/        # data.go.kr 실서버 호출 통합 테스트
│   └── unit/               # Mock/Respx 기반 단위 테스트
├── pyproject.toml          # 패키지 메타데이터, Ruff/Mypy 설정
└── README.md               # 한글 패키지 안내 및 퀵스타트
```

Python 3.10 이상 사용. WSL 가상환경 `.venv`에서 실행.

## 빠른 검증 명령

```bash
# 린트 및 스타일 가이드 검사
wsl .venv/bin/ruff check

# 타입 체크 (strict 모드 만족 필수)
wsl .venv/bin/mypy

# 테스트 실행 (단위 테스트 중심)
wsl .venv/bin/python -m pytest
```

## 주요 결정 사항

- **Pydantic v2 기반 설계**: 모든 Open API 응답은 엄격하게 typed Pydantic 모델로 변환하여 API 응답 오류 및 스키마 변경에 회복 탄력성을 둔다.
- **WSL 통합 개발 환경**: Windows 파일 시스템 상에 가상환경이 구축되어 있으므로, 툴체인 및 테스트는 WSL의 Python 인터프리터를 통해 일관성 있게 구동한다.
- **인증 분리 구조**: API Key 주입은 client 생성자 인자 혹은 `DATA_GO_KR_SERVICE_KEY` 환경변수로 통일하여, 안전하고 테스트 친화적인 설계를 가진다.

## 작업 후 의무사항

1. `wsl .venv/bin/ruff check`가 깨끗하게 통과되는지 확인.
2. `wsl .venv/bin/mypy`를 통한 엄격한 타입 검증 통과.
3. `wsl .venv/bin/python -m pytest`로 단위 테스트 성공 확인.
4. 모든 코드는 `main`에 직접 푸시하지 않고, feature 브랜치를 생성하여 PR 생성 후 머지한다.
