import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getRaymondsIndexRanking,
  getRaymondsIndexStatistics,
  type RaymondsIndexRankingItem,
  type RaymondsIndexStatistics
} from '../api/raymondsIndex'
import { MarketBadge } from '../components/common'

// 등급 설정
const gradeConfig = {
  'A+': { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  'A': { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  'B': { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  'C': { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  'D': { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
}

function RaymondsIndexRankingPage() {
  const navigate = useNavigate()

  const [rankings, setRankings] = useState<RaymondsIndexRankingItem[]>([])
  const [statistics, setStatistics] = useState<RaymondsIndexStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 필터/정렬 상태
  const [sortBy, setSortBy] = useState<'score_desc' | 'score_asc' | 'gap_asc' | 'gap_desc'>('score_desc')
  const [selectedGrades, setSelectedGrades] = useState<string[]>([])
  const [limit, setLimit] = useState(50)

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        // 병렬로 데이터 로드
        const [rankingData, statsData] = await Promise.all([
          getRaymondsIndexRanking({
            sort: sortBy,
            grades: selectedGrades.length > 0 ? selectedGrades : undefined,
            limit
          }),
          getRaymondsIndexStatistics()
        ])

        setRankings(rankingData)
        setStatistics(statsData)
      } catch (err) {
        console.error('데이터 로드 실패:', err)
        setError('데이터를 불러오는데 실패했습니다')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [sortBy, selectedGrades, limit])

  const handleCompanyClick = useCallback((companyId: string) => {
    navigate(`/company/${companyId}/report`)
  }, [navigate])

  const toggleGrade = useCallback((grade: string) => {
    setSelectedGrades(prev =>
      prev.includes(grade)
        ? prev.filter(g => g !== grade)
        : [...prev, grade]
    )
  }, [])

  const getGradeConfig = (grade: string) => {
    return gradeConfig[grade as keyof typeof gradeConfig] || gradeConfig.D
  }

  return (
    <div className="bg-dark-bg">
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Page Title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-text-primary">RaymondsIndex 랭킹</h1>
          <p className="text-sm text-text-secondary mt-1">자본 배분 효율성 지수 순위</p>
        </div>
        {/* 통계 카드 */}
        {statistics && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <p className="text-xs text-text-secondary mb-1">총 기업</p>
              <p className="text-2xl font-bold text-text-primary">{statistics.total_companies?.toLocaleString() || 0}</p>
            </div>
            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <p className="text-xs text-text-secondary mb-1">평균 점수</p>
              <p className="text-2xl font-bold text-text-primary">{statistics.average_score?.toFixed(1) || 0}</p>
            </div>
            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <p className="text-xs text-text-secondary mb-1">A+ 등급</p>
              <p className="text-2xl font-bold text-emerald-400">
                {statistics.grade_distribution?.['A+'] || 0}
              </p>
            </div>
            <div className="bg-dark-card border border-dark-border rounded-lg p-4">
              <p className="text-xs text-text-secondary mb-1">평균 투자괴리율</p>
              <p className="text-2xl font-bold text-text-primary">
                {statistics.average_investment_gap?.toFixed(1) || 0}%
              </p>
            </div>
          </div>
        )}

        {/* 필터/정렬 */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          {/* 등급 필터 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">등급:</span>
            {['A+', 'A', 'B', 'C', 'D'].map(grade => {
              const config = getGradeConfig(grade)
              const isSelected = selectedGrades.includes(grade)
              return (
                <button
                  key={grade}
                  onClick={() => toggleGrade(grade)}
                  className={`px-3 py-1 text-sm font-medium rounded-full border transition-all ${
                    isSelected
                      ? `${config.bg} ${config.text} ${config.border}`
                      : 'bg-dark-card border-dark-border text-text-secondary hover:border-dark-border-hover'
                  }`}
                >
                  {grade}
                </button>
              )
            })}
          </div>

          {/* 정렬 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">정렬:</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as typeof sortBy)}
              className="bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value="score_desc">점수 높은순</option>
              <option value="score_asc">점수 낮은순</option>
              <option value="gap_asc">투자괴리율 낮은순</option>
              <option value="gap_desc">투자괴리율 높은순</option>
            </select>
          </div>

          {/* 표시 개수 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">표시:</span>
            <select
              value={limit}
              onChange={e => setLimit(Number(e.target.value))}
              className="bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
            >
              <option value={20}>20개</option>
              <option value={50}>50개</option>
              <option value={100}>100개</option>
            </select>
          </div>
        </div>

        {/* 로딩 */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
          </div>
        )}

        {/* 에러 */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* 랭킹 테이블 */}
        {!isLoading && !error && rankings.length > 0 && (
          <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-border bg-dark-bg/50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                      순위
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                      기업명
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider">
                      등급
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                      점수
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                      투자괴리율
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider hidden md:table-cell">
                      CEI
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider hidden md:table-cell">
                      RII
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider hidden md:table-cell">
                      CGI
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider hidden md:table-cell">
                      MAI
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border">
                  {rankings.map((item, index) => {
                    const config = getGradeConfig(item.grade)
                    const gapColor = item.investment_gap > 10 ? 'text-red-400' :
                                     item.investment_gap < -10 ? 'text-yellow-400' : 'text-green-400'

                    return (
                      <tr
                        key={item.company_id}
                        onClick={() => handleCompanyClick(item.company_id)}
                        className="hover:bg-dark-bg/50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-4">
                          <span className={`text-sm font-medium ${
                            index < 3 ? 'text-accent-primary' : 'text-text-secondary'
                          }`}>
                            {index + 1}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-text-primary">{item.company_name}</p>
                              {item.market && <MarketBadge market={item.market} size="sm" />}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${config.bg} ${config.text}`}>
                            {item.grade}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className="text-sm font-bold text-text-primary">{item.total_score.toFixed(1)}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className={`text-sm font-medium ${gapColor}`}>
                            {item.investment_gap > 0 ? '+' : ''}{item.investment_gap.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-4 py-4 text-center hidden md:table-cell">
                          <span className="text-xs text-text-secondary">{item.cei_score?.toFixed(0) || '-'}</span>
                        </td>
                        <td className="px-4 py-4 text-center hidden md:table-cell">
                          <span className="text-xs text-text-secondary">{item.rii_score?.toFixed(0) || '-'}</span>
                        </td>
                        <td className="px-4 py-4 text-center hidden md:table-cell">
                          <span className="text-xs text-text-secondary">{item.cgi_score?.toFixed(0) || '-'}</span>
                        </td>
                        <td className="px-4 py-4 text-center hidden md:table-cell">
                          <span className="text-xs text-text-secondary">{item.mai_score?.toFixed(0) || '-'}</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 데이터 없음 */}
        {!isLoading && !error && rankings.length === 0 && (
          <div className="bg-dark-card border border-dark-border rounded-lg p-8 text-center">
            <p className="text-text-secondary">데이터가 없습니다</p>
          </div>
        )}

        {/* 범례 */}
        <div className="mt-8 bg-dark-card border border-dark-border rounded-lg p-6">
          <h3 className="text-sm font-medium text-text-primary mb-4">Sub-Index 설명</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="font-medium text-accent-primary mb-1">CEI (20%)</p>
              <p className="text-text-secondary">Capital Efficiency Index<br/>자본 효율성</p>
            </div>
            <div>
              <p className="font-medium text-accent-primary mb-1">RII (35%)</p>
              <p className="text-text-secondary">Reinvestment Intensity Index<br/>재투자 강도 (핵심)</p>
            </div>
            <div>
              <p className="font-medium text-accent-primary mb-1">CGI (25%)</p>
              <p className="text-text-secondary">Cash Governance Index<br/>현금 거버넌스</p>
            </div>
            <div>
              <p className="font-medium text-accent-primary mb-1">MAI (20%)</p>
              <p className="text-text-secondary">Momentum Alignment Index<br/>모멘텀 정렬</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default RaymondsIndexRankingPage
