# AGENTS.md

## 문서 언어 정책

이 저장소의 **모든 Markdown 문서는 한글로 작성한다**. 예외 없음. `README.md`, `CLAUDE.md`, `SKILL.md`도 본문은 한글이다.

다음 항목만 영어를 유지한다 — 한글로 옮기면 의미가 변하거나 정확성이 깨지기 때문:

- **코드 식별자**: 클래스/함수/타입/변수/모듈 이름 (`DataGoKrClient`, `StandardService`, `MuseumArtInfo`, `prkplce_info_api`).
- **명령어와 경로**: `wsl .venv/bin/pytest`, `wsl .venv/bin/ruff check`, `F:\dev\python-datagokr-api\src\datagokr`.
- **외부 공식 용어**: httpx, pydantic (v2), Open API, dam/sluice, AgriWeather, OpenAPI.
- **벤더/제품명**: data.go.kr, TripMate, Python.
- **표준 keyword**: ADR, CHANGELOG, ISO 8601 날짜, semver 라벨(`Added`/`Changed`/`Removed`/`Fixed`/`Security`).
- **shell 출력 / 로그 예시**: 그대로 캡처한 문자열은 보존.

설명 문장, 절제목, 표 column 헤더, ADR 본문, 빠른 시작 가이드, 일지 항목은 한글로 적는다. 새 문서를 만들 때 영문 초안을 두지 않는다 — 처음부터 한글로 쓴다.

## 역할

이 저장소(GitHub 이름 `python-datagokr-api`, Python 패키지 `datagokr`)는 한국 공공데이터포털(data.go.kr)의 표준 Open API 및 특정 OpenAPI들을 TripMate 서비스에서 사용할 수 있도록 타입 정의와 httpx 기반 HTTP 전송을 묶어 둔 **Typed Python 클라이언트 라이브러리**다.

## Think Before Coding

- 변경 전 관련 서비스 클래스(`src/datagokr/services/standard.py`, `services/file_data.py`, `services/openapi.py`)를 먼저 읽을 것
- 새 필드/모델을 추가하기 전 `tests/unit/`의 기존 fixture 응답으로 실제 data.go.kr 필드명을 확인할 것
- `client.py`의 서비스 속성 이름과 `__init__.py`의 공개 export 목록이 일치하는지 확인할 것

## Simplicity First

- 요청을 완전히 해결하는 최소한의 코드만 작성할 것
- 요청되지 않은 기능(예: 아직 필요 없는 비동기 클라이언트)을 추가하지 말 것
- 구체적인 필요 없이 설정 가능성이나 유연성을 늘리지 말 것

## Surgical Changes

- 버그 수정은 원인이 되는 서비스/모델 코드만 건드리고 주변 리팩터링을 곁들이지 말 것
- `DataGoKrClient`의 공개 서비스 속성 이름(`museum_art`, `file_data` 등)을 임의로 바꾸지 말 것 — TripMate 소비 코드가 직접 참조한다
- `FILE_DATASETS` 같은 카탈로그 항목을 변경할 때는 실제 data.go.kr 상세 페이지 값을 재확인한 뒤 수정할 것

## Goal-Driven Execution

- 실제 사용자 요청(또는 이슈)이 요구하는 것만 구현할 것
- data.go.kr 오류 envelope(HTTP 200 + 오류 코드로 감싼 실패)을 다룰 때는 `exceptions.py`의 기존 예외 계층을 따를 것
- 검증되지 않은 가정을 문서에 기록하지 말 것 — 실제 API 응답이나 코드로 확인한 것만 기록할 것

## Practical Bias

- 동작하는 최소 구현을 우선하고, 완벽한 일반화를 좇지 말 것
- provider가 원문에서 쓰는 필드명(`fclty_nm`, `trrsrt_nm` 등)은 번역하지 말고 `Field(alias=...)`로만 매핑할 것
- 네트워크 호출 없는 단위 테스트를 실제 API 호출이 필요한 live 테스트보다 우선할 것

## 식별자 (혼동 방지)

| 항목 | 값 |
|------|----|
| GitHub 저장소 이름 | `python-datagokr-api` |
| Python 패키지 이름 | `datagokr` |
| import 경로 | `from datagokr import DataGoKrClient` |
| 핵심 의존성 | `httpx>=0.27`, `pydantic>=2.6` |
| 개발 의존성 | `pytest`, `respx`, `ruff`, `mypy` |

## 개발 환경 정책

PC 개발은 Windows 호스트에서 진행하되, 테스트 및 린팅 검증은 WSL 환경의 가상환경(`.venv/bin`)을 이용해 수행한다.

- **`dist/` 혹은 빌드 산출물 비커밋**: 이 프로젝트는 소스 코드로만 배포하므로 빌드 배포본을 git에 커밋하지 않는다.
- **GitHub Actions 비사용**: 품질 게이트는 PR 머지 직전 작업자가 로컬 WSL에서 직접 실행한다.
- **에이전트별 고정 worktree**: ChatGPT Codex는 `F:\dev\python-datagokr-api-codex`, Claude Code는 `F:\dev\python-datagokr-api-claude`, Google Antigravity 2.0은 `F:\dev\python-datagokr-api-antigravity`를 고정 worktree로 사용한다. 작업마다 브랜치만 새로 만들고, CodeGraph는 worktree마다 1회 `codegraph init -i` 후 `codegraph sync`로 유지한다.

작업 전에 반드시 다음을 읽는다:

1. `CLAUDE.md` — 현재 작업과 잔존 부채
2. `SKILL.md` — 에이전트 매뉴얼 및 도메인 어휘
3. `README.md` — 클라이언트 기본 사용법

## 지시 우선순위

1. 사용자 요청
2. 이 `AGENTS.md`
3. `SKILL.md`
4. `README.md`
5. 기존 코드와 테스트
6. 최소한의, 되돌릴 수 있는 가정

## 절대 하지 말 것 (DO NOT)

1. **`main` 직접 푸시 금지** — 반드시 feature 브랜치 + PR 생성 후 머지.
2. **API 키 평문 커밋 금지** — 인증용 서비스 키는 환경변수 `DATA_GO_KR_SERVICE_KEY`로 넘기며 절대 코드나 설정 파일에 평문으로 커밋하지 않는다.
3. **타입 어노테이션 누락 금지** — 이 패키지는 `mypy --strict` 수준의 엄격한 타입 검사를 만족해야 하므로, 모든 함수와 메서드는 명확한 타입 선언이 필수적이다.
4. **Pydantic v1 스타일 코드 작성 금지** — `pydantic>=2.6` 버전을 기준으로 모델을 설계해야 하며, v1 형식(예: `class Config:`)을 사용하지 않고 v2 형식(`model_config = ...`)을 사용한다.
5. **캐시 디렉토리 커밋 금지** — `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`는 반드시 gitignore에 포함하고 커밋하지 않는다.
6. **동기/비동기 혼동 금지** — 동기 전송은 Client를, 비동기 전송은 AsyncClient 구조를 명확히 구분하여 설계한다.

## 작업 후 체크리스트

- [ ] `wsl .venv/bin/ruff check` 통과
- [ ] `wsl .venv/bin/mypy` 통과
- [ ] `wsl .venv/bin/python -m pytest` 통과
- [ ] 의사결정이 있었다면 변경 내역에 기록
- [ ] 사용자 가시 변경이면 `CHANGELOG.md`가 있을 시 업데이트

## 검증

```bash
wsl .venv/bin/ruff check
wsl .venv/bin/mypy
wsl .venv/bin/python -m pytest
```
