# decisions.md — 의사결정 기록

이 문서는 이 프로젝트의 구조적 결정을 결정 시점 순서로 누적한다.
결정이 뒤집힐 때는 새 항목을 추가하고, 옛 항목은 지우지 않은 채
(supersedes: 위 항목)으로 표시한다.

## D-001: 응답 모델은 Pydantic v2 전용으로 설계한다

- 상태: accepted
- 날짜: 2026-05-20 (초기 구현부터)

### 컨텍스트

`models.py`의 모든 응답 모델은 `model_config = ConfigDict(...)`로 설정을 선언한다.
`pyproject.toml`의 의존성도 `pydantic>=2.6`이다.

### 결정

모든 Open API/파일데이터 응답 모델은 Pydantic v2 스타일(`model_config`,
`Field(alias=...)`)로만 작성한다. v1 스타일(`class Config:`)은 쓰지 않는다.

### 근거

data.go.kr 응답은 camelCase 필드명과 느슨한 타입(빈 문자열, 숫자의 자유 표기)이
섞여 있어, `model_validate`/`TypeAdapter` 기반의 엄격한 검증과 별칭 매핑이 있는
Pydantic v2가 파싱 안정성에 유리하다.

### 결과

`AGENTS.md`의 DO NOT 목록이 이를 명시한다. 새 모델을 추가할 때도 이 스타일을
따른다.

## D-002: data.go.kr 인증키 환경변수는 형제 저장소와 `DATA_GO_KR_SERVICE_KEY`로 통일한다

- 상태: accepted
- 날짜: 2026-05-20 (초기 구현부터)

### 컨텍스트

`config.py`의 `API_KEY_ENV_NAMES`는 `("DATA_GO_KR_SERVICE_KEY",)` 하나만 담고
있으며, `DataGoKrConfig.from_env()`가 이 이름으로 환경변수를 조회한다.

### 결정

data.go.kr 게이트웨이를 호출하는 인증키 환경변수 이름은 `DATA_GO_KR_SERVICE_KEY`로
고정한다. 같은 data.go.kr 발급 키를 쓰는 다른 형제 저장소(`python-mois-api`,
`python-krheritage-api` 등)와 이름을 통일해, 여러 라이브러리를 함께 쓰는 소비자
앱의 설정을 단순하게 유지한다. RustFS 등 이 패키지에만 의미 있는 설정값은
`DATAGOKR_*`/`RUSTFS_*` 프리픽스로 별도 구분한다.

### 근거

인증키 자체는 실제로 동일한 발급 체계를 공유하므로, 저장소마다 다른 이름을 쓰면
TripMate 같은 다중 라이브러리 소비자가 같은 키를 여러 이름으로 중복 설정해야
한다.

### 결과

`README.md`와 `AGENTS.md`가 이 환경변수 이름을 명시한다. 새 인증 방식이 필요해도
기존 이름을 재사용하지 않고 새 환경변수를 추가한다.

## D-003: `DataGoKrClient`는 현재 범위에서 동기 전용으로 유지한다

- 상태: accepted
- 날짜: 2026-05-20 (초기 구현부터)

### 컨텍스트

`src/datagokr`에는 `SyncHttpxTransport`와 `DataGoKrClient`만 있고, 비동기
전송/클라이언트 구현은 없다(`Async`로 시작하는 이름이 소스에 없음).

### 결정

비동기 클라이언트는 실제 수요가 생기기 전까지 추가하지 않는다. 동작하지 않는
자리표시자 `AsyncDataGoKrClient`도 두지 않는다 — 필요해지면 실제 비동기 전송
계층과 함께 새 결정으로 추가한다.

### 근거

현재 소비자(TripMate 배치/스크립트 경로)는 동기 호출만으로 충분하며, 미완성
비동기 API를 노출하면 소비자가 실제로 쓸 수 있다고 오해할 수 있다.

### 결과

`AGENTS.md`의 "동기/비동기 혼동 금지" 규칙은 이후 비동기 클라이언트를 추가할 때도
동기 `Client`와 비동기 `AsyncClient` 구조를 명확히 분리하라는 뜻이며, 아직 존재하지
않는 비동기 클라이언트를 만들라는 지시가 아니다. 실제로 추가할 때는 이 항목을
supersede하는 새 결정을 남긴다.
