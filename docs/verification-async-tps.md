# 비동기/TPS 전환 검증

- 독립 적대적 리뷰 2인: 구현 승인. 서비스·페이지 순회·디버그·저장 동작 보존 확인.
- WSL 오프라인: 47개 테스트 및 14개 subtest 통과, Ruff/mypy 통과.
- live E2E: 박물관/미술관, 주차장, 관광지, 축제 4개 정상 응답 검증 통과.
- `special_street`, `agri_weather.station_list`, `kwater_sluice.hour_list`: HTTP 403.
- 안산 세계음식점 ODCloud 파일 API: HTTP 401.
- 특화거리 403과 ODCloud 401은 변경 전 코드에서도 동일하게 재현되었다.
- 2026-09-14 사용자가 위 403 API를 사용하지 않으며 안산 세계음식점 오류도 무시해도
  된다고 명시하고 머지를 승인했다. 실패 2개 및 skip 2개를 성공으로 계산하지 않는다.
