# RaymondsRisk 검수 통과 체크리스트

> 작성일: 2025-12-30
> 비게임 검수 가이드 기준 현황 분석

---

## 현재 상태 요약

| 카테고리 | 상태 | 설명 |
|----------|:----:|------|
| 시스템 모드 | ⚠️ | 라이트 모드 적용됨, 추가 확인 필요 |
| 내비게이션 바 | ❌ | 앱인토스 네이티브 NavBar 미연동 |
| 서비스 동작 | ⚠️ | 기본 기능 구현, 성능 검증 필요 |
| 접근성 | ⚠️ | 기본 적용, 상세 검토 필요 |
| 보안 | ✅ | HTTPS 통신 |

---

## 🔴 Critical: 반드시 수정 필요

### 1. viewport 핀치줌 방지 설정
**현재 상태**: 미적용
**요구사항**: 핀치줌 비활성화

```html
<!-- index.html 수정 필요 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
```

**파일**: `index.html`

---

### 2. html lang 속성 한국어 설정
**현재 상태**: `lang="en"`
**요구사항**: 한국어 서비스이므로 `lang="ko"` 필요

```html
<html lang="ko">
```

**파일**: `index.html`

---

### 3. 내비게이션 바 연동
**현재 상태**: 커스텀 헤더 사용
**요구사항**: 앱인토스 네이티브 NavBar 사용

**필요 작업**:
- `@apps-in-toss/web-framework`의 NavBar 컴포넌트 사용
- 브랜드 로고+이름 표시 (필수)
- 더보기 버튼 (필수)
- 닫기 버튼 (필수)

**파일**: `App.tsx`, 모든 페이지 컴포넌트

---

### 4. 앱 타이틀 변경
**현재 상태**: `raymondsrisk-app`
**요구사항**: 서비스명으로 변경

```html
<title>RaymondsRisk - 기업 리스크 분석</title>
```

**파일**: `index.html`

---

## 🟡 Major: 권장 수정 사항

### 5. 에러 처리 UI
**현재 상태**: 기본 에러 메시지만 표시
**요구사항**: 사용자 친화적 에러 화면

**필요 작업**:
- API 실패 시 재시도 버튼 제공
- 네트워크 오류 안내
- 서버 오류 안내

---

### 6. 로딩 상태 개선
**현재 상태**: 간단한 스피너
**요구사항**: 토스 스타일 로딩 (스켈레톤 UI 권장)

**필요 작업**:
- 검색 결과 스켈레톤 UI
- 리포트 페이지 스켈레톤 UI

---

### 7. 빈 상태 UI
**현재 상태**: 텍스트만 표시
**요구사항**: 친화적인 빈 상태 화면

**필요 작업**:
- 검색 결과 없음 일러스트/아이콘
- 검색 유도 메시지

---

### 8. 접근성 개선
**현재 상태**: 기본 수준
**요구사항**: 스크린 리더 지원, 명도 대비

**필요 작업**:
- 버튼에 `aria-label` 추가
- 이미지에 `alt` 텍스트
- 터치 영역 최소 44x44px 확보
- 색상 대비 비율 확인 (4.5:1 이상)

---

### 9. 재접속 시 데이터 유지
**현재 상태**: URL 파라미터로 일부 유지
**요구사항**: 검색어, 스크롤 위치 등 유지

**필요 작업**:
- 검색어 세션 스토리지 저장
- 스크롤 위치 복원

---

### 10. 응답 속도 검증
**요구사항**: 스크롤/인터랙션 반응 2초 이내

**필요 작업**:
- API 응답 시간 모니터링
- 느린 네트워크 환경 테스트

---

## 🟢 Minor: 선택 사항

### 11. 파비콘 변경
**현재 상태**: Vite 기본 아이콘
**권장**: RaymondsRisk 브랜드 아이콘

---

### 12. 메타 태그 추가
**권장**: SEO 및 공유용 메타 태그

```html
<meta name="description" content="RaymondsRisk - 기업 관계형 리스크 분석 서비스">
<meta name="theme-color" content="#ffffff">
```

---

## 해당 없음 (N/A)

| 항목 | 사유 |
|------|------|
| 토스 로그인 | 로그인 기능 없음 (무료 서비스) |
| 토스페이 | 결제 기능 없음 |
| 인앱결제 | 결제 기능 없음 |
| 프로모션 | 이벤트 없음 |
| 기능성 메시지 | 푸시 알림 없음 |
| 인앱광고 | 광고 없음 |

---

## 즉시 적용 가능한 수정

### index.html 수정

```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="description" content="RaymondsRisk - 기업 관계형 리스크 분석 서비스">
    <meta name="theme-color" content="#ffffff">
    <title>RaymondsRisk</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## 검수 통과 우선순위

| 우선순위 | 작업 | 예상 소요 |
|:--------:|------|----------|
| 1 | index.html 메타 태그 수정 | 5분 |
| 2 | 앱인토스 NavBar 연동 | 2시간 |
| 3 | 에러 처리 UI | 1시간 |
| 4 | 접근성 aria-label 추가 | 30분 |
| 5 | 스켈레톤 로딩 UI | 1시간 |

---

## 참고

- [비게임 가이드라인](https://developers-apps-in-toss.toss.im/checklist/app-nongame.html)
- [서비스 오픈 프로세스](https://developers-apps-in-toss.toss.im/intro/onboarding-process.html)

---

*검수 평균 소요시간: 2~3일*
