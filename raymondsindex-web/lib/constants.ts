// RaymondsIndex v2.1 등급 색상 및 상수 정의

/**
 * v2.1 등급 기준 (완화됨):
 * - A++: 95-100 (최우수)
 * - A+:  88-94  (우수)
 * - A:   80-87  (양호)
 * - A-:  72-79  (양호-)
 * - B+:  64-71  (보통+)
 * - B:   55-63  (보통)
 * - B-:  45-54  (보통-)
 * - C+:  30-44  (주의)
 * - C:   0-29   (위험)
 */
export const GRADE_COLORS = {
  'A++': { bg: '#1E40AF', text: 'white', label: '최우수' },
  'A+': { bg: '#2563EB', text: 'white', label: '우수' },
  'A': { bg: '#3B82F6', text: 'white', label: '양호' },
  'A-': { bg: '#60A5FA', text: 'white', label: '양호-' },
  'B+': { bg: '#22C55E', text: 'white', label: '보통+' },
  'B': { bg: '#84CC16', text: 'white', label: '보통' },
  'B-': { bg: '#EAB308', text: 'black', label: '보통-' },
  'C+': { bg: '#F97316', text: 'white', label: '주의' },
  'C': { bg: '#EF4444', text: 'white', label: '위험' },
} as const;

export type Grade = keyof typeof GRADE_COLORS;

export const GRADE_ORDER: Grade[] = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'];

/**
 * v3.1 Sub-Index 구성 (2026-01-22 Option C 최적화 적용):
 * - CEI (45%): 자산회전율(25%) + 유형자산효율성(20%) + 현금수익률(20%) + ROIC(25%) + 추세(10%)
 * - RII (10%): CAPEX강도(25%) + 투자괴리율(30%) + 재투자율(25%) + 지속성(20%)
 * - CGI (45%): 현금활용도(20%) + 자금조달효율성(25%) + 주주환원균형(20%) + 현금적정성(15%) + 부채건전성(20%)
 * - MAI (0%):  종합 점수에서 제외 (실패 예측에 무관함 확인)
 *
 * Option C 결과: AUC 0.837, F1 0.650 (Tier 1 실패기업 571개 기반)
 */
export const SUB_INDEX_INFO = {
  CEI: {
    name: 'Capital Efficiency Index',
    label: '자본 효율성',
    weight: 45,  // v3.1: 20% → 45% (핵심 지표)
    description: '투입한 자본 대비 수익 창출 능력을 평가합니다. 자산회전율, 유형자산효율성, 현금수익률, ROIC를 종합 평가합니다.',
    components: '자산회전율(25%) + 유형자산효율성(20%) + 현금수익률(20%) + ROIC(25%) + 추세(10%)'
  },
  RII: {
    name: 'Reinvestment Intensity Index',
    label: '재투자 강도',
    weight: 10,  // v3.1: 35% → 10% (역방향 관계 보정)
    description: '벌어들인 이익을 성장에 재투자하는지 평가합니다. 투자괴리율이 핵심 지표입니다.',
    components: 'CAPEX강도(25%) + 투자괴리율(30%) + 재투자율(25%) + 지속성(20%)'
  },
  CGI: {
    name: 'Cash Governance Index',
    label: '현금 거버넌스',
    weight: 45,  // v3.1: 25% → 45% (핵심 지표)
    description: '보유 현금을 생산적 자산으로 전환하는지 평가합니다. 부채 건전성도 포함됩니다.',
    components: '현금활용도(20%) + 자금조달효율성(25%) + 주주환원균형(20%) + 현금적정성(15%) + 부채건전성(20%)'
  },
  MAI: {
    name: 'Momentum Alignment Index',
    label: '모멘텀 정합성',
    weight: 0,   // v3.1: 20% → 0% (종합점수 계산에서 제외)
    description: '매출 성장과 투자 방향이 일치하는지 평가합니다. (v3.1에서 종합점수 계산 제외)',
    components: '매출-투자동조성(30%) + 이익품질(25%) + 성장투자비율(15%) + FCF추세(10%) + CAPEX추세(20%)'
  },
} as const;

