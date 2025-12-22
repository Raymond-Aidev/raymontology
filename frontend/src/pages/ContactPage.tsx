import { Link } from 'react-router-dom'
import RaymondsRiskLogo from '../components/common/RaymondsRiskLogo'

function ContactPage() {
  const email = 'Raymond.jj.park@proton.me'

  return (
    <div className="min-h-screen bg-theme-bg">
      {/* 헤더 */}
      <header className="sticky top-0 z-50 bg-theme-bg/80 backdrop-blur-lg border-b border-theme-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="inline-block">
            <RaymondsRiskLogo size="md" variant="compact" />
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/about"
              className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
            >
              서비스 소개
            </Link>
            <Link
              to="/login"
              className="px-4 py-2 bg-[#5E6AD2] hover:bg-[#4F5ABF] text-white text-sm font-medium rounded-lg transition-colors"
            >
              로그인
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4">
            문의하기
          </h1>
          <p className="text-lg text-text-secondary">
            RaymondsRisk 서비스에 대한 문의사항이 있으시면 연락주세요.
          </p>
        </div>

        {/* Contact Card */}
        <div className="max-w-md mx-auto">
          <div className="bg-theme-card border border-theme-border rounded-2xl p-8 text-center">
            {/* Email Icon */}
            <div className="w-16 h-16 mx-auto mb-6 bg-accent-primary/10 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>

            <h2 className="text-xl font-semibold text-text-primary mb-2">
              이메일 문의
            </h2>
            <p className="text-text-secondary mb-6">
              아래 이메일로 문의해 주시면 빠르게 답변 드리겠습니다.
            </p>

            {/* Email Link */}
            <a
              href={`mailto:${email}`}
              className="inline-flex items-center gap-2 px-6 py-3 bg-accent-primary hover:bg-accent-primary/90 text-white font-medium rounded-xl transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {email}
            </a>

            {/* Copy Button */}
            <button
              onClick={() => {
                navigator.clipboard.writeText(email)
                alert('이메일 주소가 복사되었습니다.')
              }}
              className="block w-full mt-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              이메일 주소 복사하기
            </button>
          </div>

          {/* Additional Info */}
          <div className="mt-8 text-center text-sm text-text-muted">
            <p className="mb-2">
              서비스 이용 문의, 제휴 제안, 기술 지원 등
            </p>
            <p>
              일반적으로 24시간 이내 답변드립니다.
            </p>
          </div>
        </div>

        {/* Back Link */}
        <div className="mt-12 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            홈으로 돌아가기
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-theme-border py-8 mt-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center text-sm text-text-muted">
          <p>2025 RaymondsRisk. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default ContactPage
