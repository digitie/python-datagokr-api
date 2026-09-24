# Changelog

이 프로젝트의 주목할 만한 변경 사항을 이 파일에 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 이
프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

### Added

- `DataGoKrClient.express_bus`와 `DataGoKrClient.intercity_bus`에 TAGO 터미널·도시·등급
  목록과 출발/도착 터미널 기준 운행정보 typed async 조회를 추가한다.

### Changed
- DataGoKrClient의 모든 조회·debug·저장을 async로 전환하고 페이지 순회를 async for로 제공한다.
- close()/동기 context manager를 aclose()/async with로 교체한다.
- 동일 AsyncTokenBucket으로 전체 서비스·HTTP 재시도·redirect의 TPS를 제어한다.
- max_rps(기본 5)와 공유 rate_limiter를 지원하고 전송 오류의 인증키 노출을 방지한다.


### Changed

- 문서 구조를 형제 저장소(`kor-travel-geo`) 컨벤션에 맞춰 재정리. `README.md`에
  배지, 제공 표면 표, 먼저 읽을 문서 표, 법적 고지를 추가하고 `docs/decisions.md`,
  `CHANGELOG.md`를 신설.
