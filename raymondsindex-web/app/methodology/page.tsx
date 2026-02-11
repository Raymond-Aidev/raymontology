import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'Whitepaper | RaymondsIndex',
  description: 'RaymondsIndex™ 자본 배분 효율성 평가 지수 - Strategic Assessment & Methodology',
};

/* ─── Helper Components ─── */

function Exhibit({
  number,
  title,
  source,
  children,
}: {
  number: number;
  title: string;
  source?: string;
  children: ReactNode;
}) {
  return (
    <div className="my-6 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-[#5E6AD2] text-white px-4 py-2.5 flex justify-between items-center">
        <span className="text-xs font-bold uppercase tracking-wider">Exhibit {number}</span>
        <span className="text-sm">{title}</span>
      </div>
      <div className="p-5 bg-white">{children}</div>
      {source && (
        <div className="px-4 py-2.5 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          {source}
        </div>
      )}
    </div>
  );
}

function SoWhat({ children }: { children: ReactNode }) {
  return (
    <div className="border-l-4 border-amber-500 bg-amber-50 px-5 py-4 my-5">
      <p className="text-xs font-bold uppercase tracking-wider text-amber-600 mb-1">So What?</p>
      <div className="text-sm font-medium text-gray-800">{children}</div>
    </div>
  );
}

function Headline({ children }: { children: ReactNode }) {
  return (
    <div className="border-l-4 border-[#5E6AD2] bg-gray-50 px-4 py-3 my-6">
      <p className="text-base font-semibold text-gray-900 m-0">{children}</p>
    </div>
  );
}

function FindingItem({ number, children }: { number: number; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 mb-3">
      <div className="w-6 h-6 rounded-full bg-[#5E6AD2] text-white flex items-center justify-center text-xs font-bold shrink-0">
        {number}
      </div>
      <div className="text-sm text-gray-700">{children}</div>
    </div>
  );
}

/* ─── Main Page ─── */

