# heartopia-weather

두근두근타운의 한국시간(KST) 기준 날씨와 향후 7일 예보를 표시하는 정적 사이트입니다.

## 로컬 실행

저장소 루트에서 `python -m http.server 8000`을 실행한 뒤
`http://localhost:8000`에 접속합니다. JSON을 요청하므로 HTML 파일을
직접 여는 방식 대신 HTTP 서버를 사용합니다. 빌드나 npm 설치는 필요 없습니다.

## 구성

- `index.html`: 사이트 화면 구조
- `assets/weather.css`: PC·모바일 반응형 스타일
- `assets/weather-core.js`: 한국시간, 데이터 검증, 아이콘 대응표, 구간 계산
- `assets/weather-app.js`: 예보 로딩과 화면·시계·계산기·공지 동작
- `assets/redeem-ui.js`: 리딤코드 표시 및 팝업 동작
- `design-reference/icons-light.png`: 초기 디자인 참고 이미지
- `assets/canopy.png`, `assets/landscape.png`: 라이트 디자인 장식 이미지
- `weather.py`: Playwright 기반 날씨 수집기. GitHub Actions가 실행합니다.
- `weather.json`, `notice.json`: 공개 사이트에서 사용하는 예보와 공지 데이터

## 날씨 표시 기준

- 날짜는 **KST 달력 날짜 00:00~23:59** 기준입니다. 시간별 예보는 해당 날짜의 00~23시를 사용합니다.
- 주간 예보 카드는 **오늘을 제외한 다음 7일**을 표시합니다. 데이터 수집·검증 범위는 오늘부터 9개 연속 달력 날짜입니다.
- 날씨 시계는 현재 시간 기준으로 표시되며, Light/Midnight 테마를 지원합니다.
- 상세 예보는 날짜별 시간 목록 및 시간대별 묶어보기를 지원합니다.
- 계산기는 시작 시각 제외, 종료 시각 포함 기준을 사용합니다.
- 예보에 없는 날씨나 시간을 임의로 생성하지 않습니다.

## 리딤코드

리딤코드는 사용 가능/만료 목록, 복사, 신규 알림 등을 지원합니다.
공개 데이터는 `redeem-codes.json`과 `manual-redeem-codes.json`으로 관리합니다.

## 검증

```text
node --check assets/weather-core.js
node --check assets/weather-app.js
node tests/weather-core.test.cjs
python tests/test_weather_rules.py
python tests/browser_smoke.py
```

브라우저 검증에는 Python Playwright와 로컬 Microsoft Edge가 필요합니다.
검증용 임시 HTTP 서버는 실행 후 종료되며, 스크린샷은 시스템 임시 폴더에
저장됩니다. 테스트는 수집기를 실행하거나 실제 예보를 다시 쓰지 않습니다.

## 문서 관리

이 저장소는 공개 사이트 운영용입니다. 내부 개발 계획, 원본 게임 데이터 분석 및 패치 점검 기록은 별도 비공개 저장소에서 관리합니다.
