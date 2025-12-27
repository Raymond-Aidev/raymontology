import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  BookOpen,
  PieChart,
  TrendingUp,
  Wallet,
  Activity,
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';
import { GRADE_COLORS, SUB_INDEX_INFO, GRADE_ORDER, type Grade } from '@/lib/constants';

export default function MethodologyPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          RaymondsIndex 평가 방법론
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          RaymondsIndex는 기업의 자본 배분 효율성을 투자자 관점에서 평가하는 종합 지표입니다.
          기업이 벌어들인 돈을 어디에, 어떻게 쓰는지 분석합니다.
        </p>
      </div>

      {/* Overview Section */}
      <section className="mb-12">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-500" />
              평가 개요
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">평가 목적</h3>
                <ul className="space-y-2 text-gray-600">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-1 shrink-0" />
                    <span>현금만 쌓아두는 기업과 성장에 재투자하는 기업 구별</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-1 shrink-0" />
                    <span>투자자 관점의 자본 배분 효율성 평가</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-1 shrink-0" />
                    <span>재무제표 기반 객관적 분석 제공</span>
                  </li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">데이터 출처</h3>
                <ul className="space-y-2 text-gray-600">
                  <li>- DART 전자공시시스템 공시 데이터</li>
                  <li>- 분기/반기/사업보고서 재무제표</li>
                  <li>- CB 발행 및 자금 조달 공시</li>
                  <li>- 최근 5개년 데이터 분석</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Grade System */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">등급 체계 (9등급)</h2>
        <div className="grid sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {GRADE_ORDER.map((grade) => {
            const colors = GRADE_COLORS[grade as Grade];
            const gradeInfo = getGradeInfo(grade);
            return (
              <Card key={grade} className="text-center">
                <CardContent className="pt-6">
                  <div
                    className="w-14 h-14 rounded-lg mx-auto flex items-center justify-center text-xl font-bold mb-3"
                    style={{
                      backgroundColor: colors.bg,
                      color: colors.text,
                    }}
                  >
                    {grade}
                  </div>
                  <p className="font-medium text-gray-900">{gradeInfo.label}</p>
                  <p className="text-sm text-gray-500">{gradeInfo.range}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Sub-Index Section */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Sub-Index 구성</h2>

        <div className="space-y-6">
          {/* CEI */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-gray-500" />
                  CEI (Capital Efficiency Index)
                </div>
                <Badge variant="outline">가중치 15%</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                <strong>자본 효율성 지표</strong>: 기업이 투입한 자본 대비 얼마나 효율적으로 수익을 창출하는지 평가
              </p>
              <div className="grid sm:grid-cols-3 gap-4 text-sm">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">ROIC</p>
                  <p className="text-gray-500">투하자본수익률</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">자산회전율</p>
                  <p className="text-gray-500">자산 활용 효율성</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">ROE</p>
                  <p className="text-gray-500">자기자본이익률</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RII */}
          <Card className="border-blue-200 bg-blue-50/30">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-500" />
                  RII (Reinvestment Intensity Index)
                  <Badge className="bg-blue-600">핵심</Badge>
                </div>
                <Badge variant="outline" className="border-blue-400 text-blue-700">가중치 40%</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                <strong>재투자 강도 지표</strong>: 벌어들인 돈을 성장을 위해 얼마나 적극적으로 재투자하는지 평가.
                <span className="text-blue-600"> 현금만 쌓아두는 기업은 감점.</span>
              </p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div className="bg-white p-3 rounded border">
                  <p className="font-medium">재투자율</p>
                  <p className="text-gray-500">CAPEX / 영업현금흐름</p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="font-medium">CAPEX 증가율</p>
                  <p className="text-gray-500">투자 확대 여부</p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="font-medium">투자괴리율</p>
                  <p className="text-gray-500">현금 vs CAPEX 증가 차이</p>
                </div>
                <div className="bg-white p-3 rounded border">
                  <p className="font-medium">CAPEX 변동계수</p>
                  <p className="text-gray-500">투자 지속성</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* CGI */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wallet className="w-5 h-5 text-gray-500" />
                  CGI (Cash Governance Index)
                </div>
                <Badge variant="outline">가중치 30%</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                <strong>현금 거버넌스 지표</strong>: 보유 현금을 생산적 자산으로 전환하는지, 단기 금융상품에만 묻어두는지 평가
              </p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">현금/유형자산 비율</p>
                  <p className="text-gray-500">현금 vs 생산자산</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">조달자금 전환율</p>
                  <p className="text-gray-500">자금 활용 효율</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">단기금융비율</p>
                  <p className="text-gray-500">유동성 과잉 여부</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">유휴현금 비율</p>
                  <p className="text-gray-500">비생산적 현금 보유</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* MAI */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-gray-500" />
                  MAI (Momentum Alignment Index)
                </div>
                <Badge variant="outline">가중치 15%</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                <strong>모멘텀 정합성 지표</strong>: 기업의 투자 방향과 시장 모멘텀이 일치하는지 평가
              </p>
              <div className="grid sm:grid-cols-3 gap-4 text-sm">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">주주환원율</p>
                  <p className="text-gray-500">배당 + 자사주 매입</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">CAPEX 추세</p>
                  <p className="text-gray-500">증가/유지/감소</p>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <p className="font-medium">매출 성장 정합성</p>
                  <p className="text-gray-500">투자와 성장의 연관성</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Special Rules */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">특별 규칙 (등급 제한)</h2>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
              <p className="text-gray-600">
                특정 조건에 해당하는 기업은 점수와 관계없이 최대 등급이 제한됩니다.
              </p>
            </div>
            <div className="space-y-4">
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
                <p className="font-medium text-yellow-800 mb-2">
                  현금/유형자산 비율 &gt; 30:1 → 최대 등급 B-
                </p>
                <p className="text-sm text-gray-600">
                  현금 증가율이 유형자산 증가율의 30배를 초과하는 경우
                </p>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
                <p className="font-medium text-yellow-800 mb-2">
                  조달자금 전환율 &lt; 30% → 최대 등급 B-
                </p>
                <p className="text-sm text-gray-600">
                  CB/유상증자 등으로 조달한 자금의 CAPEX 전환율이 30% 미만인 경우
                </p>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
                <p className="font-medium text-yellow-800 mb-2">
                  단기금융비율 &gt; 65% + CAPEX 감소 → 최대 등급 B
                </p>
                <p className="text-sm text-gray-600">
                  현금의 65% 이상을 단기금융상품으로 보유하면서 CAPEX가 감소하는 경우
                </p>
              </div>
              <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                <p className="font-medium text-red-800 mb-2">
                  위 조건 2개 이상 해당 → 최대 등급 C+
                </p>
                <p className="text-sm text-gray-600">
                  복합적인 자본 배분 문제가 있는 경우
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Disclaimer */}
      <section>
        <Card className="bg-gray-50">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-gray-900 mb-3">면책조항</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              RaymondsIndex는 공시 데이터를 기반으로 한 참고용 지표입니다.
              투자 결정의 유일한 근거로 사용하지 마시고, 반드시 전문가 상담 및 추가 조사를 병행하시기 바랍니다.
              과거의 자본 배분 패턴이 미래의 성과를 보장하지 않습니다.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function getGradeInfo(grade: string) {
  const info: Record<string, { label: string; range: string }> = {
    'A++': { label: '최고 효율', range: '95+ 점' },
    'A+': { label: '매우 우수', range: '90-94 점' },
    'A': { label: '우수', range: '85-89 점' },
    'A-': { label: '양호', range: '80-84 점' },
    'B+': { label: '평균 이상', range: '70-79 점' },
    'B': { label: '평균', range: '60-69 점' },
    'B-': { label: '평균 이하', range: '50-59 점' },
    'C+': { label: '주의 필요', range: '40-49 점' },
    'C': { label: '심각한 문제', range: '40 미만' },
  };
  return info[grade] || { label: '', range: '' };
}