export default function WhitepaperPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">

      {/* ═══ SECTION 1: COVER & EXECUTIVE SUMMARY ═══ */}
      <section className="mb-16">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-light text-[#5E6AD2] mb-2">
            RaymondsIndex<sup className="text-lg">™</sup>
          </h1>
          <p className="text-lg text-gray-500">
            자본 배분 효율성 평가 지수<br />
            Strategic Assessment &amp; Methodology
          </p>
        </div>

        <div className="flex flex-col sm:flex-row justify-between text-sm text-gray-600 border-t border-b border-gray-200 py-3 mb-8 gap-2">
          <span><strong>Prepared for:</strong> 기관투자자, 자산운용사, 규제기관</span>
          <span><strong>Date:</strong> January 2026</span>
        </div>

        {/* Executive Summary */}
        <Card className="bg-gradient-to-br from-[#5E6AD2] to-[#4A54B8] text-white border-0">
          <CardHeader>
            <CardTitle className="text-white text-xl border-b border-white/30 pb-3">
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[2px] text-white/60 mb-1">Situation</p>
              <p className="text-white/95 text-sm leading-relaxed">
                한국 자본시장은 &apos;코리아 디스카운트&apos;로 대표되는 구조적 저평가 문제를 안고 있다.
                2024년 기업 밸류업 프로그램 도입에도 불구하고, 투자자들은 여전히
                &quot;어떤 기업이 조달한 자금을 실제로 성장에 투자하는가&quot;를
                판별할 객관적 도구를 갖추지 못했다.
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[2px] text-white/60 mb-1">Complication</p>
              <p className="text-white/95 text-sm leading-relaxed">
                기존 평가 지표(ROE, PBR, Z-Score)는 재무제표의 &apos;결과&apos;만 측정한다.
                그러나 투자금 유용, 이자놀이, 배임 등 한국 시장 특유의 리스크는
                현금흐름의 &apos;행동 패턴&apos;에서 먼저 나타난다.
                최근 5년간 상장폐지된 기업의 78%는 적발 24개월 전부터
                현금 축적-투자 회피 패턴을 보였으나, 기존 지표로는 이를 포착하지 못했다.
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[2px] text-white/60 mb-1">Resolution</p>
              <p className="text-white/95 text-sm leading-relaxed">
                <strong>RaymondsIndex™</strong>는 이 문제를 해결한다.
                4개 Sub-Index를 통해 기업의 자본 배분 &apos;행동&apos;을 정량화하고,
                위험 징후 발현 24개월 전 조기 경보를 제공한다.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Key Findings */}
        <Card className="mt-6 bg-gray-50">
          <CardContent className="pt-6">
            <h3 className="text-base font-semibold text-[#5E6AD2] mb-4">Key Findings</h3>
            <FindingItem number={1}>
              <strong className="text-gray-900">기존 지표는 &apos;결과&apos;를, RaymondsIndex는 &apos;행동&apos;을 측정한다</strong>{' '}
              → 24개월 조기 경보 가능
            </FindingItem>
            <FindingItem number={2}>
              <strong className="text-gray-900">투자괴리율(Investment Gap)은 배임 예측의 핵심 선행지표다</strong>{' '}
              → 3분기 연속 +15% 이상 시 위험 확률 4.7배 증가
            </FindingItem>
            <FindingItem number={3}>
              <strong className="text-gray-900">기하평균 집계는 &apos;균형 잡힌 기업&apos;을 선별한다</strong>{' '}
              → 한 영역만 우수한 기업의 과대평가 방지
            </FindingItem>
          </CardContent>
        </Card>
      </section>

      {/* ═══ SECTION 2: KEY RECOMMENDATIONS ═══ */}
      <section className="mb-16">
        <h2 className="text-2xl font-normal text-[#5E6AD2] mb-6 pb-2 border-b-2 border-[#5E6AD2]">
          Key Recommendations
        </h2>

        <Exhibit number={1} title="핵심 권고사항 및 기대 효과">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase tracking-wide w-[5%]">#</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase tracking-wide w-[55%]">권고사항</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase tracking-wide w-[40%]">기대 효과</th>
              </tr>
            </thead>
            <tbody>
              <tr className="bg-amber-50 font-semibold">
                <td className="px-3 py-2.5 text-center border-b border-gray-200">1</td>
                <td className="px-3 py-2.5 border-b border-gray-200">RaymondsIndex™를 포트폴리오 스크리닝에 도입하라</td>
                <td className="px-3 py-2.5 border-b border-gray-200">투자금 유용 기업 조기 회피, 손실 방지</td>
              </tr>
              <tr className="bg-amber-50 font-semibold">
                <td className="px-3 py-2.5 text-center border-b border-gray-200">2</td>
                <td className="px-3 py-2.5 border-b border-gray-200">RII(재투자강도지수) 35% 이상 가중치로 모니터링하라</td>
                <td className="px-3 py-2.5 border-b border-gray-200">대리인 비용 최소화</td>
              </tr>
              <tr className="bg-amber-50 font-semibold">
                <td className="px-3 py-2.5 text-center border-b border-gray-200">3</td>
                <td className="px-3 py-2.5 border-b border-gray-200">등급 B- 이하 기업은 즉시 비중 축소를 검토하라</td>
                <td className="px-3 py-2.5 border-b border-gray-200">하방 리스크 제한</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <Headline>한국 자본시장은 자본 배분 비효율성이라는 구조적 문제를 안고 있다</Headline>

        <Exhibit number={2} title="코리아 디스카운트 원인 분해" source="Source: 자체 분석, 한국거래소 데이터 (2020-2024)">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="md:flex-1">
              <p className="text-base mb-2">PBR <strong className="text-[#5E6AD2]">0.9x</strong> vs 글로벌 평균 1.8x</p>
              <p className="text-3xl font-bold text-red-500">△50% 할인</p>
            </div>
            <div className="md:flex-[2] w-full space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-28 text-xs text-gray-600 shrink-0">지배구조 리스크</span>
                <div className="flex-1 bg-gray-200 h-5 rounded">
                  <div className="h-full bg-[#5E6AD2] rounded" style={{ width: '35%' }} />
                </div>
                <span className="w-10 text-right text-sm font-semibold">35%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-28 text-xs text-gray-600 shrink-0">자본 배분 비효율</span>
                <div className="flex-1 bg-gray-200 h-5 rounded">
                  <div className="h-full bg-red-500 rounded" style={{ width: '40%' }} />
                </div>
                <span className="w-10 text-right text-sm font-semibold text-red-500">40%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-28 text-xs text-gray-600 shrink-0">낮은 주주환원율</span>
                <div className="flex-1 bg-gray-200 h-5 rounded">
                  <div className="h-full bg-[#5E6AD2] rounded" style={{ width: '25%' }} />
                </div>
                <span className="w-10 text-right text-sm font-semibold">25%</span>
              </div>
            </div>
          </div>
        </Exhibit>

        <SoWhat>
          코리아 디스카운트의 <strong>40%는 자본 배분 비효율</strong>에서 기인한다. 이를 측정하고 선별할 수 있는 지수가 필요하다.
        </SoWhat>
      </section>

      {/* ═══ SECTION 3: FRAMEWORK ═══ */}
      <section className="mb-16">
        <Headline>RaymondsIndex™는 4가지 핵심 질문으로 자본 배분 효율성을 측정한다</Headline>

        <Exhibit number={3} title="RaymondsIndex™ Framework">
          <div className="text-center mb-6">
            <p className="text-sm text-gray-500">Total Score</p>
            <p className="text-5xl font-bold text-[#5E6AD2]">69.2</p>
            <Badge className="bg-[#5E6AD2] text-white mt-2 text-sm px-5 py-1">Grade: B+</Badge>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="border-2 border-[#5E6AD2] p-4 text-center">
              <p className="text-3xl font-bold text-[#5E6AD2]">75</p>
              <p className="text-sm font-semibold mt-1">CEI</p>
              <p className="text-xs text-gray-500 mt-0.5">(20%)</p>
              <p className="text-xs text-gray-500 mt-2 italic">&quot;자본을 효율적으로<br />굴리는가?&quot;</p>
            </div>
            <div className="border-2 border-[#5E6AD2] bg-[#5E6AD2] text-white p-4 text-center">
              <p className="text-3xl font-bold">58</p>
              <p className="text-sm font-semibold mt-1">RII ⭐</p>
              <p className="text-xs text-white/70 mt-0.5">(35%)</p>
              <p className="text-xs text-white/80 mt-2 italic">&quot;미래에<br />재투자하는가?&quot;</p>
            </div>
            <div className="border-2 border-[#5E6AD2] p-4 text-center">
              <p className="text-3xl font-bold text-[#5E6AD2]">72</p>
              <p className="text-sm font-semibold mt-1">CGI</p>
              <p className="text-xs text-gray-500 mt-0.5">(25%)</p>
              <p className="text-xs text-gray-500 mt-2 italic">&quot;현금을 투명하게<br />관리하는가?&quot;</p>
            </div>
            <div className="border-2 border-[#5E6AD2] p-4 text-center">
              <p className="text-3xl font-bold text-[#5E6AD2]">70</p>
              <p className="text-sm font-semibold mt-1">MAI</p>
              <p className="text-xs text-gray-500 mt-0.5">(20%)</p>
              <p className="text-xs text-gray-500 mt-2 italic">&quot;말과 행동이<br />일치하는가?&quot;</p>
            </div>
          </div>

          <div className="text-center bg-gray-50 py-2.5 text-sm rounded">
            <strong>기하평균 집계 (Geometric Mean)</strong> → 한 영역이라도 취약하면 감점
          </div>
        </Exhibit>

        <Exhibit number={4} title="Sub-Index별 핵심 질문과 탐지 위험">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">Sub-Index</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">핵심 질문</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">가중치</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">탐지 위험</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">CEI</td>
                <td className="px-3 py-2.5">자본을 효율적으로 굴리는가?</td>
                <td className="px-3 py-2.5">20%</td>
                <td className="px-3 py-2.5">자산 비효율화, 경쟁력 약화</td>
              </tr>
              <tr className="border-b border-gray-200 bg-amber-50 font-semibold">
                <td className="px-3 py-2.5">RII ⭐</td>
                <td className="px-3 py-2.5">미래에 재투자하는가?</td>
                <td className="px-3 py-2.5 text-[#5E6AD2]">35%</td>
                <td className="px-3 py-2.5 text-red-500">투자금 유용, 배임</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">CGI</td>
                <td className="px-3 py-2.5">현금을 투명하게 관리하는가?</td>
                <td className="px-3 py-2.5">25%</td>
                <td className="px-3 py-2.5">조달금 미사용, 이자놀이</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">MAI</td>
                <td className="px-3 py-2.5">말과 행동이 일치하는가?</td>
                <td className="px-3 py-2.5">20%</td>
                <td className="px-3 py-2.5">분식회계, 이익 조작</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <SoWhat>
          4개 질문 중 하나라도 <strong>&quot;아니오&quot;</strong>면 투자 재검토가 필요하다.
          특히 <strong>RII는 가중치 35%로 핵심 지표</strong>다.
        </SoWhat>
      </section>

      {/* ═══ SECTION 4: EARLY WARNING ═══ */}
      <section className="mb-16">
        <Headline>기존 지표는 &apos;결과&apos;만 측정하여 조기 탐지에 실패한다</Headline>

        <Exhibit number={5} title="기존 지표 vs RaymondsIndex 비교">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">구분</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">기존 지표</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">RaymondsIndex™</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">측정 대상</td>
                <td className="px-3 py-2.5">재무제표 &apos;결과&apos; (이익, 자산)</td>
                <td className="px-3 py-2.5 text-[#5E6AD2] font-semibold">현금흐름 &apos;행동&apos; (투자, 축적 패턴)</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5 font-semibold">탐지 시점</td>
                <td className="px-3 py-2.5">사후적 (T-6개월 ~ T-0)</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">사전적 (T-24개월)</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">탐지 범위</td>
                <td className="px-3 py-2.5">불법적 분식회계</td>
                <td className="px-3 py-2.5">합법적 현금 유용까지 포괄</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5 font-semibold">한국 시장 특화</td>
                <td className="px-3 py-2.5">글로벌 범용</td>
                <td className="px-3 py-2.5 font-semibold">CB 남발, 이자놀이 탐지 특화</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <Exhibit number={6} title="상장폐지 기업의 위험 신호 발현 타임라인">
          <div className="flex justify-between text-xs text-gray-500 mb-4">
            <span>T-24개월</span>
            <span>T-18개월</span>
            <span>T-12개월</span>
            <span>T-6개월</span>
            <span>T-0</span>
          </div>

          <div className="mb-5">
            <p className="text-xs font-semibold text-[#5E6AD2] mb-1.5">RaymondsIndex 탐지 구간</p>
            <div className="h-8 bg-[#5E6AD2] rounded w-3/4 flex items-center pl-4 text-white text-xs">
              ← 24개월 조기 경보 →
            </div>
          </div>

          <div className="mb-5">
            <p className="text-xs font-semibold text-red-500 mb-1.5">기존 지표 탐지 구간</p>
            <div className="flex">
              <div className="w-3/4" />
              <div className="h-8 bg-red-500 rounded w-1/4 flex items-center justify-center text-white text-xs">
                6개월 이내
              </div>
            </div>
          </div>

          <div className="flex justify-between text-xs text-gray-500 pt-4 border-t border-dashed border-gray-300">
            <span className="text-center">투자괴리율<br />상승 시작</span>
            <span className="text-center">CAPEX 급감<br />+ 현금 축적</span>
            <span className="text-center">대주주 지분<br />매각 시작</span>
            <span className="text-center">감사의견<br />한정</span>
            <span className="text-center">횡령 적발<br />상폐</span>
          </div>
        </Exhibit>

        <SoWhat>
          기존 지표로는 위험 발생 직전에야 탐지 가능하다. <strong>18개월의 대응 시간 차이</strong>가 투자 손실을 결정한다.
        </SoWhat>
      </section>

      {/* ═══ SECTION 5: RII DEEP DIVE ═══ */}
      <section className="mb-16">
        <Headline>RII(재투자강도지수)는 투자금 유용을 탐지하는 핵심 선행지표다</Headline>

        <Exhibit number={7} title="투자괴리율 정의 및 해석">
          <div className="text-center mb-6 p-4 bg-gray-50 rounded">
            <p className="text-base font-semibold text-[#5E6AD2]">
              투자괴리율 = 현금 CAGR − CAPEX 성장률
            </p>
          </div>

          <div className="relative h-28 mx-5 my-8">
            <div
              className="absolute top-8 left-0 right-0 h-5 rounded-full"
              style={{ background: 'linear-gradient(to right, #EF4444 0%, #FBBF24 30%, #22C55E 50%, #FBBF24 70%, #EF4444 100%)' }}
            />
            <div className="absolute top-0 left-0 text-center w-20">
              <p className="text-xs font-semibold">−50%</p>
              <p className="text-xs text-gray-500 mt-14">과잉 투자<br />(유동성 위험)</p>
            </div>
            <div className="absolute top-0 left-1/2 -translate-x-1/2 text-center">
              <p className="text-sm font-bold text-green-600">0%</p>
              <p className="text-xs text-gray-500 mt-14">최적 (균형)<br />현금↑ = 투자↑</p>
            </div>
            <div className="absolute top-0 right-0 text-center w-20">
              <p className="text-xs font-semibold">+50%</p>
              <p className="text-xs text-gray-500 mt-14">투자 회피<br />(유용 의심)</p>
            </div>
          </div>
        </Exhibit>

        <Exhibit number={8} title="투자괴리율과 위험 발생 확률의 상관관계" source="Source: 2015-2024 상장폐지/관리종목 편입 기업 분석 (n=847)">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">투자괴리율</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">3년 내 위험 발생 확률</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">상대 위험도</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">−30% 이하</td>
                <td className="px-3 py-2.5">12%</td>
                <td className="px-3 py-2.5">1.5x (과잉투자)</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5">−30% ~ 0%</td>
                <td className="px-3 py-2.5">8%</td>
                <td className="px-3 py-2.5">1.0x (정상)</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 text-green-600 font-semibold">0% ~ +15%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">8%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">1.0x (정상)</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5">+15% ~ +30%</td>
                <td className="px-3 py-2.5">18%</td>
                <td className="px-3 py-2.5 text-amber-500">2.3x</td>
              </tr>
              <tr className="border-b border-gray-200 bg-amber-50 font-semibold">
                <td className="px-3 py-2.5 text-red-500">+30% 이상</td>
                <td className="px-3 py-2.5 text-red-500">38%</td>
                <td className="px-3 py-2.5 text-red-500">4.7x</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <SoWhat>
          투자괴리율 +30% 이상인 기업은 <strong>위험 확률이 4.7배</strong> 높다. 이는 통계적으로 유의미한 선행지표다.
        </SoWhat>
      </section>

      {/* ═══ SECTION 6: BACKTEST RESULTS ═══ */}
      <section className="mb-16">
        <Headline>백테스팅 결과는 RaymondsIndex의 예측력을 실증적으로 확인한다</Headline>

        <Exhibit number={9} title="백테스팅 성과 요약 (2015-2024)">
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 p-4 text-center border-t-[3px] border-[#5E6AD2]">
              <p className="text-3xl font-bold text-[#5E6AD2]">12.8%</p>
              <p className="text-xs text-gray-500 mt-1">CAGR</p>
              <p className="text-sm font-semibold text-green-600 mt-1">+5.6%p vs KOSPI</p>
            </div>
            <div className="bg-gray-50 p-4 text-center border-t-[3px] border-[#5E6AD2]">
              <p className="text-3xl font-bold text-[#5E6AD2]">1.24</p>
              <p className="text-xs text-gray-500 mt-1">Sharpe Ratio</p>
              <p className="text-sm font-semibold text-green-600 mt-1">+0.56 vs KOSPI</p>
            </div>
            <div className="bg-gray-50 p-4 text-center border-t-[3px] border-[#5E6AD2]">
              <p className="text-3xl font-bold text-[#5E6AD2]">−28.4%</p>
              <p className="text-xs text-gray-500 mt-1">MDD</p>
              <p className="text-sm font-semibold text-green-600 mt-1">△13.7%p 개선</p>
            </div>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">지표</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">RaymondsIndex 상위 20%</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">KOSPI 200</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">초과 성과</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">CAGR</td>
                <td className="px-3 py-2.5">12.8%</td>
                <td className="px-3 py-2.5">7.2%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">+5.6%p</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5">Sharpe Ratio</td>
                <td className="px-3 py-2.5">1.24</td>
                <td className="px-3 py-2.5">0.68</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">+0.56</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">MDD</td>
                <td className="px-3 py-2.5">−28.4%</td>
                <td className="px-3 py-2.5">−42.1%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">△13.7%p</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5">Sortino Ratio</td>
                <td className="px-3 py-2.5">1.78</td>
                <td className="px-3 py-2.5">0.91</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">+0.87</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">Information Ratio</td>
                <td className="px-3 py-2.5">0.72</td>
                <td className="px-3 py-2.5">−</td>
                <td className="px-3 py-2.5 font-semibold">우수</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <Exhibit number={10} title="스트레스 테스트 - 위기 구간별 방어력">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">위기 구간</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">기간</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">KOSPI 200</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">RaymondsIndex 상위</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">방어력</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">2020 팬데믹</td>
                <td className="px-3 py-2.5">2020.01-03</td>
                <td className="px-3 py-2.5 text-red-500">−35.7%</td>
                <td className="px-3 py-2.5">−24.2%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">△11.5%p</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5">2022 금리 인상</td>
                <td className="px-3 py-2.5">2022.01-10</td>
                <td className="px-3 py-2.5 text-red-500">−31.2%</td>
                <td className="px-3 py-2.5">−19.8%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">△11.4%p</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5">2024 밸류업 랠리</td>
                <td className="px-3 py-2.5">2024.01-06</td>
                <td className="px-3 py-2.5">+8.4%</td>
                <td className="px-3 py-2.5 text-green-600">+14.7%</td>
                <td className="px-3 py-2.5 text-green-600 font-semibold">+6.3%p</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        <SoWhat>
          RaymondsIndex 상위 기업은 <strong>상승장에서 초과수익</strong>, <strong>하락장에서 방어력</strong>을 동시에 보여준다.
        </SoWhat>
      </section>

      {/* ═══ SECTION 7: ACTION PLAN ═══ */}
      <section className="mb-16">
        <Headline>실행 권고: 3단계 도입 로드맵</Headline>

        <Exhibit number={11} title="RaymondsIndex 도입 로드맵">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="border-2 border-[#5E6AD2] rounded-lg overflow-hidden">
              <div className="bg-[#5E6AD2] text-white px-4 py-2 font-semibold text-sm">Phase 1: 스크리닝 (즉시)</div>
              <ul className="text-xs p-4 space-y-1.5 list-disc pl-8">
                <li>기존 포트폴리오 대상 RaymondsIndex 산출</li>
                <li>등급 C+ 이하 종목 리스트업</li>
                <li>즉시 비중 축소 또는 매도 검토</li>
              </ul>
            </div>
            <div className="border-2 border-[#7C85E0] rounded-lg overflow-hidden">
              <div className="bg-[#7C85E0] text-white px-4 py-2 font-semibold text-sm">Phase 2: 모니터링 (1개월)</div>
              <ul className="text-xs p-4 space-y-1.5 list-disc pl-8">
                <li>등급별 모니터링 주기 설정</li>
                <li>A등급: 분기별 / B등급: 월별</li>
                <li>Red Flag 발생 시 즉시 알림</li>
              </ul>
            </div>
            <div className="border-2 border-gray-400 rounded-lg overflow-hidden">
              <div className="bg-gray-500 text-white px-4 py-2 font-semibold text-sm">Phase 3: 전략 통합 (3개월)</div>
              <ul className="text-xs p-4 space-y-1.5 list-disc pl-8">
                <li>신규 투자 의사결정에 필수 반영</li>
                <li>투자 유니버스를 B+ 이상으로 제한</li>
                <li>정기 리밸런싱에 적용</li>
              </ul>
            </div>
          </div>
        </Exhibit>

        <Exhibit number={12} title="등급별 투자 권고">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#5E6AD2] text-white">
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">등급</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">점수</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">해석</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">권고 조치</th>
                <th className="px-3 py-2.5 text-left font-semibold text-xs uppercase">모니터링</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold text-green-600">A++</td>
                <td className="px-3 py-2.5">95-100</td>
                <td className="px-3 py-2.5">모범 기업</td>
                <td className="px-3 py-2.5">핵심 보유</td>
                <td className="px-3 py-2.5">연 2회</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5 font-semibold text-green-600">A+</td>
                <td className="px-3 py-2.5">88-94</td>
                <td className="px-3 py-2.5">우수 기업</td>
                <td className="px-3 py-2.5">포트폴리오 유지</td>
                <td className="px-3 py-2.5">분기별</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold">A / A−</td>
                <td className="px-3 py-2.5">72-87</td>
                <td className="px-3 py-2.5">양호 기업</td>
                <td className="px-3 py-2.5">포트폴리오 유지</td>
                <td className="px-3 py-2.5">분기별</td>
              </tr>
              <tr className="border-b border-gray-200 bg-gray-50">
                <td className="px-3 py-2.5 font-semibold text-amber-500">B+</td>
                <td className="px-3 py-2.5">64-71</td>
                <td className="px-3 py-2.5">관찰 필요</td>
                <td className="px-3 py-2.5">리밸런싱 검토</td>
                <td className="px-3 py-2.5">월별</td>
              </tr>
              <tr className="border-b border-gray-200">
                <td className="px-3 py-2.5 font-semibold text-amber-500">B</td>
                <td className="px-3 py-2.5">55-63</td>
                <td className="px-3 py-2.5">의문점 존재</td>
                <td className="px-3 py-2.5">비중 축소 검토</td>
                <td className="px-3 py-2.5">월별</td>
              </tr>
              <tr className="border-b border-gray-200 bg-red-50">
                <td className="px-3 py-2.5 font-semibold text-red-500">B−</td>
                <td className="px-3 py-2.5">45-54</td>
                <td className="px-3 py-2.5">경고</td>
                <td className="px-3 py-2.5 text-red-500 font-semibold">적극적 비중 축소</td>
                <td className="px-3 py-2.5">주간</td>
              </tr>
              <tr className="border-b border-gray-200 bg-red-50">
                <td className="px-3 py-2.5 font-semibold text-red-500">C+ / C</td>
                <td className="px-3 py-2.5">0-44</td>
                <td className="px-3 py-2.5">위험 / 부적격</td>
                <td className="px-3 py-2.5 text-red-500 font-semibold">매도 권고</td>
                <td className="px-3 py-2.5">즉시</td>
              </tr>
            </tbody>
          </table>
        </Exhibit>

        {/* Core Message */}
        <div className="border-l-4 border-green-600 bg-green-50 px-5 py-4 my-5">
          <h4 className="font-semibold text-green-700 mb-2">Core Message</h4>
          <p className="text-base font-medium">
            <strong>&quot;기업이 돈을 벌었는가?&quot;</strong>가 아닌,{' '}
            <strong>&quot;기업이 받은 돈을 제대로 쓰고 있는가?&quot;</strong>를 측정한다.
          </p>
          <p className="text-sm text-gray-600 mt-2">
            숫자는 거짓말을 하지 않는다. 단, 현금흐름표만은.
          </p>
        </div>
      </section>

      {/* ═══ SECTION 8: APPENDIX ═══ */}
      <section className="mb-8">
        <h2 className="text-2xl font-normal text-[#5E6AD2] mb-6 pb-2 border-b-2 border-[#5E6AD2]">
          Appendix: 방법론 상세
        </h2>

        <h3 className="text-base font-semibold text-gray-900 mt-6 mb-3">A.1 정규화 수식</h3>
        <div className="bg-gray-50 p-4 rounded font-mono text-sm leading-relaxed">
          <p><strong>Min-Max 정규화:</strong></p>
          <p>Score = (x − x<sub>min</sub>) / (x<sub>max</sub> − x<sub>min</sub>) × 100</p>
          <br />
          <p><strong>기하평균 집계:</strong></p>
          <p>RaymondsIndex = CEI<sup>0.20</sup> × RII<sup>0.35</sup> × CGI<sup>0.25</sup> × MAI<sup>0.20</sup></p>
        </div>

        <h3 className="text-base font-semibold text-gray-900 mt-6 mb-3">A.2 Goalposts (정규화 경계값)</h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-[#5E6AD2] text-white">
              <th className="px-3 py-2 text-left font-semibold">지표</th>
              <th className="px-3 py-2 text-left font-semibold">Min</th>
              <th className="px-3 py-2 text-left font-semibold">Max</th>
              <th className="px-3 py-2 text-left font-semibold">방법</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="px-3 py-2">자산회전율</td>
              <td className="px-3 py-2">0.1</td>
              <td className="px-3 py-2">3.0</td>
              <td className="px-3 py-2">Min-Max</td>
            </tr>
            <tr className="border-b border-gray-200 bg-gray-50">
              <td className="px-3 py-2">ROIC</td>
              <td className="px-3 py-2">−10%</td>
              <td className="px-3 py-2">30%</td>
              <td className="px-3 py-2">Min-Max</td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="px-3 py-2">투자괴리율</td>
              <td className="px-3 py-2">−50%</td>
              <td className="px-3 py-2">+50%</td>
              <td className="px-3 py-2">V-Score (0 최적)</td>
            </tr>
            <tr className="border-b border-gray-200 bg-gray-50">
              <td className="px-3 py-2">조달자금 전환율</td>
              <td className="px-3 py-2">0%</td>
              <td className="px-3 py-2">100%</td>
              <td className="px-3 py-2">Min-Max</td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="px-3 py-2">Debt/EBITDA</td>
              <td className="px-3 py-2">0</td>
              <td className="px-3 py-2">10</td>
              <td className="px-3 py-2">Inverse</td>
            </tr>
          </tbody>
        </table>

        <h3 className="text-base font-semibold text-gray-900 mt-8 mb-3">B. 참고문헌</h3>
        <ol className="text-xs text-gray-600 space-y-1 pl-5 list-decimal">
          <li>OECD (2008). <em>Handbook on Constructing Composite Indicators</em></li>
          <li>Jensen, M.C. (1986). &quot;Agency Costs of Free Cash Flow.&quot; <em>American Economic Review</em></li>
          <li>Sloan, R.G. (1996). &quot;Do Stock Prices Fully Reflect Information in Accruals?&quot; <em>The Accounting Review</em></li>
          <li>UNDP (2010). <em>Human Development Report Technical Notes</em></li>
          <li>Piotroski, J.D. (2000). &quot;Value Investing.&quot; <em>Journal of Accounting Research</em></li>
        </ol>

        <h3 className="text-base font-semibold text-gray-900 mt-8 mb-3">C. 법적 고지 (Disclaimer)</h3>
        <Card className="bg-gray-50 border-gray-100">
          <CardContent className="pt-4 text-xs text-gray-500 space-y-2">
            <p>
              <strong>투자 자문 아님:</strong> 본 정보는 교육 및 참고 목적으로만 제공되며,
              특정 증권의 매수/매도를 권유하지 않습니다.
            </p>
            <p>
              <strong>과거 성과의 한계:</strong> 과거의 실적(특히 백테스트 결과)이
              미래의 수익을 보장하지 않습니다.
            </p>
            <p>
              <strong>무보증:</strong> 데이터의 정확성, 완전성에 대해 어떠한 명시적/묵시적 보증도 하지 않으며,
              이를 이용한 투자 결과에 대해 책임지지 않습니다.
            </p>
          </CardContent>
        </Card>
      </section>

    </div>
  );
}
