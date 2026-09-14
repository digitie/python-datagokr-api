# 비동기 호출과 TPS 제어

`DataGoKrClient`의 서비스 속성 이름과 응답 모델은 유지하며 네트워크 호출을 async로
전환했다. `list()`, 각 서비스 조회, `debug_fetch()`는 await가 필요하다.
`iter_pages()`와 `iter_all()`은 비동기 순회자이므로 async for를 사용한다.
연결 종료는 async with 또는 await client.aclose()를 사용한다.

`AsyncTokenBucket`은 표준 라이브러리만 사용하는 동일한 공통 구현이다.
`max_rps`는 유한한 양수, `capacity`는 유한한 1 이상의 수를 받으며 bool은 거절한다.
기본값은 5 TPS, 기본 용량은 max(1, max_rps)다. 초기 burst 이후 monotonic 시간에
비례해 충전하고 FIFO 순서로 대기한다. 대기 중 취소된 요청은 토큰을 소비하지 않는다.
한 버킷은 한 이벤트 루프에 연결되며 다른 루프에 재사용하면 오류를 낸다.

클라이언트 하나의 모든 서비스는 같은 버킷을 공유한다. 여러 클라이언트가 같은 공급자
quota를 공유할 때 rate_limiter 인자로 동일 인스턴스를 주입할 수 있다.
주입한 버킷은 max_rps 설정보다 우선한다. HTTP 재시도와 redirect마다 토큰을 추가로
획득하며, redirect의 메서드·쿠키·인증 헤더 처리는 HTTPX의 next_request를 따른다.
사용자가 주입한 DigestAuth/transport 내부의 추가 송신은 제어 범위 밖이다.

로컬 저장과 선택적 boto3 업로드는 await API를 제공하고 블로킹 작업을 작업 스레드에서
수행한다. boto3 내부 multipart/retry는 data.go.kr TPS 예산에 포함하지 않는다.
취소는 이미 시작한 작업 스레드의 저장·업로드까지 중단시키지 않는다.
카탈로그 조회, 응답 파싱, fixture 저장 등 네트워크 없는 유틸리티는 일반 함수다.

오프라인 테스트는 기존 응답 파싱·필터·페이지 종료 조건, async 종료,
서비스 간 예산 공유, 재시도·redirect별 과금, 인증키 마스킹, FIFO·취소를 검증한다.
live 테스트는 환경변수 DATA_GO_KR_SERVICE_KEY가 있을 때 별도로 실행한다.
