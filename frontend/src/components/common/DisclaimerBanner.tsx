interface DisclaimerBannerProps {
  variant?: 'warning' | 'info'
  className?: string
}

/**
 * 투자 면책 고지 배너
 * - 투자 권유가 아님을 명시
 * - 데이터 정확성 보장 불가
 * - 투자 손실 책임 없음
 */
export function DisclaimerBanner({ variant = 'info', className = '' }: DisclaimerBannerProps) {
  const isWarning = variant === 'warning'

  return (
    <div className={`rounded-lg border ${
      isWarning
        ? 'bg-yellow-500/5 border-yellow-500/20'
        : 'bg-theme-surface border-theme-border'
    } p-4 ${className}`}>
      <div className="flex gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {isWarning ? (
            <svg className="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>
        <div className="text-xs text-text-secondary leading-relaxed space-y-1">
          <p>
            <strong className="text-text-primary">투자 유의사항:</strong> 본 서비스에서 제공하는 정보는
            투자 권유나 추천이 아니며, 정보 제공 목적으로만 제공됩니다.
          </p>
          <p>
            모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 하며,
            본 서비스 이용으로 인한 투자 손실에 대해 당사는 책임지지 않습니다.
          </p>
          <p className="text-text-muted">
            데이터 출처: 금융감독원 DART OpenAPI | 데이터의 정확성, 완전성, 최신성을 보장하지 않습니다.
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * 리스크 점수 안내 문구 (간단 버전)
 */
export function RiskScoreDisclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-[10px] text-text-muted ${className}`}>
      리스크 점수는 알고리즘 기반 산출 결과이며, 투자 판단의 유일한 기준으로 사용해서는 안 됩니다.
    </p>
  )
}

/**
 * Footer용 간단 면책 문구
 */
export function FooterDisclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-[10px] text-text-muted leading-relaxed ${className}`}>
      본 서비스는 투자 권유가 아닌 정보 제공 목적입니다. 투자 결정은 본인 책임이며,
      당사는 투자 손실에 대해 책임지지 않습니다.
    </p>
  )
}

export default DisclaimerBanner
