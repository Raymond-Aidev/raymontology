import { useState } from 'react'
import { colors } from '../constants/colors'

interface DebugPanelProps {
  logs: string[]
  extraInfo?: Record<string, string | number | boolean | null | undefined>
}

/**
 * 디버그 패널 컴포넌트
 * 개발/테스트 시 환경정보와 로그를 확인할 수 있는 패널
 */
export function DebugPanel({ logs, extraInfo }: DebugPanelProps) {
  const [showDebug, setShowDebug] = useState(false)

  return (
    <div style={{ marginTop: '20px' }}>
      {/* 토글 버튼 */}
      <div style={{ textAlign: 'center' }}>
        <button
          onClick={() => setShowDebug(!showDebug)}
          style={{
            padding: '8px 16px',
            fontSize: '12px',
            backgroundColor: colors.gray100,
            border: 'none',
            borderRadius: '8px',
            color: colors.gray600,
            cursor: 'pointer',
          }}
        >
          {showDebug ? '디버그 숨기기' : '디버그 보기'}
        </button>
      </div>

      {/* 디버그 로그 패널 */}
      {showDebug && (
        <div style={{
          marginTop: '12px',
          padding: '12px',
          backgroundColor: '#1a1a2e',
          borderRadius: '8px',
          maxHeight: '400px',
          overflowY: 'auto',
          textAlign: 'left',
        }}>
          <div style={{
            fontFamily: 'monospace',
            fontSize: '11px',
            color: '#00ff00',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            {/* 환경 정보 */}
            <div style={{ marginBottom: '8px', color: '#ffff00' }}>
              === 환경 정보 ===
            </div>
            <div>DEV: {String(import.meta.env.DEV)}</div>
            <div>MODE: {import.meta.env.MODE}</div>
            <div>PROD: {String(import.meta.env.PROD)}</div>

            {/* 추가 정보 */}
            {extraInfo && Object.entries(extraInfo).map(([key, value]) => (
              <div key={key}>{key}: {String(value ?? 'null')}</div>
            ))}

            {/* window 객체 */}
            <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
              === window 객체 ===
            </div>
            <div>__CONSTANT_HANDLER_MAP: {typeof window !== 'undefined' ? JSON.stringify((window as unknown as Record<string, unknown>).__CONSTANT_HANDLER_MAP) : 'undefined'}</div>
            <div>ReactNativeWebView: {typeof window !== 'undefined' && (window as unknown as Record<string, unknown>).ReactNativeWebView ? 'exists' : 'null'}</div>
            <div>__GRANITE_NATIVE_EMITTER: {typeof window !== 'undefined' && (window as unknown as Record<string, unknown>).__GRANITE_NATIVE_EMITTER ? 'exists' : 'null'}</div>

            {/* 디버그 로그 */}
            <div style={{ marginTop: '8px', marginBottom: '8px', color: '#ffff00' }}>
              === 디버그 로그 ({logs.length}개) ===
            </div>
            {logs.length === 0 ? (
              <div style={{ color: '#888' }}>(로그 없음)</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default DebugPanel
