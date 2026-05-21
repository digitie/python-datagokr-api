# python-datagokr-api

TripMate에서 쓰는 공공데이터포털(data.go.kr) 표준데이터 Open API를 작은 typed
Python client로 감싼 라이브러리입니다.

현재 포함한 표준데이터셋은 아래 네 가지입니다.

- 전국박물관미술관정보표준데이터: `tn_pubr_public_museum_artgr_info_api`
- 전국주차장정보표준데이터: `tn_pubr_prkplce_info_api`
- 전국관광지정보표준데이터: `tn_pubr_public_trrsrt_api`
- 전국문화축제표준데이터: `tn_pubr_public_cltur_fstvl_api`

TripMate 문서에서 별도 `python-*-api` 소유가 없는 data.go.kr OpenAPI도 함께 둡니다.

- 농촌진흥청 국립농업과학원 농업기상 관측지점 상세정보: `1390802/AgriWeather/getObsrSpotList`
- 한국수자원공사 수문 운영 정보: `B500001/dam/sluicePresentCondition/*`

## Quick Start

```python
from datagokr import DataGoKrClient

with DataGoKrClient() as client:
    page = client.museum_art.list(num_of_rows=10)
    print(page.total_count, page.items[0].fclty_nm)
```

인증키는 `DataGoKrClient(api_key="...")`로 직접 넘기거나 `DATA_GO_KR_SERVICE_KEY`
환경변수에 설정합니다. data.go.kr 엔드포인트 서비스키 환경변수는 이 이름으로 통일합니다.

`.env`는 저장소에 포함하지 않습니다.
