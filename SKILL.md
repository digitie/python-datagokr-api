# SKILL — python-datagokr-api 에이전트 매뉴얼

> 이 파일은 당신(AI 에이전트)이 작업을 시작하기 전 반드시 읽어야 한다.
> 프로젝트의 독특한 구조와 Python 스타일 가이드라인을 담고 있어, 사전에 불필요한 디버깅 시간을 크게 단축시킨다.

## 1. 정체성

이 저장소(GitHub 이름 `python-datagokr-api`, Python 패키지 `datagokr`)는 TripMate 서비스에서 한국 공공데이터포털(data.go.kr)의 표준데이터 Open API와 댐/기상 OpenAPI를 안전하고 일관된 형식으로 호출하기 위한 **Typed Python 클라이언트 라이브러리**다.

- HTTP 통신은 `httpx`를 이용한다.
- 모든 API 응답 및 요청 파라미터는 `pydantic` v2 모델을 사용하여 타입 검증을 거친다.
- Mypy의 strict 모드 검사를 100% 만족하는 고품질의 타입 안정성을 지향한다.

### 식별자 매핑

| 항목 | 값 |
|------|----|
| GitHub 저장소 | `python-datagokr-api` |
| Python 패키지 | `datagokr` |
| import | `from datagokr import DataGoKrClient` |
| 핵심 의존성 | `httpx>=0.27`, `pydantic>=2.6` |

### 개발 환경

- Python 3.10 이상 지원.
- WSL 환경 하에 `.venv` 가상환경을 구축하여 린터 및 테스트 등을 구동한다.
- GitHub Actions CI를 사용하지 않으며, 작업자가 PR 생성 및 머지 전에 로컬에서 검증 스크립트를 수동 실행하여 최종 게이트 역할을 수행한다.

## 2. 빠른 시작

```bash
cd F:\dev\python-datagokr-api

# WSL 환경 아래서 검증 스크립트 실행
wsl .venv/bin/ruff check
wsl .venv/bin/mypy
wsl .venv/bin/python -m pytest
```

에이전트 작업은 고정 worktree에서 진행한다. ChatGPT Codex는 `F:\dev\python-datagokr-api-codex`, Claude Code는 `F:\dev\python-datagokr-api-claude`, Google Antigravity 2.0은 `F:\dev\python-datagokr-api-antigravity`를 사용한다. 작업 시작/변경마다 `git switch -c agent/<topic> main`으로 새 브랜치를 따고 `codegraph sync`를 실행해 인덱스를 최신화한다.

## 3. 디렉토리 지도

```
src/datagokr/
  services/               — API 서비스 모듈 레이어
    standard.py           — 전국박물관미술관, 전국주차장 등 표준데이터 API 서비스 구현
    openapi.py            — 농업기상, 수문 운영 정보 등 일반 OpenAPI 서비스 구현
  client.py               — DataGoKrClient 메인 컴포넌트 및 서비스 프로퍼티 매핑
  config.py               — 서비스 인증키(Service Key) 로드 및 기본 설정
  exceptions.py           — DataGoKrError 및 하위 예외 클래스 선언
  models.py               — Pydantic v2 기반의 전체 스키마 응답/아이템 데이터 모델 정의
  transport.py            — httpx 동기/비동기 클라이언트 래핑 및 API 호출 로직
  py.typed                — PEP 561 호환 타입 정보 마커 파일
tests/
  unit/                   — Respx를 이용한 오프라인 Mocking 단위 테스트
  integration/            — data.go.kr 서버 실주소 호출을 포함한 온라인 통합 테스트
```

의존 방향은 **`config/exceptions/models` → `transport` → `services` → `client`**의 단방향 흐름을 지킨다.

## 4. 절대 하지 말 것 (DO NOT)

