# python-datagokr-api

TripMate에서 쓰는 공공데이터포털(data.go.kr) 표준데이터 Open API를 작은 typed
Python client로 감싼 라이브러리입니다.

현재 포함한 표준데이터셋은 아래 네 가지입니다.

- 전국박물관미술관정보표준데이터: `tn_pubr_public_museum_artgr_info_api`
- 전국주차장정보표준데이터: `tn_pubr_prkplce_info_api`
- 전국관광지정보표준데이터: `tn_pubr_public_trrsrt_api`
- 전국문화축제표준데이터: `tn_pubr_public_cltur_fstvl_api`

## Quick Start

```python
from datagokr import DataGoKrClient

with DataGoKrClient() as client:
    page = client.museum_art.list(num_of_rows=10)
    print(page.total_count, page.items[0].fclty_nm)
```

인증키는 `DataGoKrClient(api_key="...")`로 직접 넘기거나 아래 환경변수 중 하나에
설정합니다.

- `DATAGOKR_API_KEY`
- `DATA_GO_KR_SERVICE_KEY`
- `PUBLIC_DATA_SERVICE_KEY`
- `SERVICE_KEY`

`.env`는 저장소에 포함하지 않습니다.

