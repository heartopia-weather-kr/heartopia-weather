# heartopia-weather

두근두근타운의 한국시간 기준 7일 예보를 표시하는 정적 사이트입니다.

## 로컬 실행

저장소 루트에서 `python -m http.server 8000`을 실행한 뒤
`http://localhost:8000`에 접속합니다. JSON을 요청하므로 HTML 파일을
직접 여는 방식 대신 HTTP 서버를 사용합니다. 빌드나 npm 설치는 필요 없습니다.

## 구성

- `index.html`: 라이트 대시보드의 화면 구조
- `assets/weather.css`: PC·모바일 반응형 스타일
- `assets/weather-core.js`: 한국시간, 데이터 검증, 아이콘 대응표, 구간 계산
- `assets/weather-app.js`: 예보 로딩과 화면·시계·계산기·공지 동작
- `design-reference/icons-light.png`: 21종 아이콘 원본. SVG 표시 영역으로 원본을 사용합니다.
- `assets/canopy.png`, `assets/landscape.png`: 제공된 라이트 시안에서 잘라낸 장식입니다.
- `weather.py`: Playwright 기반 수집기. GitHub Actions가 실행합니다.
- `weather.json`, `notice.json`: 실제 예보와 공지

게임 날짜는 한국시간 06:00 ~ 다음 날 05:00입니다. 00·06·12·18시는
동일 날씨여도 변경으로 계산합니다. 계산기는 시작 시각을 제외하고
종료 시각까지 기존 변경 표시를 합산합니다. 일별 변동률의 분모는 24,
계산기 변동률의 분모는 선택한 시간 간격입니다.

7일 카드에는 특수 날씨가 있으면 첫 특수 날씨를, 없으면 06시 예보를
대표로 표시합니다. 날짜를 선택하면 시간별 예보와 시계가 바뀝니다.
시계의 낮·밤 선택은 예보 시간대이며 사이트 테마 전환이 아닙니다.

예보는 15분마다 다시 요청합니다. 마지막 갱신 후 2시간이 지나거나
현재 게임 날짜가 없으면 경고합니다. 데이터 로딩 실패 시 가짜 예보는
표시하지 않으며, 갱신 재시도 실패 시 이전에 불러온 데이터만 유지합니다.

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
