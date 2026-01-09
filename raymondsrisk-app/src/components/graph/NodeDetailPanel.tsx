import { useState, useEffect } from 'react'
import type { GraphNode } from '../../types/graph'
import { nodeTypeColors } from '../../types/graph'
import { colors } from '../../constants/colors'
import { fetchOfficerCareer, type OfficerCareerResult } from '../../api/graph'

interface NodeDetailPanelProps {
  node: GraphNode | null
  onClose: () => void
  onNavigateToCompany?: (node: GraphNode) => void
}

export default function NodeDetailPanel({
  node,
  onClose,
  onNavigateToCompany,
}: NodeDetailPanelProps) {
  const [officerCareer, setOfficerCareer] = useState<OfficerCareerResult | null>(null)
  const [isLoadingCareer, setIsLoadingCareer] = useState(false)

  // 임원 경력 로드
  useEffect(() => {
    if (node?.type === 'officer') {
      setIsLoadingCareer(true)
      fetchOfficerCareer(node.id)
        .then(setOfficerCareer)
        .finally(() => setIsLoadingCareer(false))
    } else {
      setOfficerCareer(null)
    }
  }, [node?.id, node?.type])

  if (!node) {
    return (
      <div style={{
        padding: '20px',
        textAlign: 'center',
        color: colors.gray500,
      }}>
        <p style={{ fontSize: '14px' }}>노드를 선택하면<br />상세 정보가 표시됩니다</p>
      </div>
    )
  }

  const nodeColor = nodeTypeColors[node.type]

  // 금액 포맷
  const formatAmount = (amount: number) => {
    if (amount >= 100000000) {
      return `${(amount / 100000000).toFixed(1)}억원`
    }
    if (amount >= 10000) {
      return `${(amount / 10000).toFixed(0)}만원`
    }
    return `${amount.toLocaleString()}원`
  }

  return (
    <div style={{ padding: '16px' }}>
      {/* 헤더 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            backgroundColor: nodeColor.fill,
          }} />
          <span style={{
            fontSize: '12px',
            fontWeight: '500',
            color: nodeColor.fill,
            backgroundColor: `${nodeColor.fill}15`,
            padding: '2px 8px',
            borderRadius: '4px',
          }}>
            {nodeColor.label}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '4px 8px',
            fontSize: '18px',
            color: colors.gray500,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          ×
        </button>
      </div>

      {/* 노드 이름 */}
      <h3 style={{
        fontSize: '18px',
        fontWeight: '700',
        color: colors.gray900,
        margin: '0 0 12px 0',
      }}>
        {node.name}
      </h3>

      {/* 회사 노드 */}
      {node.type === 'company' && (
        <div style={{ marginBottom: '16px' }}>
          {node.corp_code && (
            <div style={{ fontSize: '13px', color: colors.gray500, marginBottom: '8px' }}>
              종목코드: {node.corp_code}
            </div>
          )}
          {node.investment_grade && (
            <div style={{
              display: 'inline-block',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '600',
              backgroundColor: '#FEF3C7',
              color: '#D97706',
            }}>
              투자등급 {node.investment_grade}
            </div>
          )}
          {onNavigateToCompany && node.corp_code && (
            <button
              onClick={() => onNavigateToCompany(node)}
              style={{
                marginTop: '12px',
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: colors.blue500,
                color: colors.white,
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              이 회사 관계도 보기
            </button>
          )}
        </div>
      )}

      {/* 임원 노드 */}
      {node.type === 'officer' && (
        <div style={{ marginBottom: '16px' }}>
          {node.position && (
            <div style={{ fontSize: '14px', color: colors.gray600, marginBottom: '8px' }}>
              직책: {node.position}
            </div>
          )}

          {/* 경력 배지 */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {node.listedCareerCount !== undefined && node.listedCareerCount >= 3 && (
              <span style={{
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '600',
                backgroundColor: '#FEE2E2',
                color: '#DC2626',
              }}>
                상장사 {node.listedCareerCount}개 경력
              </span>
            )}
            {node.deficitCareerCount !== undefined && node.deficitCareerCount >= 1 && (
              <span style={{
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '600',
                backgroundColor: '#FFEDD5',
                color: '#EA580C',
              }}>
                적자기업 {node.deficitCareerCount}개 경력
              </span>
            )}
          </div>

          {/* 경력 상세 */}
          {isLoadingCareer ? (
            <div style={{ fontSize: '13px', color: colors.gray500 }}>경력 로딩 중...</div>
          ) : officerCareer && officerCareer.careers.length > 0 ? (
            <div>
              <div style={{ fontSize: '13px', fontWeight: '600', color: colors.gray600, marginBottom: '8px' }}>
                상장사 임원 DB ({officerCareer.careers.length}건)
              </div>
              <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
                {officerCareer.careers.slice(0, 5).map((career, idx) => (
                  <div key={idx} style={{
                    padding: '8px',
                    backgroundColor: colors.gray50,
                    borderRadius: '6px',
                    marginBottom: '6px',
                    fontSize: '13px',
                  }}>
                    <div style={{ fontWeight: '500', color: colors.gray900 }}>
                      {career.company_name}
                      {career.is_listed && (
                        <span style={{ marginLeft: '4px', color: colors.blue500 }}>(상장)</span>
                      )}
                    </div>
                    <div style={{ color: colors.gray500 }}>{career.position}</div>
                  </div>
                ))}
                {officerCareer.careers.length > 5 && (
                  <div style={{ fontSize: '12px', color: colors.gray500, textAlign: 'center' }}>
                    +{officerCareer.careers.length - 5}개 더보기
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* 사업보고서 주요경력 원문 (v2.4) */}
          {!isLoadingCareer && officerCareer?.careerRawText && (
            <div style={{ marginTop: '16px' }}>
              <div style={{
                fontSize: '13px',
                fontWeight: '600',
                color: '#F59E0B',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                사업보고서 주요경력
                <span style={{ fontSize: '11px', color: colors.gray500, fontWeight: '400' }}>(원문)</span>
              </div>
              <div style={{
                backgroundColor: colors.gray50,
                borderRadius: '8px',
                padding: '12px',
                border: `1px solid ${colors.gray100}`,
              }}>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontSize: '12px',
                  color: colors.gray600,
                  lineHeight: '1.6',
                  margin: 0,
                  fontFamily: 'inherit',
                  maxHeight: '200px',
                  overflowY: 'auto',
                }}>
                  {officerCareer.careerRawText}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* CB 노드 */}
      {node.type === 'cb' && (
        <div style={{ marginBottom: '16px' }}>
          {node.bond_name && (
            <div style={{ fontSize: '14px', color: colors.gray600, marginBottom: '8px' }}>
              {node.bond_name}
            </div>
          )}
          {node.issue_date && (
            <div style={{ fontSize: '13px', color: colors.gray500, marginBottom: '4px' }}>
              발행일: {node.issue_date}
            </div>
          )}
          {node.amount && (
            <div style={{ fontSize: '13px', color: colors.gray500 }}>
              발행금액: {formatAmount(node.amount)}
            </div>
          )}
        </div>
      )}

      {/* 투자자 노드 */}
      {node.type === 'subscriber' && (
        <div style={{ marginBottom: '16px' }}>
          {node.representative_name && (
            <div style={{ fontSize: '13px', color: colors.gray600, marginBottom: '4px' }}>
              대표: {node.representative_name}
            </div>
          )}
          {node.gp_name && (
            <div style={{ fontSize: '13px', color: colors.gray600, marginBottom: '4px' }}>
              업무집행자: {node.gp_name}
            </div>
          )}
          {node.largest_shareholder_name && (
            <div style={{ fontSize: '13px', color: colors.gray600 }}>
              최대주주: {node.largest_shareholder_name}
            </div>
          )}
        </div>
      )}

      {/* 대주주 노드 */}
      {node.type === 'shareholder' && (
        <div style={{ marginBottom: '16px' }}>
          {node.shareholder_type && (
            <div style={{ fontSize: '13px', color: colors.gray600, marginBottom: '4px' }}>
              유형: {node.shareholder_type === 'individual' ? '개인' :
                     node.shareholder_type === 'corporation' ? '법인' : '기관'}
            </div>
          )}
          {node.percentage && (
            <div style={{ fontSize: '13px', color: colors.gray600, marginBottom: '4px' }}>
              지분율: {node.percentage.toFixed(2)}%
            </div>
          )}
          {node.shares && (
            <div style={{ fontSize: '13px', color: colors.gray600 }}>
              보유주식: {node.shares.toLocaleString()}주
            </div>
          )}
        </div>
      )}
    </div>
  )
}
