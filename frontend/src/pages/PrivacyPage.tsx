import { useState, useEffect } from 'react'
import apiClient from '../api/client'

function PrivacyPage() {
  const [content, setContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadPrivacy = async () => {
      try {
        const response = await apiClient.get('/api/admin/public/settings/privacy')
        setContent(response.data.value || '')
      } catch (err) {
        console.error('Failed to load privacy:', err)
        setContent('개인정보처리방침을 불러오는데 실패했습니다.')
      } finally {
        setIsLoading(false)
      }
    }
    loadPrivacy()
  }, [])

  // 간단한 Markdown 렌더링 (h1, h2, p, ul, li 지원)
  const renderMarkdown = (text: string) => {
    return text.split('\n').map((line, index) => {
      if (line.startsWith('# ')) {
        return <h1 key={index} className="text-2xl font-bold text-text-primary mt-6 mb-4">{line.slice(2)}</h1>
      }
      if (line.startsWith('## ')) {
        return <h2 key={index} className="text-xl font-semibold text-text-primary mt-5 mb-3">{line.slice(3)}</h2>
      }
      if (line.startsWith('### ')) {
        return <h3 key={index} className="text-lg font-medium text-text-primary mt-4 mb-2">{line.slice(4)}</h3>
      }
      if (line.startsWith('- ')) {
        return <li key={index} className="text-text-secondary ml-4 mb-1">{line.slice(2)}</li>
      }
      if (line.startsWith('---')) {
        return <hr key={index} className="my-6 border-theme-border" />
      }
      if (line.trim() === '') {
        return <br key={index} />
      }
      return <p key={index} className="text-text-secondary mb-2">{line}</p>
    })
  }

  return (
    <div className="bg-theme-bg">
      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-theme-card border border-theme-border rounded-2xl p-8">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-4 border-accent-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="prose prose-invert max-w-none">
              {renderMarkdown(content)}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default PrivacyPage