// 핵심 지표 설명 (v2.1 위험요소 파악 관점)
export const METRIC_DESCRIPTIONS = {
  investment_gap: {
    label: '투자괴리율 (레거시)',
    description: '현금 증가 대비 투자 증가 차이입니다. (구버전 호환용)',
  },
  investment_gap_v2: {
    label: '투자괴리율 v2 (레거시)',
    description: '초기 2년 재투자율 대비 최근 2년 재투자율 변화입니다. (v2.0 호환용)',
  },
  investment_gap_v21: {
    label: '투자괴리율',
    description: '현금 CAGR - CAPEX 성장률입니다. 양수(+)면 현금만 쌓고 투자는 안 하는 것이고, 음수(-)면 적극 투자 중입니다. 핵심 지표입니다.',
  },
  reinvestment_rate: {
    label: '재투자율',
    description: '영업현금흐름(OCF) 대비 설비투자(CAPEX) 비율입니다. 40-80%가 적정합니다.',
  },
  roic: {
    label: 'ROIC',
    description: '투하자본수익률로, 투자금이 얼마나 효율적으로 수익을 창출하는지 보여줍니다. 8% 이상이 양호합니다.',
  },
  cash_utilization: {
    label: '현금 활용도',
    description: '(CAPEX + 배당 + 자사주매입) / (기초현금 + 영업현금흐름)입니다. 60-90%가 적정합니다.',
  },
  cash_tangible_ratio: {
    label: '현금/유형자산 비율',
    description: '현금 증가 대비 유형자산 증가 비율입니다. 30:1 이상이면 투자 없이 현금만 쌓고 있는 위험 신호입니다.',
  },
  short_term_ratio: {
    label: '단기금융비율',
    description: '현금 중 단기금융상품 비율입니다. 65% 이상이면 이자놀이에 투자금을 묶어두고 있을 가능성이 있습니다.',
  },
  shareholder_return: {
    label: '주주환원율',
    description: '배당 및 자사주 매입 비율입니다. 20-50%가 적정합니다.',
  },
  idle_cash_ratio: {
    label: '유휴현금비율',
    description: '총자산 대비 현금성자산 비율입니다. 10-20%가 적정합니다.',
  },
  fundraising_utilization: {
    label: '조달자금 전환율',
    description: '조달한 자금 대비 투자 전환 비율입니다. 30% 미만이면 조달금을 목적대로 사용하지 않는 위험 신호입니다.',
  },
  capex_cv: {
    label: 'CAPEX 변동계수',
    description: '투자의 일관성을 측정합니다. 0.25 이하가 안정적입니다.',
  },
  capex_trend: {
    label: 'CAPEX 추세',
    description: '투자 규모의 추세입니다. 지속적 감소는 성장 의지 약화를 나타낼 수 있습니다.',
  },
  // v2.1 신규 지표
  tangible_efficiency: {
    label: '유형자산 효율성',
    description: '매출 / 유형자산입니다. 유형자산이 얼마나 효율적으로 매출을 창출하는지 보여줍니다.',
  },
  cash_yield: {
    label: '현금 수익률',
    description: '영업이익 / 보유현금(%)입니다. 현금 대비 수익 창출 능력을 보여줍니다.',
  },
  debt_to_ebitda: {
    label: '부채/EBITDA',
    description: '총부채 / EBITDA 비율입니다. 3 이하가 양호하고, 5 이상이면 부채 부담이 큽니다.',
  },
  growth_investment_ratio: {
    label: '성장 투자 비율',
    description: '성장 CAPEX / 총 CAPEX(%)입니다. 높을수록 미래 지향적 투자입니다.',
  },
} as const;

export const STATUS_COLORS = {
  good: { bg: 'bg-green-100', text: 'text-green-700', icon: 'text-green-500' },
  warning: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: 'text-yellow-500' },
  danger: { bg: 'bg-red-100', text: 'text-red-700', icon: 'text-red-500' },
  neutral: { bg: 'bg-gray-100', text: 'text-gray-700', icon: 'text-gray-500' },
} as const;

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';
