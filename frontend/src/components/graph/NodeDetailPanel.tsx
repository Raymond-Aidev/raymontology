import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { GraphNode } from '../../types/graph'
import { nodeTypeColors } from '../../types/graph'
import { riskLevelColors, gradeColors } from '../../types/company'
import {
  fetchOfficerCareer,
  fetchSubscriberInvestments,
  fetchShareholderDetail,
  fetchShareholderHistory,
  fetchShareholderCompanies,
  fetchCBSubscribers,
  type OfficerCareer,
  type SubscriberInvestment,
  type ShareholderDetail,
  type ShareholderHistory,
  type ShareholderCompany,
  type CBSubscriberItem,
} from '../../api/graph'

interface NodeDetailPanelProps {
  node: GraphNode | null
  onClose: () => void
  onRecenter?: (node: GraphNode) => void
  onNavigateToCompany?: (node: GraphNode) => void
}

// 주주 유형 레이블
const shareholderTypeLabels: Record<string, string> = {
  individual: '개인',
  corporation: '법인',
  institution: '기관투자자',
}

export default function NodeDetailPanel({ node, onClose, onRecenter, onNavigateToCompany: _onNavigateToCompany }: NodeDetailPanelProps) {
  // Note: _onNavigateToCompany is available for future use when company cards are clickable
  // 임원 경력 상태
  const [career, setCareer] = useState<OfficerCareer[]>([])
  const [careerLoading, setCareerLoading] = useState(false)
  const [careerError, setCareerError] = useState<string | null>(null)

  // 인수인 투자 이력 상태
  const [investments, setInvestments] = useState<SubscriberInvestment[]>([])
  const [investmentsLoading, setInvestmentsLoading] = useState(false)
  const [investmentsError, setInvestmentsError] = useState<string | null>(null)

  // 대주주 상태
  const [shareholderDetail, setShareholderDetail] = useState<ShareholderDetail | null>(null)
  const [shareholderHistory, setShareholderHistory] = useState<ShareholderHistory[]>([])
  const [shareholderCompanies, setShareholderCompanies] = useState<ShareholderCompany[]>([])
  const [shareholderLoading, setShareholderLoading] = useState(false)
  const [shareholderError, setShareholderError] = useState<string | null>(null)

  // CB 인수자 상태
  const [cbSubscribers, setCbSubscribers] = useState<CBSubscriberItem[]>([])
  const [cbSubscribersLoading, setCbSubscribersLoading] = useState(false)
  const [cbSubscribersError, setCbSubscribersError] = useState<string | null>(null)

  // 임원 노드일 때 경력 데이터 로드
  useEffect(() => {
    if (node?.type === 'officer') {
      setCareerLoading(true)
      setCareerError(null)
      fetchOfficerCareer(node.id)
        .then(data => {
          setCareer(data)
        })
        .catch(() => {
          setCareerError('경력 정보를 불러오는데 실패했습니다')
        })
        .finally(() => {
          setCareerLoading(false)
        })
    } else {
      setCareer([])
      setCareerError(null)
    }
  }, [node?.id, node?.type])

  // 인수인 노드일 때 투자 이력 데이터 로드
  useEffect(() => {
    if (node?.type === 'subscriber') {
      setInvestmentsLoading(true)
      setInvestmentsError(null)
      fetchSubscriberInvestments(node.id)
        .then(data => {
          setInvestments(data)
        })
        .catch(() => {
          setInvestmentsError('투자 이력을 불러오는데 실패했습니다')
        })
        .finally(() => {
          setInvestmentsLoading(false)
        })
    } else {
      setInvestments([])
      setInvestmentsError(null)
    }
  }, [node?.id, node?.type])

  // CB 노드일 때 인수자 데이터 로드
  useEffect(() => {
    if (node?.type === 'cb') {
      setCbSubscribersLoading(true)
      setCbSubscribersError(null)
      fetchCBSubscribers(node.id)
        .then(data => {
          setCbSubscribers(data)
        })
        .catch(() => {
          setCbSubscribersError('인수자 정보를 불러오는데 실패했습니다')
        })
        .finally(() => {
          setCbSubscribersLoading(false)
        })
    } else {
      setCbSubscribers([])
      setCbSubscribersError(null)
    }
  }, [node?.id, node?.type])

  // 대주주 노드일 때 상세 데이터 로드
  useEffect(() => {
    if (node?.type === 'shareholder') {
      setShareholderLoading(true)
      setShareholderError(null)

      // 병렬로 모든 데이터 로드
      Promise.all([
        fetchShareholderDetail(node.id),
        fetchShareholderHistory(node.id),
        fetchShareholderCompanies(node.id),
      ])
        .then(([detail, history, companies]) => {
          setShareholderDetail(detail)
          setShareholderHistory(history.slice(0, 5)) // 최근 5건만
          setShareholderCompanies(companies)
        })
        .catch(() => {
          setShareholderError('대주주 정보를 불러오는데 실패했습니다')
        })
        .finally(() => {
          setShareholderLoading(false)
        })
    } else {
      setShareholderDetail(null)
      setShareholderHistory([])
      setShareholderCompanies([])
      setShareholderError(null)
    }
  }, [node?.id, node?.type])

  if (!node) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-text-muted p-6">
        <div className="w-16 h-16 mb-4 rounded-full bg-dark-hover flex items-center justify-center">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-center text-sm">노드를 클릭하여<br />상세 정보를 확인하세요</p>
      </div>
    )
  }

  const typeColor = nodeTypeColors[node.type]
  const riskColor = node.risk_level ? riskLevelColors[node.risk_level] : null
  const gradeColor = node.investment_grade ? gradeColors[node.investment_grade] : null

  return (
    <div className="h-full flex flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between pb-4 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: typeColor.fill }}
          />
          <span className="text-xs text-text-muted uppercase tracking-wide">{typeColor.label}</span>
        </div>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary transition-colors p-1 rounded hover:bg-dark-hover"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* 이름 */}
      <div className="py-4 border-b border-dark-border">
        <h2 className="text-lg font-semibold text-text-primary">{node.name}</h2>
        {node.corp_code && (
          <p className="text-xs text-text-muted mt-1 font-mono">기업코드: {node.corp_code}</p>
        )}
      </div>

      {/* 상세 정보 */}
      <div className="flex-1 py-4 space-y-4 overflow-y-auto">
        {/* 회사 노드 상세 */}
        {node.type === 'company' && (
          <>
            {riskColor && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">리스크 레벨</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${riskColor.bg} ${riskColor.text}`}>
                  {riskColor.label}
                </span>
              </div>
            )}
            {gradeColor && node.investment_grade && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">투자등급</span>
                <span className={`font-bold font-mono ${gradeColor}`}>
                  {node.investment_grade}
                </span>
              </div>
            )}
          </>
        )}

        {/* 임원 노드 상세 */}
        {node.type === 'officer' && (
          <>
            {node.position && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">직책</span>
                <span className="font-medium text-text-primary text-sm">{node.position}</span>
              </div>
            )}

            {/* 경력 타임라인 섹션 */}
            <div className="pt-4 border-t border-dark-border">
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">경력 이력</h3>

              {/* 로딩 스켈레톤 */}
              {careerLoading && (
                <div className="space-y-3">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-dark-hover rounded w-3/4 mb-1" />
                      <div className="h-3 bg-dark-surface rounded w-1/2" />
                    </div>
                  ))}
                </div>
              )}

              {/* 에러 메시지 */}
              {careerError && !careerLoading && (
                <p className="text-xs text-accent-danger">{careerError}</p>
              )}

              {/* 데이터 없음 */}
              {!careerLoading && !careerError && career.length === 0 && (
                <p className="text-xs text-text-muted">경력 정보 없음</p>
              )}

              {/* 경력 타임라인 */}
              {!careerLoading && !careerError && career.length > 0 && (
                <div className="space-y-4">
                  {/* 상장사 임원 DB (source="db") */}
                  {career.filter(c => c.source === 'db').length > 0 && (
                    <div className={`${career.filter(c => c.source === 'db').length >= 3 ? 'border border-accent-danger/50 rounded-lg p-2 bg-accent-danger/10' : ''}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-medium text-accent-primary">상장사 임원 DB</span>
                        <span className={`text-xs ${career.filter(c => c.source === 'db').length >= 3 ? 'text-accent-danger font-semibold' : 'text-text-muted'}`}>({career.filter(c => c.source === 'db').length}건)</span>
                        {career.filter(c => c.source === 'db').length >= 3 && (
                          <span className="text-xs bg-accent-danger/20 text-accent-danger px-1.5 py-0.5 rounded font-medium">다수 재직</span>
                        )}
                      </div>
                      <div className="relative">
                        <div className="absolute left-2 top-2 bottom-2 w-0.5 bg-accent-primary/30" />
                        <div className="space-y-3">
                          {career.filter(c => c.source === 'db').map((item, index) => (
                            <div key={`db-${index}`} className="relative pl-6">
                              <div
                                className={`absolute left-0 top-1.5 w-4 h-4 rounded-full border-2 ${
                                  item.is_current && (item.start_date || item.end_date)
                                    ? 'bg-accent-success border-accent-success'
                                    : 'bg-dark-card border-accent-primary'
                                }`}
                              />
                              <div className={`${item.is_current && (item.start_date || item.end_date) ? 'bg-accent-success/10 rounded-lg p-2 -ml-1' : ''}`}>
                                <div className="flex items-center gap-2 flex-wrap">
                                  {item.company_id ? (
                                    <Link
                                      to={`/company/${item.company_id}/graph`}
                                      className="font-medium text-accent-danger hover:text-accent-danger/80 text-sm cursor-pointer"
                                    >
                                      {item.company_name}
                                    </Link>
                                  ) : (
                                    <span className="font-medium text-text-primary text-sm">
                                      {item.company_name}
                                    </span>
                                  )}
                                  <span className="text-xs bg-accent-danger/20 text-accent-danger px-1 py-0.5 rounded">상장</span>
                                  {item.is_current && (item.start_date || item.end_date) ? (
                                    <span className="text-xs bg-accent-success/20 text-accent-success px-1.5 py-0.5 rounded">재직중</span>
                                  ) : null}
                                </div>
                                <p className="text-xs text-text-secondary mt-0.5">{item.position}</p>
                                {(item.start_date || item.end_date) && (
                                  <p className="text-xs text-text-muted font-mono mt-0.5">
                                    {item.start_date || '?'} ~ {item.is_current ? '현재' : (item.end_date || '?')}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 공시 파일 확인 (source="disclosure") */}
                  {career.filter(c => c.source === 'disclosure').length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-medium text-text-muted">공시 파일 확인</span>
                        <span className="text-xs text-text-muted">({career.filter(c => c.source === 'disclosure').length}건)</span>
                      </div>
                      <div className="relative">
                        <div className="absolute left-2 top-2 bottom-2 w-0.5 bg-dark-border" />
                        <div className="space-y-3">
                          {career.filter(c => c.source === 'disclosure').map((item, index) => (
                            <div key={`disc-${index}`} className="relative pl-6">
                              <div className={`absolute left-0 top-1.5 w-4 h-4 rounded-full border-2 ${
                                item.is_current ? 'bg-text-muted border-text-muted' : 'bg-dark-card border-dark-border'
                              }`} />
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="font-medium text-text-secondary text-sm">{item.company_name}</span>
                                  {item.is_current && (
                                    <span className="text-xs bg-dark-hover text-text-muted px-1.5 py-0.5 rounded">現</span>
                                  )}
                                  {!item.is_current && (
                                    <span className="text-xs bg-dark-surface text-text-muted px-1.5 py-0.5 rounded">前</span>
                                  )}
                                </div>
                                <p className="text-xs text-text-muted mt-0.5">{item.position}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* CB 노드 상세 */}
        {node.type === 'cb' && (
          <>
            {node.amount !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">발행금액</span>
                <span className="font-bold text-data-cb font-mono">
                  {(node.amount / 100000000).toFixed(1)}억원
                </span>
              </div>
            )}
            {node.issue_date && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">발행일</span>
                <span className="font-medium text-text-primary font-mono text-sm">{node.issue_date}</span>
              </div>
            )}

            {/* 인수자 목록 섹션 */}
            <div className="pt-4 border-t border-dark-border">
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">인수자 목록</h3>

              {/* 로딩 스켈레톤 */}
              {cbSubscribersLoading && (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="animate-pulse flex justify-between">
                      <div className="h-4 bg-dark-hover rounded w-1/3" />
                      <div className="h-4 bg-dark-surface rounded w-1/4" />
                    </div>
                  ))}
                </div>
              )}

              {/* 에러 메시지 */}
              {cbSubscribersError && !cbSubscribersLoading && (
                <p className="text-xs text-accent-danger">{cbSubscribersError}</p>
              )}

              {/* 데이터 없음 */}
              {!cbSubscribersLoading && !cbSubscribersError && cbSubscribers.length === 0 && (
                <p className="text-xs text-text-muted">인수자 정보 없음</p>
              )}

              {/* 인수자 목록 */}
              {!cbSubscribersLoading && !cbSubscribersError && cbSubscribers.length > 0 && (
                <div className="space-y-2">
                  {cbSubscribers.map((sub, index) => (
                    <div
                      key={index}
                      className={`rounded-lg p-2 ${sub.is_related_party ? 'bg-accent-danger/10 border border-accent-danger/30' : 'bg-dark-surface'}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-text-primary text-sm">
                            {sub.subscriber_name}
                          </span>
                          {sub.is_related_party && (
                            <span className="text-xs bg-accent-danger/20 text-accent-danger px-1 py-0.5 rounded">특수관계</span>
                          )}
                        </div>
                        {sub.subscription_amount && (
                          <span className="text-sm font-bold text-data-subscriber font-mono">
                            {(sub.subscription_amount / 100000000).toFixed(1)}억원
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-0.5">
                        <span className="text-xs text-text-muted">
                          {sub.subscriber_type || '일반'}
                        </span>
                        {sub.subscription_quantity && (
                          <span className="text-xs text-text-muted font-mono">
                            {sub.subscription_quantity.toLocaleString()}주
                          </span>
                        )}
                      </div>
                      {sub.relationship && (
                        <p className="text-xs text-accent-danger mt-0.5">{sub.relationship}</p>
                      )}
                    </div>
                  ))}

                  {/* 총 인수금액 */}
                  <div className="pt-2 mt-2 border-t border-dark-border flex justify-between items-center">
                    <span className="text-xs text-text-muted uppercase tracking-wide">총 인수금액</span>
                    <span className="text-sm font-bold text-text-primary font-mono">
                      {(cbSubscribers.reduce((sum, sub) => sum + (sub.subscription_amount || 0), 0) / 100000000).toFixed(1)}억원
                    </span>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* 인수인 노드 상세 */}
        {node.type === 'subscriber' && (
          <>
            {node.amount !== undefined && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">투자금액</span>
                <span className="font-bold text-data-subscriber font-mono">
                  {(node.amount / 100000000).toFixed(1)}억원
                </span>
              </div>
            )}
            {node.issue_date && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted uppercase tracking-wide">투자일</span>
                <span className="font-medium text-text-primary font-mono text-sm">{node.issue_date}</span>
              </div>
            )}

            {/* 법인/단체 기본정보 */}
            {(node.representative_name || node.gp_name || node.largest_shareholder_name) && (
              <div className="pt-4 border-t border-dark-border">
                <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">법인/단체 기본정보</h3>
                <div className="space-y-2 bg-dark-surface rounded-lg p-3">
                  {node.representative_name && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-text-muted">대표이사</span>
                      <span className="text-sm font-medium text-accent-primary">{node.representative_name}</span>
                    </div>
                  )}
                  {node.gp_name && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-text-muted">업무집행자(GP)</span>
                      <span className="text-sm font-medium text-text-primary">{node.gp_name}</span>
                    </div>
                  )}
                  {node.largest_shareholder_name && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-text-muted">최대주주</span>
                      <span className="text-sm font-medium text-text-primary">{node.largest_shareholder_name}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 타사 CB 투자 이력 섹션 */}
            <div className="pt-4 border-t border-dark-border">
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">타사 CB 투자 이력</h3>

              {/* 로딩 스켈레톤 */}
              {investmentsLoading && (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="animate-pulse flex justify-between">
                      <div className="h-4 bg-dark-hover rounded w-1/3" />
                      <div className="h-4 bg-dark-surface rounded w-1/4" />
                    </div>
                  ))}
                </div>
              )}

              {/* 에러 메시지 */}
              {investmentsError && !investmentsLoading && (
                <p className="text-xs text-accent-danger">{investmentsError}</p>
              )}

              {/* 데이터 없음 */}
              {!investmentsLoading && !investmentsError && investments.length === 0 && (
                <p className="text-xs text-text-muted">투자 이력 없음</p>
              )}

              {/* 투자 이력 테이블 */}
              {!investmentsLoading && !investmentsError && investments.length > 0 && (
                <div className="space-y-2">
                  {investments.map((inv, index) => (
                    <div
                      key={index}
                      className="bg-dark-surface rounded-lg p-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-text-primary text-sm">
                          {inv.company_name}
                        </span>
                        <span className="text-sm font-bold text-data-subscriber font-mono">
                          {(inv.amount / 100000000).toFixed(1)}억원
                        </span>
                      </div>
                      <p className="text-xs text-text-muted font-mono mt-0.5">
                        {inv.cb_issue_date}
                      </p>
                    </div>
                  ))}

                  {/* 총 투자금액 */}
                  <div className="pt-2 mt-2 border-t border-dark-border flex justify-between items-center">
                    <span className="text-xs text-text-muted uppercase tracking-wide">총 투자금액</span>
                    <span className="text-sm font-bold text-text-primary font-mono">
                      {(investments.reduce((sum, inv) => sum + inv.amount, 0) / 100000000).toFixed(1)}억원
                    </span>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* 대주주 노드 상세 */}
        {node.type === 'shareholder' && (
          <>
            {/* 로딩 스켈레톤 */}
            {shareholderLoading && (
              <div className="space-y-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="animate-pulse flex justify-between">
                    <div className="h-4 bg-dark-hover rounded w-1/3" />
                    <div className="h-4 bg-dark-surface rounded w-1/4" />
                  </div>
                ))}
              </div>
            )}

            {/* 에러 메시지 */}
            {shareholderError && !shareholderLoading && (
              <p className="text-xs text-accent-danger">{shareholderError}</p>
            )}

            {/* 대주주 상세 정보 */}
            {!shareholderLoading && !shareholderError && shareholderDetail && (
              <>
                {/* 기본 정보 */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-muted uppercase tracking-wide">주주 유형</span>
                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-data-shareholder/20 text-data-shareholder">
                    {shareholderTypeLabels[shareholderDetail.type] || shareholderDetail.type}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-muted uppercase tracking-wide">지분율</span>
                  <span className="font-bold text-text-primary font-mono">{(shareholderDetail.percentage ?? 0).toFixed(1)}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-muted uppercase tracking-wide">보유 주식 수</span>
                  <span className="font-medium text-text-primary font-mono text-sm">{(shareholderDetail.shares ?? 0).toLocaleString()}주</span>
                </div>

                {/* 보유 정보 */}
                {shareholderDetail.acquisition_date && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted uppercase tracking-wide">취득일</span>
                    <span className="text-text-primary font-mono text-sm">{shareholderDetail.acquisition_date}</span>
                  </div>
                )}
                {shareholderDetail.acquisition_price != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted uppercase tracking-wide">취득가액</span>
                    <span className="text-text-primary font-mono text-sm">{shareholderDetail.acquisition_price.toLocaleString()}원</span>
                  </div>
                )}
                {shareholderDetail.current_value != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted uppercase tracking-wide">현재가</span>
                    <span className="text-text-primary font-mono text-sm">{shareholderDetail.current_value.toLocaleString()}원</span>
                  </div>
                )}
                {shareholderDetail.profit_loss != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted uppercase tracking-wide">평가손익</span>
                    <span className={`font-semibold font-mono ${shareholderDetail.profit_loss >= 0 ? 'text-accent-danger' : 'text-accent-primary'}`}>
                      {shareholderDetail.profit_loss >= 0 ? '+' : ''}{shareholderDetail.profit_loss.toLocaleString()}원
                    </span>
                  </div>
                )}

                {/* 변동 이력 섹션 */}
                <div className="pt-4 border-t border-dark-border">
                  <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">지분 변동 이력</h3>

                  {shareholderHistory.length === 0 ? (
                    <p className="text-xs text-text-muted">변동 이력 없음</p>
                  ) : (
                    <div className="space-y-2">
                      {shareholderHistory.map((hist, index) => (
                        <div key={index} className="bg-dark-surface rounded-lg p-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-text-secondary font-mono">{hist.date || '-'}</span>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-text-primary font-mono">{(hist.percentage ?? 0).toFixed(1)}%</span>
                              {(hist.change ?? 0) !== 0 && (
                                <span className={`text-xs font-semibold font-mono ${(hist.change ?? 0) > 0 ? 'text-accent-danger' : 'text-accent-primary'}`}>
                                  {(hist.change ?? 0) > 0 ? '+' : ''}{(hist.change ?? 0).toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>
                          {hist.reason && (
                            <p className="text-xs text-text-muted mt-0.5">{hist.reason}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 관련 회사 섹션 */}
                <div className="pt-4 border-t border-dark-border">
                  <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-3">보유 지분 현황</h3>

                  {shareholderCompanies.length === 0 ? (
                    <p className="text-xs text-text-muted">보유 지분 정보 없음</p>
                  ) : (
                    <div className="space-y-2">
                      {shareholderCompanies.map((company, index) => (
                        <div key={index} className="bg-dark-surface rounded-lg p-2">
                          <div className="flex items-center justify-between">
                            <Link
                              to={`/company/${company.company_id}/report`}
                              className="font-medium text-accent-primary hover:text-accent-primary/80 text-sm"
                            >
                              {company.company_name}
                            </Link>
                            <span className="text-sm font-semibold text-data-shareholder font-mono">
                              {(company.percentage ?? 0).toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-xs text-text-muted font-mono mt-0.5">
                            {(company.shares ?? 0).toLocaleString()}주
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}

        {/* 계열사 노드 상세 */}
        {node.type === 'affiliate' && (
          <>
            <p className="text-xs text-text-muted">
              계열사 관계 정보는 추후 업데이트 예정입니다.
            </p>
          </>
        )}

        {/* 노드 ID */}
        <div className="pt-4 border-t border-dark-border">
          <p className="text-xs text-text-muted font-mono">ID: {node.id}</p>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="pt-4 border-t border-dark-border space-y-2">
        {/* 노드로 이동 버튼 */}
        {onRecenter && (
          <button
            onClick={() => onRecenter(node)}
            className="w-full py-2.5 px-4 bg-accent-primary text-white text-sm font-medium rounded-lg hover:bg-accent-primary/90 transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l-4 4m0 0l-4-4m4 4V3m0 18a9 9 0 110-18 9 9 0 010 18z" />
            </svg>
            노드로 이동
          </button>
        )}
        {/* 분석 보고서 링크 (회사 노드만) */}
        {node.type === 'company' && (
          <Link
            to={`/company/${node.id}/report`}
            className="block w-full py-2.5 px-4 bg-accent-purple text-white text-sm font-medium text-center rounded-lg hover:bg-accent-purple/90 transition-all"
          >
            분석 보고서 보기
          </Link>
        )}
      </div>
    </div>
  )
}
