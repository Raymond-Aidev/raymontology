# RaymondsRisk 앱인토스 개발계획

> 작성일: 2025-12-30
> 상태: Phase 1 완료 ✅

---

## 1. 현황 분석 (Gap Analysis)

### 검수 필수 요구사항 vs 현재 상태

| 요구사항 | 현재 상태 | Gap |
|----------|:--------:|:---:|
| **TDS 컴포넌트 사용** | ✅ Top, Button, ListRow, Loader, Badge | Done |
| **내비게이션 바 (Top)** | ✅ 모든 페이지 적용 | Done |
| **토스 디자인 색상 시스템** | ⚠️ 일부 커스텀 색상 | Major |
| **토스 타이포그래피** | ⚠️ 일부 적용 | Major |
| **BottomCTA 레이아웃** | ❌ 미구현 | Major |
| **로딩/에러 상태 처리** | ✅ Loader 적용 | Done |
| **토스 로그인** | ❌ 미구현 | Optional |
| **토스페이 결제** | ❌ 미구현 | Optional |

---

## 2. 개발 우선순위

### Phase 1: 검수 필수 (Critical) ✅ 완료
> **목표: TDS 컴포넌트 기본 적용**

| 작업 | 상태 | 설명 |
|------|:----:|------|
| 1.1 TDS Provider 설정 | ✅ | @emotion/react, @emotion/styled 설치 |
| 1.2 Top 컴포넌트 | ✅ | 모든 페이지에 내비게이션 바 적용 |
| 1.3 Button → TDS Button | ✅ | primary, light 버튼 사용 |
| 1.4 TextField → TDS TextField | ⚠️ | 기본 input 유지 (Phase 2에서 개선) |
| 1.5 Card → TDS Card/ListRow | ✅ | ListRow.Texts 활용 |
| 1.6 Loader 컴포넌트 | ✅ | 검색 로딩 상태 표시 |
| 1.7 Badge 컴포넌트 | ✅ | 리스크 레벨 표시 |

### Phase 2: 디자인 정합성 (Major)
> **목표: TDS 디자인 시스템 완전 적용**

| 작업 | 상태 | 설명 |
|------|:----:|------|
| 2.1 색상 시스템 통일 | ⬜ | TDS Colors 사용 |
| 2.2 타이포그래피 적용 | ⬜ | TDS 폰트 시스템 |
| 2.3 BottomCTA | ⬜ | 하단 고정 버튼 영역 |
| 2.4 Spinner/Toast | ⬜ | 로딩/알림 컴포넌트 |

### Phase 3: 기능 완성 (Minor)
> **목표: UX 완성도 향상**

| 작업 | 상태 | 설명 |
|------|:----:|------|
| 3.1 에러 처리 UI | ⬜ | TDS Dialog 활용 |
| 3.2 빈 상태 UI | ⬜ | 검색 결과 없음 등 |
| 3.3 스켈레톤 로딩 | ⬜ | 데이터 로딩 중 UI |

### Phase 4: 선택 기능 (Optional)
> **목표: 고급 기능 (필요시)**

| 작업 | 상태 | 설명 | 필요 조건 |
|------|:----:|------|----------|
| 4.1 토스 로그인 | ⬜ | 사용자 인증 | mTLS 인증서 |
| 4.2 토스페이 결제 | ⬜ | 유료 서비스 | mTLS 인증서 |

---

## 3. 파일 구조

```
src/
├── components/
│   ├── Layout.tsx          # 공통 레이아웃 (Top 포함)
│   ├── StatCard.tsx        # TDS Card 기반 통계 카드
│   ├── FeatureCard.tsx     # TDS ListRow 기반 기능 카드
│   └── CompanyCard.tsx     # TDS ListRow 기반 기업 카드
├── pages/
│   ├── HomePage.tsx        # TDS 컴포넌트 적용
│   ├── SearchPage.tsx      # TDS 컴포넌트 적용
│   └── ReportPage.tsx      # TDS 컴포넌트 적용
├── api/
│   ├── client.ts           # API 클라이언트
│   └── company.ts          # 기업 API
├── types/
│   ├── company.ts          # 기업 타입
│   └── report.ts           # 리포트 타입
├── App.tsx                 # TDSProvider 추가
└── main.tsx                # 엔트리포인트
```

---

## 4. 검수 체크리스트

### 필수 (검수 통과 기준)
- [x] TDS Provider 설정 완료
- [x] 모든 페이지에 Top (내비게이션 바) 적용
- [x] Button, ListRow, Badge 등 TDS 컴포넌트 사용
- [ ] TDS 색상 시스템 완전 적용 (Phase 2)
- [x] 로딩 상태 Loader 적용
- [ ] 에러 상태 Dialog 적용 (Phase 3)
- [x] HTTPS 통신 확인 (Railway API)

### 권장
- [ ] 다크패턴 없음 확인
- [ ] 명확한 UX 라이팅
- [ ] 접근성 고려 (색상 대비 등)

---

## 5. 참고 문서

| 문서 | URL |
|------|-----|
| TDS Mobile 문서 | https://tossmini-docs.toss.im/tds-mobile/ |
| 앱인토스 개발자 문서 | https://developers-apps-in-toss.toss.im/ |
| 앱인토스 콘솔 | https://console.apps-in-toss.toss.im |

---

*이 문서는 개발 진행에 따라 업데이트됩니다.*
