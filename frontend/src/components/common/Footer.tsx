import { Link, useNavigate } from 'react-router-dom'
import { useGraphStore, selectCurrentNavEntry } from '../../store'

function Footer() {
  const currentYear = new Date().getFullYear()
  const navigate = useNavigate()

  // 최근 조회한 회사 정보 가져오기
  const currentNavEntry = useGraphStore(selectCurrentNavEntry)
  const hasRecentCompany = !!currentNavEntry?.companyId

  // 관계도/보고서 클릭 핸들러 - 회사 정보 없으면 검색으로 이동
  const handleGraphClick = (e: React.MouseEvent) => {
    if (!hasRecentCompany) {
      e.preventDefault()
      navigate('/')
    }
  }

  const handleReportClick = (e: React.MouseEvent) => {
    if (!hasRecentCompany) {
      e.preventDefault()
      navigate('/')
    }
  }

  return (
    <footer className="bg-dark-surface border-t border-dark-border">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 bg-gradient-to-br from-accent-primary to-purple-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">R</span>
              </div>
              <span className="text-lg font-semibold text-text-primary">Raymontology</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed max-w-md">
              한국 주식시장의 숨겨진 이해관계자 네트워크를 분석하여
              개인 투자자를 보호하는 리스크 탐지 플랫폼
            </p>
            {/* Tech badges */}
            <div className="flex items-center gap-2 mt-4">
              <span className="px-2 py-1 text-[10px] font-mono bg-dark-card border border-dark-border rounded text-text-muted">
                NEO4J
              </span>
              <span className="px-2 py-1 text-[10px] font-mono bg-dark-card border border-dark-border rounded text-text-muted">
                POSTGRESQL
              </span>
              <span className="px-2 py-1 text-[10px] font-mono bg-dark-card border border-dark-border rounded text-text-muted">
                DART API
              </span>
            </div>
          </div>

          {/* Links */}
          <div>
            <h3 className="text-text-primary font-semibold mb-4 text-sm">서비스</h3>
            <ul className="space-y-2.5">
              <li>
                <Link to="/" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
                  회사 검색
                </Link>
              </li>
              <li>
                <Link
                  to={hasRecentCompany ? `/company/${currentNavEntry.companyId}/graph` : '/'}
                  onClick={handleGraphClick}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1.5"
                >
                  관계도 분석
                  {hasRecentCompany && (
                    <span className="text-xs text-text-muted">({currentNavEntry.companyName})</span>
                  )}
                </Link>
              </li>
              <li>
                <Link
                  to={hasRecentCompany ? `/company/${currentNavEntry.companyId}/report` : '/'}
                  onClick={handleReportClick}
                  className="text-sm text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1.5"
                >
                  리스크 보고서
                  {hasRecentCompany && (
                    <span className="text-xs text-text-muted">({currentNavEntry.companyName})</span>
                  )}
                </Link>
              </li>
            </ul>
          </div>

          {/* Info */}
          <div>
            <h3 className="text-text-primary font-semibold mb-4 text-sm">정보</h3>
            <ul className="space-y-2.5">
              <li>
                <span className="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
                  이용약관
                </span>
              </li>
              <li>
                <span className="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
                  개인정보처리방침
                </span>
              </li>
              <li>
                <span className="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
                  데이터 출처
                </span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="border-t border-dark-border mt-8 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-text-muted">
            &copy; {currentYear} Raymontology. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <p className="text-xs text-text-muted">
              데이터 출처: 금융감독원 DART OpenAPI
            </p>
            <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" title="시스템 정상" />
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
