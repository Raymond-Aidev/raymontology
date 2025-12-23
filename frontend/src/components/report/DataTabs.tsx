import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { CBIssuance, CBSubscriber, Officer, FinancialStatement, Shareholder, Affiliate } from '../../types/report'
import { shareholderTypeConfig, affiliateRelationConfig } from '../../types/report'

interface DataTabsProps {
  cbIssuances: CBIssuance[]
  cbSubscribers: CBSubscriber[]
  officers: Officer[]
  financials: FinancialStatement[]
  shareholders: Shareholder[]
  affiliates: Affiliate[]
}

type TabKey = 'cb_issue' | 'cb_subscriber' | 'officer' | 'financial' | 'shareholder' | 'affiliate'

const tabs: { key: TabKey; label: string; shortLabel: string }[] = [
  { key: 'cb_issue', label: 'CB 발행', shortLabel: 'CB' },
  { key: 'cb_subscriber', label: 'CB 인수인', shortLabel: '인수' },
  { key: 'officer', label: '임원 현황', shortLabel: '임원' },
  { key: 'financial', label: '재무제표', shortLabel: '재무' },
  { key: 'shareholder', label: '주주 구성', shortLabel: '주주' },
  { key: 'affiliate', label: '계열회사', shortLabel: '계열' },
]

