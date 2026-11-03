# Changelog

이 프로젝트의 주목할 만한 변경 사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 이
프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

### Fixed

- 공공주차장 응답의 `insttCode`·`insttNm`을 기관 코드·기관명 필드로 파싱해 기관별 주차장 식별자를 보존한다. 기존 `instt_code`·`instt_nm` 입력도 계속 지원한다.

### Added

- `client.parking.iter_file_pages()`로 전국주차장정보표준데이터의 공식 파일 다운로드를
  서비스키 없이 조회한다. 키가 설정돼 있어도 다운로드 요청에는 전달하지 않는다.
  전체 건수·페이지 길이·5만 건 다운로드 상한·수집 전후 메타데이터를 검산하며 원문을 보존한다.

- `DataGoKrClient.train`에 TAGO 열차정보(15098552)의 도시·차량종류·역·예정 운행편
  비동기 조회를 추가한다. 실제 승인 확인은 별도이며 오프라인 계약 테스트로 검증한다.

- `DataGoKrClient.express_bus`와 `DataGoKrClient.intercity_bus`에 TAGO 터미널·도시·등급
  목록과 출발/도착 터미널 기준 운행정보 typed async 조회를 추가한다.

### Changed
- TAGO 버스·열차의 성공 코드/본문/건수 계약을 검증한다. 비정상 응답은
  `ResponseParseError`로 구분하고 빈 `item`을 가짜 행으로 만들지 않는다.
- 열차 요금의 음수·불리언 값을 거부하고 날짜 객체를 항상 8자리로 직렬화한다.
- DataGoKrClient의 모든 조회·debug·저장을 async로 전환하고 페이지 순회를 async for로 제공한다.
- close()/동기 context manager를 aclose()/async with로 교체한다.
- 동일 AsyncTokenBucket으로 전체 서비스·HTTP 재시도·redirect의 TPS를 제어한다.
- max_rps(기본 5)와 공유 rate_limiter를 지원하고 전송 오류의 인증키 노출을 방지한다.


### Changed

- 문서 구조를 형제 저장소(`kor-travel-geo`) 컨벤션에 맞춰 재정리. `README.md`에
  배지, 제공 표면 표, 먼저 읽을 문서 표, 법적 고지를 추가하고 `docs/decisions.md`,
  `CHANGELOG.md`를 신설.
