// RaymondsIndex 등급 색상 및 상수 정의

export const GRADE_COLORS = {
  'A++': { bg: '#1E40AF', text: 'white', label: '최고 효율' },
  'A+': { bg: '#2563EB', text: 'white', label: '매우 우수' },
  'A': { bg: '#3B82F6', text: 'white', label: '우수' },
  'A-': { bg: '#60A5FA', text: 'white', label: '양호' },
  'B+': { bg: '#22C55E', text: 'white', label: '평균 이상' },
  'B': { bg: '#84CC16', text: 'white', label: '평균' },
  'B-': { bg: '#EAB308', text: 'black', label: '평균 이하' },
  'C+': { bg: '#F97316', text: 'white', label: '주의 필요' },
  'C': { bg: '#EF4444', text: 'white', label: '심각한 문제' },
} as const;

export type Grade = keyof typeof GRADE_COLORS;

export const GRADE_ORDER: Grade[] = ['A++', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'];

export const SUB_INDEX_INFO = {
  CEI: {
    name: 'Capital Efficiency Index',
    label: '자본 효율성',
    weight: 15,
    description: '투입한 자본 대비 수익 창출 능력을 평가합니다. 자본 효율성이 낮으면 투자금이 성장에 기여하지 못하고 있을 수 있습니다.'
  },
  RII: {
    name: 'Reinvestment Intensity Index',
    label: '재투자 강도',
    weight: 40,
    description: '벌어들인 이익을 성장에 재투자하는지 평가합니다. 재투자가 부족하면 현금만 쌓아두며 성장 기회를 놓치고 있을 수 있습니다.'
  },
  CGI: {
    name: 'Cash Governance Index',
    label: '현금 거버넌스',
    weight: 30,
    description: '보유 현금을 생산적 자산으로 전환하는지 평가합니다. 단기금융상품에만 묻어두면 투자금이 유용될 위험이 있습니다.'
  },
  MAI: {
    name: 'Momentum Alignment Index',
    label: '모멘텀 정합성',
    weight: 15,
    description: '매출 성장과 투자 방향이 일치하는지 평가합니다. 불일치하면 경영진의 자본 배분 판단에 의문이 생깁니다.'
  },
} as const;

// 핵심 지표 설명 (위험요소 파악 관점)
export const METRIC_DESCRIPTIONS = {
  investment_gap: {
    label: '투자괴리율',
    description: '현금 증가 대비 투자 증가 차이입니다. 괴리율이 높으면 현금만 쌓고 투자는 안 하고 있을 가능성이 있습니다.',
  },
  reinvestment_rate: {
    label: '재투자율',
    description: '영업이익 대비 설비투자 비율입니다. 재투자율이 낮으면 성장에 대한 의지가 부족할 수 있습니다.',
  },
  roic: {
    label: 'ROIC',
    description: '투하자본수익률로, 투자금이 얼마나 효율적으로 수익을 창출하는지 보여줍니다. 낮으면 투자 효율성 문제입니다.',
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
    description: '배당 및 자사주 매입 비율입니다. 적정 수준의 주주환원은 건전한 자본 정책을 의미합니다.',
  },
  idle_cash_ratio: {
    label: '유휴현금비율',
    description: '총자산 대비 현금성자산 비율입니다. 과도하면 현금을 활용하지 않고 방치하는 것입니다.',
  },
  fundraising_utilization: {
    label: '조달자금 전환율',
    description: '조달한 자금 대비 투자 전환 비율입니다. 30% 미만이면 조달금을 목적대로 사용하지 않는 위험 신호입니다.',
  },
  capex_cv: {
    label: 'CAPEX 변동계수',
    description: '투자의 일관성을 측정합니다. 변동이 크면 투자 계획이 불안정하고 예측 가능성이 낮습니다.',
  },
  capex_trend: {
    label: 'CAPEX 추세',
    description: '투자 규모의 추세입니다. 지속적 감소는 성장 의지 약화를 나타낼 수 있습니다.',
  },
} as const;

export const STATUS_COLORS = {
  good: { bg: 'bg-green-100', text: 'text-green-700', icon: 'text-green-500' },
  warning: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: 'text-yellow-500' },
  danger: { bg: 'bg-red-100', text: 'text-red-700', icon: 'text-red-500' },
  neutral: { bg: 'bg-gray-100', text: 'text-gray-700', icon: 'text-gray-500' },
} as const;

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://raymontology-production.up.railway.app/api';
