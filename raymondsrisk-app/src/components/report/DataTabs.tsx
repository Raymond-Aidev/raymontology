import { useState } from 'react'
import type {
  CBIssuance,
  CBSubscriber,
  Officer,
  FinancialStatement,
  Shareholder,
  Affiliate,
} from '../../types/report'
import { colors } from '../../constants/colors'

interface DataTabsProps {
  cbIssuances: CBIssuance[]
  cbSubscribers: CBSubscriber[]
  officers: Officer[]
  financials: FinancialStatement[]
  shareholders: Shareholder[]
  affiliates: Affiliate[]
}

type TabKey = 'cb_issue' | 'cb_subscriber' | 'officer' | 'financial' | 'shareholder' | 'affiliate'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'cb_issue', label: 'CB' },
  { key: 'cb_subscriber', label: '인수' },
  { key: 'officer', label: '임원' },
  { key: 'financial', label: '재무' },
  { key: 'shareholder', label: '주주' },
  { key: 'affiliate', label: '계열' },
]

export default function DataTabs({
  cbIssuances,
  cbSubscribers,
  officers,
  financials,
  shareholders,
  affiliates,
}: DataTabsProps) {
  const [activeTab, setActiveTab] = useState<TabKey>('cb_issue')

  const formatCurrency = (amount: number) => {
    const absAmount = Math.abs(amount)
    const sign = amount < 0 ? '-' : ''
    if (absAmount >= 100000000) {
      return `${sign}${(absAmount / 100000000).toFixed(1)}억원`
    }
    return `${sign}${(absAmount / 10000).toFixed(0)}만원`
  }

  const formatPercentage = (percentage: number) => `${percentage.toFixed(1)}%`

  const sortedShareholders = [...shareholders].sort((a, b) => b.percentage - a.percentage)
  const sortedAffiliates = [...affiliates].sort((a, b) => b.percentage - a.percentage)

  return (
    <div>
      {/* 탭 헤더 */}
      <div style={{
        display: 'flex',
        gap: '4px',
        borderBottom: `1px solid ${colors.gray100}`,
        marginBottom: '16px',
        overflowX: 'auto',
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 12px',
              border: 'none',
              backgroundColor: 'transparent',
              color: activeTab === tab.key ? colors.blue500 : colors.gray500,
              fontSize: '13px',
              fontWeight: activeTab === tab.key ? '600' : '500',
              cursor: 'pointer',
              borderBottom: activeTab === tab.key ? `2px solid ${colors.blue500}` : '2px solid transparent',
              whiteSpace: 'nowrap',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* CB 발행 */}
      {activeTab === 'cb_issue' && (
        cbIssuances.length === 0 ? (
          <EmptyState message="CB 발행 내역이 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {cbIssuances.map((cb, index) => (
              <div key={`${cb.id}-${index}`} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: '600', color: colors.blue500 }}>{cb.issue_round || '-'}</span>
                  <StatusBadge status={cb.status} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                  <LabelValue label="발행일" value={cb.issue_date} />
                  <LabelValue label="만기일" value={cb.maturity_date} />
                  <LabelValue label="발행금액" value={formatCurrency(cb.amount)} bold />
                  <LabelValue label="전환가격" value={`${cb.conversion_price.toLocaleString()}원`} />
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* CB 인수인 */}
      {activeTab === 'cb_subscriber' && (
        cbSubscribers.length === 0 ? (
          <EmptyState message="CB 인수인 정보가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {cbSubscribers.map((sub, index) => (
              <div key={`${sub.id}-${index}`} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: '500', color: colors.gray900 }}>{sub.name}</span>
                  <TypeBadge type={sub.type} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                  <LabelValue label="인수금액" value={formatCurrency(sub.amount)} bold />
                  <LabelValue label="지분율" value={`${sub.ratio}%`} />
                </div>
                {sub.issue_rounds && sub.issue_rounds.length > 0 && (
                  <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {sub.issue_rounds.map((round, idx) => (
                      <span key={idx} style={{
                        padding: '2px 6px',
                        fontSize: '10px',
                        backgroundColor: `${colors.blue500}20`,
                        color: colors.blue500,
                        borderRadius: '4px',
                      }}>
                        {round}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {/* 임원 현황 */}
      {activeTab === 'officer' && (
        officers.length === 0 ? (
          <EmptyState message="임원 정보가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {officers.map((officer, index) => (
              <div key={`${officer.id}-${index}`} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontWeight: '500', color: colors.gray900 }}>{officer.name}</span>
                  {officer.is_current ? (
                    <span style={{ ...badgeStyle, backgroundColor: '#D1FAE5', color: '#059669' }}>재직</span>
                  ) : (
                    <span style={{ ...badgeStyle, backgroundColor: colors.gray100, color: colors.gray500 }}>퇴임</span>
                  )}
                </div>
                <p style={{ fontSize: '13px', color: colors.blue500, margin: '0 0 8px 0' }}>{officer.position}</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                  <LabelValue label="취임일" value={officer.tenure_start || '-'} />
                  <LabelValue label="퇴임일" value={officer.tenure_end || '-'} />
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* 재무제표 */}
      {activeTab === 'financial' && (
        financials.length === 0 ? (
          <EmptyState message="재무제표 정보가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {financials.map((fin, index) => {
              const debtRatio = fin.debt_ratio ?? (fin.equity > 0 ? (fin.total_liabilities / fin.equity) * 100 : 0)
              return (
                <div key={`${fin.year}-${fin.quarter || 'annual'}-${index}`} style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: '700', color: colors.blue500, fontSize: '16px' }}>{fin.year}</span>
                      {fin.quarter && (
                        <span style={{
                          padding: '2px 6px',
                          fontSize: '10px',
                          backgroundColor: `${colors.blue500}20`,
                          color: colors.blue500,
                          borderRadius: '4px',
                        }}>
                          {fin.quarter}
                        </span>
                      )}
                    </div>
                    <span style={{
                      fontSize: '12px',
                      fontWeight: '500',
                      color: debtRatio > 200 ? colors.red500 : debtRatio > 100 ? '#F59E0B' : '#10B981',
                    }}>
                      부채비율 {debtRatio.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                    <LabelValue label="매출액" value={formatCurrency(fin.revenue)} bold />
                    <LabelValue label="총자산" value={formatCurrency(fin.total_assets)} bold />
                    <LabelValue
                      label="영업이익"
                      value={formatCurrency(fin.operating_profit)}
                      color={fin.operating_profit < 0 ? colors.red500 : undefined}
                      bold
                    />
                    <LabelValue
                      label="당기순이익"
                      value={formatCurrency(fin.net_income)}
                      color={fin.net_income < 0 ? colors.red500 : undefined}
                      bold
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )
      )}

      {/* 주주 구성 */}
      {activeTab === 'shareholder' && (
        sortedShareholders.length === 0 ? (
          <EmptyState message="주주 정보가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sortedShareholders.map((sh, index) => (
              <div key={`${sh.id}-${index}`} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: '500', color: colors.gray900 }}>{sh.name}</span>
                  <span style={{ fontWeight: '700', color: colors.blue500 }}>{formatPercentage(sh.percentage)}</span>
                </div>
                {sh.type === 'major' && (
                  <span style={{ ...badgeStyle, backgroundColor: '#DBEAFE', color: '#1D4ED8', marginTop: '8px', display: 'inline-block' }}>
                    대주주
                  </span>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {/* 계열회사 */}
      {activeTab === 'affiliate' && (
        sortedAffiliates.length === 0 ? (
          <EmptyState message="계열회사 정보가 없습니다" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sortedAffiliates.map((aff, index) => (
              <div key={`${aff.id}-${index}`} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: '500', color: colors.gray900 }}>{aff.name}</span>
                  <RelationBadge relation={aff.relation} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px' }}>
                  <span style={{ color: colors.gray500 }}>{aff.industry}</span>
                  <span style={{ color: colors.blue500, fontWeight: '600' }}>{formatPercentage(aff.percentage)}</span>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}

// 공통 스타일
const cardStyle: React.CSSProperties = {
  backgroundColor: colors.gray50,
  borderRadius: '12px',
  padding: '12px',
  border: `1px solid ${colors.gray100}`,
}

const badgeStyle: React.CSSProperties = {
  padding: '3px 8px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: '600',
}

// 유틸리티 컴포넌트
function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
      <p style={{ color: colors.gray500, fontSize: '14px' }}>{message}</p>
    </div>
  )
}

function LabelValue({
  label,
  value,
  bold,
  color,
}: {
  label: string
  value: string
  bold?: boolean
  color?: string
}) {
  return (
    <div>
      <span style={{ color: colors.gray500, display: 'block', marginBottom: '2px' }}>{label}</span>
      <span style={{ color: color || colors.gray900, fontWeight: bold ? '500' : '400' }}>{value}</span>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    active: { bg: '#D1FAE5', text: '#059669', label: '유효' },
    converted: { bg: '#DBEAFE', text: '#1D4ED8', label: '전환' },
    redeemed: { bg: colors.gray100, text: colors.gray500, label: '상환' },
  }
  const c = config[status] || config.active
  return <span style={{ ...badgeStyle, backgroundColor: c.bg, color: c.text }}>{c.label}</span>
}

function TypeBadge({ type }: { type: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    institution: { bg: '#DBEAFE', text: '#1D4ED8', label: '기관' },
    related: { bg: '#FFEDD5', text: '#EA580C', label: '특수관계인' },
    individual: { bg: colors.gray100, text: colors.gray500, label: '개인' },
  }
  const c = config[type] || config.individual
  return <span style={{ ...badgeStyle, backgroundColor: c.bg, color: c.text }}>{c.label}</span>
}

function RelationBadge({ relation }: { relation: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    subsidiary: { bg: '#DBEAFE', text: '#1D4ED8', label: '자회사' },
    grandchild: { bg: '#E0F2FE', text: '#0284C7', label: '손자회사' },
    associate: { bg: colors.gray100, text: colors.gray500, label: '관계회사' },
  }
  const c = config[relation] || config.associate
  return <span style={{ ...badgeStyle, backgroundColor: c.bg, color: c.text }}>{c.label}</span>
}
