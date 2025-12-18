import { useState, useEffect, useCallback } from 'react'
import apiClient from '../../api/client'

export type ApiStatus = 'connected' | 'disconnected' | 'checking' | 'unknown'

interface ApiStatusIndicatorProps {
  className?: string
  showText?: boolean
  autoCheck?: boolean
  checkInterval?: number // ms
}

// API 상태 체크 함수
export async function checkApiConnection(): Promise<boolean> {
  try {
    // 간단한 health check 엔드포인트 호출
    const response = await apiClient.get('/api/health', { timeout: 5000 })
    return response.status === 200
  } catch {
    // health 엔드포인트 없으면 companies 엔드포인트 시도
    try {
      const response = await apiClient.get('/api/companies', {
        params: { limit: 1 },
        timeout: 5000,
      })
      return response.status === 200
    } catch {
      return false
    }
  }
}

export function ApiStatusIndicator({
  className = '',
  showText = true,
  autoCheck = true,
  checkInterval = 30000, // 30초
}: ApiStatusIndicatorProps) {
  const [status, setStatus] = useState<ApiStatus>('unknown')
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const checkStatus = useCallback(async () => {
    setStatus('checking')
    const isConnected = await checkApiConnection()
    setStatus(isConnected ? 'connected' : 'disconnected')
    setLastChecked(new Date())
  }, [])

  // 초기 체크 및 주기적 체크
  useEffect(() => {
    if (autoCheck) {
      checkStatus()
      const interval = setInterval(checkStatus, checkInterval)
      return () => clearInterval(interval)
    }
  }, [autoCheck, checkInterval, checkStatus])

  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      text: 'text-green-600',
      label: 'API 연결됨',
      icon: (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      ),
    },
    disconnected: {
      color: 'bg-red-500',
      text: 'text-red-600',
      label: 'API 연결 실패',
      icon: (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      ),
    },
    checking: {
      color: 'bg-yellow-500',
      text: 'text-yellow-600',
      label: '확인 중...',
      icon: (
        <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      ),
    },
    unknown: {
      color: 'bg-gray-400',
      text: 'text-gray-500',
      label: '상태 불명',
      icon: (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
        </svg>
      ),
    },
  }

  const config = statusConfig[status]

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        onClick={checkStatus}
        className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${config.text} hover:bg-gray-100 transition-colors`}
        title={lastChecked ? `마지막 확인: ${lastChecked.toLocaleTimeString()}` : '클릭하여 상태 확인'}
      >
        {/* 상태 도트 */}
        <span className={`w-2 h-2 rounded-full ${config.color} ${status === 'checking' ? 'animate-pulse' : ''}`} />
        {/* 아이콘 */}
        {config.icon}
        {/* 텍스트 */}
        {showText && (
          <span className="text-xs font-medium">{config.label}</span>
        )}
      </button>
    </div>
  )
}

// 간단한 도트 인디케이터 (헤더용)
export function ApiStatusDot({ className = '' }: { className?: string }) {
  const [isConnected, setIsConnected] = useState<boolean | null>(null)

  useEffect(() => {
    checkApiConnection().then(setIsConnected)
    const interval = setInterval(() => {
      checkApiConnection().then(setIsConnected)
    }, 60000) // 1분마다 체크
    return () => clearInterval(interval)
  }, [])

  if (isConnected === null) {
    return (
      <span
        className={`w-2 h-2 rounded-full bg-gray-400 animate-pulse ${className}`}
        title="API 상태 확인 중..."
      />
    )
  }

  return (
    <span
      className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} ${className}`}
      title={isConnected ? 'API 연결됨' : 'API 연결 실패'}
    />
  )
}

export default ApiStatusIndicator