export default function DataTabs({ cbIssuances, cbSubscribers, officers, financials, shareholders, affiliates }: DataTabsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('cb_issue')

  const formatCurrency = (amount: number) => {
    const absAmount = Math.abs(amount)
    const sign = amount < 0 ? '-' : ''
    if (absAmount >= 100000000) {
      return `${sign}${(absAmount / 100000000).toFixed(1)}억원`
    }
    return `${sign}${(absAmount / 10000).toFixed(0)}만원`
  }

  // 주식 수 포맷팅 (천 단위 콤마)
  const formatShares = (shares: number) => {
    return shares.toLocaleString()
  }

  // 지분율 포맷팅 (소수점 1자리)
  const formatPercentage = (percentage: number) => {
    return `${percentage.toFixed(1)}%`
  }

  // 주주 데이터를 지분율 높은 순으로 정렬
  const sortedShareholders = [...shareholders].sort((a, b) => b.percentage - a.percentage)

  // 계열회사 데이터를 지분율 높은 순으로 정렬
  const sortedAffiliates = [...affiliates].sort((a, b) => b.percentage - a.percentage)

  return (
    <div>
      {/* 탭 헤더 - 모바일 스크롤 가능 */}
      <div className="flex gap-1 border-b border-dark-border mb-4 overflow-x-auto scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 md:px-4 py-2 text-xs md:text-sm font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
              activeTab === tab.key
                ? 'text-accent-primary border-b-2 border-accent-primary'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <span className="md:hidden">{tab.shortLabel}</span>
            <span className="hidden md:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* CB 발행 */}
      {activeTab === 'cb_issue' && (
        <>
          {cbIssuances.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-text-muted">CB 발행 내역이 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {cbIssuances.map((cb, index) => (
                  <div key={`${cb.id}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-accent-primary">{cb.issue_round || '-'}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        cb.status === 'active' ? 'bg-green-500/20 text-green-400' :
                        cb.status === 'converted' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-dark-card text-text-secondary'
                      }`}>
                        {cb.status === 'active' ? '유효' : cb.status === 'converted' ? '전환' : '상환'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-text-muted">발행일</span>
                        <p className="text-text-primary">{cb.issue_date}</p>
                      </div>
                      <div>
                        <span className="text-text-muted">만기일</span>
                        <p className="text-text-primary">{cb.maturity_date}</p>
                      </div>
                      <div>
                        <span className="text-text-muted">발행금액</span>
                        <p className="text-text-primary font-medium">{formatCurrency(cb.amount)}</p>
                      </div>
                      <div>
                        <span className="text-text-muted">전환가격</span>
                        <p className="text-text-primary">{cb.conversion_price.toLocaleString()}원</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">발행회차</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">발행일</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">발행금액</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">전환가격</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">이자율</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">만기일</th>
                      <th className="px-4 py-3 text-center font-medium text-text-secondary">상태</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {cbIssuances.map((cb, index) => (
                      <tr key={`${cb.id}-${index}`} className="hover:bg-dark-hover">
                        <td className="px-4 py-3 font-medium text-accent-primary">{cb.issue_round || '-'}</td>
                        <td className="px-4 py-3 text-text-primary">{cb.issue_date}</td>
                        <td className="px-4 py-3 text-right font-medium text-text-primary">{formatCurrency(cb.amount)}</td>
                        <td className="px-4 py-3 text-right text-text-primary">{cb.conversion_price.toLocaleString()}원</td>
                        <td className="px-4 py-3 text-right text-text-primary">{cb.coupon_rate}%</td>
                        <td className="px-4 py-3 text-text-primary">{cb.maturity_date}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            cb.status === 'active' ? 'bg-green-500/20 text-green-400' :
                            cb.status === 'converted' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-dark-card text-text-secondary'
                          }`}>
                            {cb.status === 'active' ? '유효' : cb.status === 'converted' ? '전환' : '상환'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* CB 인수인 */}
      {activeTab === 'cb_subscriber' && (
        <>
          {cbSubscribers.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-text-muted">CB 인수인 정보가 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {cbSubscribers.map((sub, index) => (
                  <div key={`${sub.id}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-text-primary">{sub.name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        sub.type === 'institution' ? 'bg-blue-500/20 text-blue-400' :
                        sub.type === 'related' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-dark-card text-text-secondary'
                      }`}>
                        {sub.type === 'institution' ? '기관' : sub.type === 'related' ? '특수관계인' : '개인'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-text-muted">인수금액</span>
                        <p className="text-text-primary font-medium">{formatCurrency(sub.amount)}</p>
                      </div>
                      <div>
                        <span className="text-text-muted">지분율</span>
                        <p className="text-text-primary">{sub.ratio}%</p>
                      </div>
                    </div>
                    {sub.issue_rounds && sub.issue_rounds.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {sub.issue_rounds.map((round, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded">
                            {round}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">인수인</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">발행회차</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">인수금액</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">지분율</th>
                      <th className="px-4 py-3 text-center font-medium text-text-secondary">유형</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {cbSubscribers.map((sub, index) => (
                      <tr key={`${sub.id}-${index}`} className="hover:bg-dark-hover">
                        <td className="px-4 py-3 font-medium text-text-primary">{sub.name}</td>
                        <td className="px-4 py-3">
                          {sub.issue_rounds && sub.issue_rounds.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {sub.issue_rounds.map((round, idx) => (
                                <span key={idx} className="px-1.5 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded">
                                  {round}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-text-muted">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right text-text-primary">{formatCurrency(sub.amount)}</td>
                        <td className="px-4 py-3 text-right text-text-primary">{sub.ratio}%</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            sub.type === 'institution' ? 'bg-blue-500/20 text-blue-400' :
                            sub.type === 'related' ? 'bg-orange-500/20 text-orange-400' :
                            'bg-dark-card text-text-secondary'
                          }`}>
                            {sub.type === 'institution' ? '기관' : sub.type === 'related' ? '특수관계인' : '개인'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* 임원 현황 */}
      {activeTab === 'officer' && (
        <>
          {officers.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-text-muted">임원 정보가 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {officers.map((officer, index) => (
                  <div key={`${officer.id}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-text-primary">{officer.name}</span>
                      {officer.is_current ? (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400">재직</span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-dark-card text-text-muted">퇴임</span>
                      )}
                    </div>
                    <p className="text-sm text-accent-primary mb-2">{officer.position}</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-text-muted">취임일</span>
                        <p className="text-text-primary">{officer.tenure_start}</p>
                      </div>
                      <div>
                        <span className="text-text-muted">퇴임일</span>
                        <p className="text-text-primary">{officer.tenure_end || '-'}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">성명</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">직책</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">취임일</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">퇴임일</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">겸직</th>
                      <th className="px-4 py-3 text-center font-medium text-text-secondary">상태</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {officers.map((officer, index) => (
                      <tr key={`${officer.id}-${index}`} className="hover:bg-dark-hover">
                        <td className="px-4 py-3 font-medium text-text-primary">{officer.name}</td>
                        <td className="px-4 py-3 text-text-primary">{officer.position}</td>
                        <td className="px-4 py-3 text-text-primary">{officer.tenure_start}</td>
                        <td className="px-4 py-3 text-text-primary">{officer.tenure_end || '-'}</td>
                        <td className="px-4 py-3 text-sm text-text-secondary">
                          {officer.other_positions?.join(', ') || '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {officer.is_current ? (
                            <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">재직</span>
                          ) : (
                            <span className="text-text-muted">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* 재무제표 */}
      {activeTab === 'financial' && (
        <>
          {financials.length === 0 ? (
            <div className="py-12 text-center">
              <svg className="w-12 h-12 mx-auto mb-3 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-text-muted">재무제표 정보가 없습니다</p>
              <p className="text-xs text-text-tertiary mt-1">아직 공시되지 않았거나 데이터를 불러올 수 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {financials.map((fin, index) => {
                  const debtRatio = fin.debt_ratio ?? (fin.equity > 0 ? (fin.total_liabilities / fin.equity) * 100 : 0)
                  return (
                    <div key={`${fin.year}-${fin.quarter || 'annual'}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-accent-primary text-lg">{fin.year}</span>
                          {fin.quarter && (
                            <span className="px-1.5 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded">{fin.quarter}</span>
                          )}
                        </div>
                        <span className={`text-xs font-medium ${debtRatio > 200 ? 'text-accent-danger' : debtRatio > 100 ? 'text-amber-400' : 'text-green-400'}`}>
                          부채비율 {debtRatio.toFixed(1)}%
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-text-muted">매출액</span>
                          <p className="text-text-primary font-medium">{formatCurrency(fin.revenue)}</p>
                        </div>
                        <div>
                          <span className="text-text-muted">총자산</span>
                          <p className="text-text-primary font-medium">{formatCurrency(fin.total_assets)}</p>
                        </div>
                        <div>
                          <span className="text-text-muted">영업이익</span>
                          <p className={fin.operating_profit < 0 ? 'text-accent-danger font-medium' : 'text-text-primary font-medium'}>
                            {formatCurrency(fin.operating_profit)}
                          </p>
                        </div>
                        <div>
                          <span className="text-text-muted">당기순이익</span>
                          <p className={fin.net_income < 0 ? 'text-accent-danger font-medium' : 'text-text-primary font-medium'}>
                            {formatCurrency(fin.net_income)}
                          </p>
                        </div>
                        <div>
                          <span className="text-text-muted">자기자본</span>
                          <p className={fin.equity < 0 ? 'text-accent-danger font-medium' : 'text-text-primary font-medium'}>
                            {formatCurrency(fin.equity)}
                          </p>
                        </div>
                        <div>
                          <span className="text-text-muted">총부채</span>
                          <p className="text-text-primary font-medium">{formatCurrency(fin.total_liabilities)}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">기간</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">매출액</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">영업이익</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">당기순이익</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">총자산</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">자기자본</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">부채비율</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {financials.map((fin, index) => {
                      const debtRatio = fin.debt_ratio ?? (fin.equity > 0 ? (fin.total_liabilities / fin.equity) * 100 : 0)
                      return (
                        <tr key={`${fin.year}-${fin.quarter || 'annual'}-${index}`} className="hover:bg-dark-hover">
                          <td className="px-4 py-3 font-medium text-text-primary">
                            <div className="flex items-center gap-2">
                              {fin.year}
                              {fin.quarter && (
                                <span className="px-1.5 py-0.5 text-xs bg-accent-primary/20 text-accent-primary rounded">{fin.quarter}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right text-text-primary">{formatCurrency(fin.revenue)}</td>
                          <td className={`px-4 py-3 text-right ${fin.operating_profit < 0 ? 'text-accent-danger' : 'text-text-primary'}`}>
                            {formatCurrency(fin.operating_profit)}
                          </td>
                          <td className={`px-4 py-3 text-right ${fin.net_income < 0 ? 'text-accent-danger' : 'text-text-primary'}`}>
                            {formatCurrency(fin.net_income)}
                          </td>
                          <td className="px-4 py-3 text-right text-text-primary">{formatCurrency(fin.total_assets)}</td>
                          <td className={`px-4 py-3 text-right ${fin.equity < 0 ? 'text-accent-danger' : 'text-text-primary'}`}>
                            {formatCurrency(fin.equity)}
                          </td>
                          <td className={`px-4 py-3 text-right font-medium ${
                            debtRatio > 200 ? 'text-accent-danger' :
                            debtRatio > 100 ? 'text-amber-400' :
                            'text-green-400'
                          }`}>
                            {debtRatio.toFixed(1)}%
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* 주주 구성 */}
      {activeTab === 'shareholder' && (
        <>
          {sortedShareholders.length === 0 ? (
            <div className="text-center py-8 text-text-muted">
              <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <p>주주 정보가 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {sortedShareholders.map((sh, index) => {
                  const typeConfig = shareholderTypeConfig[sh.type]
                  return (
                    <div key={`${sh.id}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-text-primary">{sh.name}</span>
                        {typeConfig && (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeConfig.bg} ${typeConfig.text}`}>
                            {typeConfig.label}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-text-muted">{formatShares(sh.shares)}주</span>
                        <span className="text-accent-primary font-bold text-sm">{formatPercentage(sh.percentage)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">주주명</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">주식 수</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">지분율</th>
                      <th className="px-4 py-3 text-center font-medium text-text-secondary">유형</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {sortedShareholders.map((sh, index) => {
                      const typeConfig = shareholderTypeConfig[sh.type]
                      return (
                        <tr key={`${sh.id}-${index}`} className="hover:bg-dark-hover">
                          <td className="px-4 py-3 font-medium text-text-primary">{sh.name}</td>
                          <td className="px-4 py-3 text-right text-text-primary">{formatShares(sh.shares)}</td>
                          <td className="px-4 py-3 text-right font-medium text-text-primary">{formatPercentage(sh.percentage)}</td>
                          <td className="px-4 py-3 text-center">
                            {typeConfig && (
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${typeConfig.bg} ${typeConfig.text}`}>
                                {typeConfig.label}
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      {/* 계열회사 */}
      {activeTab === 'affiliate' && (
        <>
          {sortedAffiliates.length === 0 ? (
            <div className="text-center py-8 text-text-muted">
              <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <p>계열회사 정보가 없습니다</p>
            </div>
          ) : (
            <>
              {/* 모바일 카드 뷰 */}
              <div className="md:hidden space-y-3">
                {sortedAffiliates.map((aff, index) => {
                  const relationConfig = affiliateRelationConfig[aff.relation]
                  return (
                    <div key={`${aff.id}-${index}`} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        {aff.company_id ? (
                          <Link
                            to={`/company/${aff.company_id}/report`}
                            className="font-medium text-accent-primary hover:underline"
                          >
                            {aff.name}
                          </Link>
                        ) : (
                          <span className="font-medium text-text-primary">{aff.name}</span>
                        )}
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${relationConfig.bg} ${relationConfig.text}`}>
                          {relationConfig.label}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-text-muted">{aff.industry}</span>
                        <span className="text-accent-primary font-bold text-sm">{formatPercentage(aff.percentage)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
              {/* 데스크톱 테이블 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">회사명</th>
                      <th className="px-4 py-3 text-center font-medium text-text-secondary">관계</th>
                      <th className="px-4 py-3 text-right font-medium text-text-secondary">지분율</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">업종</th>
                      <th className="px-4 py-3 text-left font-medium text-text-secondary">설립일</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-border">
                    {sortedAffiliates.map((aff, index) => {
                      const relationConfig = affiliateRelationConfig[aff.relation]
                      return (
                        <tr key={`${aff.id}-${index}`} className="hover:bg-dark-hover">
                          <td className="px-4 py-3 font-medium">
                            {aff.company_id ? (
                              <Link
                                to={`/company/${aff.company_id}/report`}
                                className="text-accent-primary hover:underline"
                              >
                                {aff.name}
                              </Link>
                            ) : (
                              <span className="text-text-primary">{aff.name}</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${relationConfig.bg} ${relationConfig.text}`}>
                              {relationConfig.label}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-medium text-text-primary">{formatPercentage(aff.percentage)}</td>
                          <td className="px-4 py-3 text-text-secondary">{aff.industry}</td>
                          <td className="px-4 py-3 text-text-muted">{aff.founded_date || '-'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
