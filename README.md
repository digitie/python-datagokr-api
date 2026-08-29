# python-datagokr-api

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![MIT 라이선스](https://img.shields.io/badge/License-MIT-blue.svg)
![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

`python-datagokr-api`(Python import 패키지 `datagokr`)는 TripMate가 쓰는 공공데이터포털
(data.go.kr) 표준데이터 Open API, 파일데이터 자동변환 API, 개별 OpenAPI 일부를 감싸는 작은
typed Python client 라이브러리입니다. `DataGoKrClient`는 동기 전용 인터페이스로 서비스별
속성(`museum_art`, `parking`, `tourist_attraction`, `festival`, `special_street`,
`file_data`, `agri_weather`, `kwater_sluice`)을 제공하며, 모든 응답을 Pydantic v2 모델로
typed 변환합니다.

최근 변경 사항은 [`CHANGELOG.md`](CHANGELOG.md)의 `[Unreleased]`를 참고합니다.

## 제공 표면

| 표면 | 진입점 | 설명 |
|------|--------|------|
| 표준데이터 5종 | `client.museum_art` / `client.parking` / `client.tourist_attraction` / `client.festival` / `client.special_street` | 박물관미술관·주차장·관광지·문화축제·지역특화거리 표준데이터 Open API |
| 파일데이터 자동변환 4종 | `client.file_data` | 서울 책방, 경기 무슬림 친화 음식점, 안산 세계맛집, 제주 향토음식점 raw row 보존 조회 |
| 개별 OpenAPI 2종 | `client.agri_weather` / `client.kwater_sluice` | 농업기상 관측지점 상세정보, 한국수자원공사 수문 운영 정보 |
| 파일 저장 helper | `client.save_to_local()` / `client.save_to_rustfs()` | 다운로드한 바이트를 로컬/RustFS 객체 저장소에 저장 |

## 먼저 읽을 문서

README는 입구 역할만 합니다. 세부 규칙과 결정은 아래 문서를 정본으로 봅니다.

| 필요 정보 | 문서 |
|-----------|------|
| 에이전트 작업 규칙과 도메인 어휘 | [`SKILL.md`](SKILL.md) |
| 설계 결정 | [`docs/decisions.md`](docs/decisions.md) |
| 변경 이력 | [`CHANGELOG.md`](CHANGELOG.md) |

## 설치

개발 중인 저장소는 편집 가능 모드로 설치합니다.

```bash
pip install -e ".[dev]"
```

PyPI 공개 배포는 하지 않습니다. TripMate 등 내부 소비자는 GitHub 저장소를 직접
의존성으로 설치합니다.

```bash
pip install "python-datagokr-api @ git+https://github.com/digitie/python-datagokr-api.git"
```

## 사용법

```python
from datagokr import DataGoKrClient

with DataGoKrClient() as client:
    page = client.museum_art.list(num_of_rows=10)
    print(page.total_count, page.items[0].fclty_nm)

    file_page = client.file_data.ansan_world_restaurants(per_page=10)
    print(file_page.items[0].raw["가게명"])
```

인증키는 `DataGoKrClient(api_key="...")`로 직접 넘기거나 `DATA_GO_KR_SERVICE_KEY`
환경변수에 설정합니다. data.go.kr 엔드포인트 서비스키 환경변수는 형제 저장소와
이 이름으로 통일합니다(`docs/decisions.md` D-002). `.env`는 저장소에 포함하지 않습니다.

## RustFS 저장 설정 (선택)

`client.save_to_rustfs()`(`src/datagokr/storage.py`)로 다운로드한 바이트를 로컬 저장과
동시에 S3 호환 RustFS 객체 저장소에 올리려면 아래 환경변수를 설정합니다. `save_to_local()`만
쓰는 경우에는 필요 없습니다.

각 값은 `save_to_rustfs()` 호출 시 넘긴 인자(또는 `DataGoKrClient` 생성 시 넘긴 값) →
`DATAGOKR_RUSTFS_*` 환경변수 → `RUSTFS_*` 환경변수 → 기본값 순으로 해석됩니다(먼저
찾은 값을 사용).

| 환경변수 (`DATAGOKR_` 접두 우선, 없으면 `RUSTFS_` 접두 사용) | 역할 | 기본값 |
|------|------|--------|
| `DATAGOKR_RUSTFS_BUCKET` / `RUSTFS_BUCKET` | 업로드 대상 버킷명 | `datagokr-uploads` |
| `DATAGOKR_RUSTFS_ENDPOINT_URL` / `RUSTFS_ENDPOINT_URL` | RustFS S3 호환 엔드포인트 URL | 없음(미설정 시 boto3 기본 리졸버 사용) |
| `DATAGOKR_RUSTFS_ACCESS_KEY_ID` / `RUSTFS_ACCESS_KEY_ID` | 액세스 키 ID | 없음 |
| `DATAGOKR_RUSTFS_SECRET_ACCESS_KEY` / `RUSTFS_SECRET_ACCESS_KEY` | 시크릿 액세스 키 | 없음 |
| `DATAGOKR_RUSTFS_REGION_NAME` / `RUSTFS_REGION_NAME` | 리전명 | `us-east-1` |

RustFS 업로드에는 `boto3`가 필요합니다(`pip install boto3`, 패키지 자체 의존성에는
포함되어 있지 않습니다). 액세스 키/시크릿 키를 모두 설정하지 않으면 boto3 기본 자격
증명 체인(환경변수, 공유 credentials 파일 등)을 그대로 따릅니다. `.env`는 저장소에
포함하지 않습니다.

## 예제: 관광지 표준데이터 조회

```python
from datagokr import DataGoKrClient

with DataGoKrClient() as client:
    page = client.tourist_attraction.list(num_of_rows=5)
    for item in page.items:
        print(item.trrsrt_nm, item.rdnmadr)
```

이 예제는 표준데이터 표면 1종만 다루며, 파일데이터·개별 OpenAPI 호출 방식은 위 "사용법"과
`SKILL.md`를 참고합니다.

## 검증

```bash
python -m pytest -q -m "not live"
python -m ruff check .
python -m mypy src/datagokr
```

live 테스트는 실제 data.go.kr 엔드포인트를 호출하므로 `DATA_GO_KR_SERVICE_KEY`가 있을 때만
`python -m pytest -m live`로 별도 실행합니다.

## 데이터 출처

현재 포함한 표준데이터셋은 아래 다섯 가지입니다.

- 전국박물관미술관정보표준데이터: `tn_pubr_public_museum_artgr_info_api`
- 전국주차장정보표준데이터: `tn_pubr_prkplce_info_api`
- 전국관광지정보표준데이터: `tn_pubr_public_trrsrt_api`
- 전국문화축제표준데이터: `tn_pubr_public_cltur_fstvl_api`
- 전국지역특화거리표준데이터: `tn_pubr_public_area_spcliz_stret_api`

TripMate/`kor-travel-map`(구 `python-krtour-map`) 큐레이션 후보로 쓰는 data.go.kr
파일데이터 자동변환 API도 raw row 보존 형태로 포함합니다.

- 서울특별시_책방(서점) 현황정보: `datagokr_seoul_bookstores`
- 경기관광공사_경기도 무슬림 친화 음식점: `datagokr_gyeonggi_muslim_friendly_restaurants`
- 경기도 안산시_세계맛집(안산맛집): `datagokr_ansan_world_restaurants`
- 제주특별자치도_향토음식점지정현황: `datagokr_jeju_local_restaurants`

TripMate 문서에서 별도 `python-*-api` 소유가 없는 data.go.kr OpenAPI도 함께 둡니다.

- 농촌진흥청 국립농업과학원 농업기상 관측지점 상세정보: `1390802/AgriWeather/getObsrSpotList`
- 한국수자원공사 수문 운영 정보: `B500001/dam/sluicePresentCondition/*`

## 디렉터리 개요

| 경로 | 역할 |
|------|------|
| `src/datagokr/client.py` | `DataGoKrClient` 진입점과 서비스 속성 조립 |
| `src/datagokr/config.py` | 환경변수·인증키·RustFS 설정 로딩 |
| `src/datagokr/services/standard.py` | 표준데이터 5종 서비스 |
| `src/datagokr/services/file_data.py` | 파일데이터 자동변환 카탈로그와 서비스 |
| `src/datagokr/services/openapi.py` | 개별 OpenAPI(농업기상, 수문) 서비스 |
| `src/datagokr/models.py` | Pydantic v2 응답 모델 |
| `src/datagokr/transport.py` | httpx 기반 동기 전송 계층 |
| `src/datagokr/storage.py` | 로컬/RustFS 저장 helper |
| `tests/unit/` | 네트워크 호출 없는 단위 테스트 |
| `tests/integration/` | `@pytest.mark.live`가 붙은 실제 data.go.kr 호출 테스트 |

## 문서와 기여 규칙

- 모든 Markdown 문서는 한글로 작성합니다. 코드 식별자, 명령어, URL, provider 원문 용어만
  예외로 원문을 유지합니다.
- 작업 전 [`AGENTS.md`](AGENTS.md)와 [`SKILL.md`](SKILL.md)를 확인합니다.
- 주요 구조 결정은 [`docs/decisions.md`](docs/decisions.md)에 ADR로 남기고, 사용자 가시
  변경은 [`CHANGELOG.md`](CHANGELOG.md)에 기록합니다.
- `main` 직접 push 대신 작업 브랜치와 PR을 사용합니다.

## 법적 고지

이 저장소의 라이선스(MIT, [`LICENSE`](LICENSE))는 이 저장소의 코드에만 적용됩니다.
공공데이터포털(data.go.kr), 농촌진흥청, 한국수자원공사, 서울특별시·경기관광공사·안산시·
제주특별자치도 등 원 제공기관의 데이터/API 이용은 각 제공기관의 이용약관과 재배포 조건을
따라야 하며, 이 저장소가 그 준수나 데이터의 정확성·최신성을 보장하지 않습니다.
