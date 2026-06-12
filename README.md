# python-datagokr-api

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성합니다. 공식 API 필드명, 코드 식별자, 명령어, URL, provider 원문처럼 그대로 보존해야 하는 값만 영어를 유지합니다. 새 문서나 기존 문서를 수정할 때도 이 규칙을 우선합니다.

TripMate에서 쓰는 공공데이터포털(data.go.kr) 표준데이터 Open API를 작은 typed
Python client로 감싼 라이브러리입니다.

현재 포함한 표준데이터셋은 아래 다섯 가지입니다.

- 전국박물관미술관정보표준데이터: `tn_pubr_public_museum_artgr_info_api`
- 전국주차장정보표준데이터: `tn_pubr_prkplce_info_api`
- 전국관광지정보표준데이터: `tn_pubr_public_trrsrt_api`
- 전국문화축제표준데이터: `tn_pubr_public_cltur_fstvl_api`
- 전국지역특화거리표준데이터: `tn_pubr_public_area_spcliz_stret_api`

TripMate/krtour-map 큐레이션 후보로 쓰는 data.go.kr 파일데이터 자동변환 API도
raw row 보존 형태로 포함합니다.

- 서울특별시_책방(서점) 현황정보: `datagokr_seoul_bookstores`
- 경기관광공사_경기도 무슬림 친화 음식점: `datagokr_gyeonggi_muslim_friendly_restaurants`
- 경기도 안산시_세계맛집(안산맛집): `datagokr_ansan_world_restaurants`
- 제주특별자치도_향토음식점지정현황: `datagokr_jeju_local_restaurants`

TripMate 문서에서 별도 `python-*-api` 소유가 없는 data.go.kr OpenAPI도 함께 둡니다.

- 농촌진흥청 국립농업과학원 농업기상 관측지점 상세정보: `1390802/AgriWeather/getObsrSpotList`
- 한국수자원공사 수문 운영 정보: `B500001/dam/sluicePresentCondition/*`

## Quick Start

```python
from datagokr import DataGoKrClient

with DataGoKrClient() as client:
    page = client.museum_art.list(num_of_rows=10)
    print(page.total_count, page.items[0].fclty_nm)

    file_page = client.file_data.ansan_world_restaurants(per_page=10)
    print(file_page.items[0].raw["가게명"])
```

인증키는 `DataGoKrClient(api_key="...")`로 직접 넘기거나 `DATA_GO_KR_SERVICE_KEY`
환경변수에 설정합니다. data.go.kr 엔드포인트 서비스키 환경변수는 이 이름으로 통일합니다.

`.env`는 저장소에 포함하지 않습니다.