1. **`main` 직접 푸시 금지**: 반드시 브랜치를 따고 PR을 거쳐 머지한다.
2. **API 키 평문 커밋 금지**: 서비스 키 주입은 `DATA_GO_KR_SERVICE_KEY` 환경변수 또는 클라이언트 생성자 인자(`api_key="..."`)로 제한하며 절대 코드에 키를 하드코딩하지 않는다.
3. **타입 어노테이션 누락 금지**: 모든 함수 시그니처와 클래스 변수 등에 명확한 타입을 정의한다. Mypy strict 모드 통과 필수.
4. **Pydantic v1 스타일 코드 작성 금지**: peer/dev 환경 모두 Pydantic v2 이상을 사용하므로, v1 스타일의 헬퍼나 구식 스키마 정의(`class Config`)를 배제하고 v2 스타일(`model_config`)을 준수한다.
5. **동기/비동기 API 혼합 금지**: httpx의 동기 클라이언트와 비동기 클라이언트 호출이 한 곳에 엉키지 않도록 `transport.py`를 통해 격리 및 깔끔한 제어를 유지한다.
6. **불필요한 캐시 디렉토리 커밋 금지**: `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`는 반드시 gitignore하며 실수로 스테이징에 올리지 않는다.

## 5. 자주 묻는 작업

### 1) 새 OpenAPI 서비스 추가하기
1. `src/datagokr/models.py`에 요청/응답 형식에 맞는 Pydantic 모델을 정의한다.
2. `src/datagokr/services/` 내부의 알맞은 서비스 파일(`openapi.py` 혹은 `standard.py`)에 서비스 호출 클래스를 구현한다.
3. `src/datagokr/client.py`의 `DataGoKrClient` 인스턴스 초기화 영역에 해당 서비스 클래스 속성을 바인딩한다.

### 2) Pydantic 응답 모델 추가 또는 확장
- 응답 데이터의 필드가 누락되지 않도록 data.go.kr 가이드 문서를 면밀히 참조하고, 필드가 비어서 넘어오는 경우가 잦으므로 필요에 따라 `Optional` 또는 기본값 설정을 부여한다.
- CamelCase나 특정 규격이 아닐 경우 `Field(alias="...")` 또는 `Field(validation_alias="...")`를 유용하게 활용한다.

### 3) 새로운 단위 테스트 추가
- `tests/unit/`에 `test_<feature>.py` 형식으로 파일을 생성한다.
- 실서버가 다운되거나 키가 만료되어도 로컬 게이트가 정상 작동하도록 `respx`를 적극 사용하여 가짜 API 응답을 Mocking한 채 안전하게 검증한다.

## 6. 도메인 어휘

| 약어 / 용어 | 의미 |
|------|------|
| data.go.kr | 대한민국 공공데이터포털. 행정 및 공공기관이 보유한 공공데이터를 개방하는 포털 사이트 |
| Service Key | OpenAPI 호출을 위해 발급받는 고유 인증키. 인코딩/디코딩 상태에 주의가 필요함 |
| Standard Dataset | 전국 단위 공통 표준 형식으로 제공되는 데이터셋 (예: 전국박물관미술관, 전국주차장 등) |
| AgriWeather | 농촌진흥청 국립농업과학원에서 제공하는 농업기상 관측지점 정보 및 실시간 수집 결과 |
| DamSluice | 한국수자원공사에서 수집·관리하는 수문 운영 및 수자원 현황 정보 |

## 7. 작업 후 체크리스트

- [ ] `wsl .venv/bin/ruff check` 실행 결과 린트 오류 없음
- [ ] `wsl .venv/bin/mypy` 실행 결과 strict 타입 경고 없음
- [ ] `wsl .venv/bin/python -m pytest` 실행 결과 모든 테스트 그린(Green) 통과
- [ ] 신규 API를 노출했을 경우 `README.md` 가이드 동기화 갱신
- [ ] 형상 관리가 정상적으로 진행되고 main 직접 커밋이 없는 브랜치 상태 확인
