import { memo } from 'react'
import { nodeTypeColors } from '../../types/graph'
import type { NodeType } from '../../types/graph'

interface GraphControlsProps {
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  visibleNodeTypes?: Set<NodeType>
  onToggleNodeType?: (type: NodeType) => void
  nodeCounts?: Record<NodeType, number>
}

export default memo(function GraphControls({
  onZoomIn,
  onZoomOut,
  onReset,
  visibleNodeTypes,
  onToggleNodeType,
  nodeCounts,
}: GraphControlsProps) {
  const nodeTypes: NodeType[] = ['company', 'officer', 'subscriber', 'cb', 'shareholder', 'affiliate']

  return (
    <div className="absolute top-4 left-4 flex-col gap-2 hidden md:flex">
      {/* 줌 컨트롤 */}
      <div className="bg-theme-card rounded-lg border border-theme-border overflow-hidden">
        <button
          onClick={onZoomIn}
          className="w-10 h-10 flex items-center justify-center hover:bg-blue-500/10 transition-colors border-b border-theme-border text-text-muted hover:text-blue-400"
          title="확대"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>
        <button
          onClick={onZoomOut}
          className="w-10 h-10 flex items-center justify-center hover:bg-blue-500/10 transition-colors border-b border-theme-border text-text-muted hover:text-blue-400"
          title="축소"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        </button>
        <button
          onClick={onReset}
          className="w-10 h-10 flex items-center justify-center hover:bg-amber-500/10 transition-colors text-text-muted hover:text-amber-400"
          title="초기화"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* 범례 + 필터 */}
      <div className="bg-theme-card rounded-lg border border-theme-border p-3 mt-2">
        <p className="text-xs font-semibold text-text-muted mb-2 uppercase tracking-wide">
          {onToggleNodeType ? '필터' : '범례'}
        </p>
        <div className="space-y-1.5">
          {nodeTypes.map(type => {
            const color = nodeTypeColors[type]
            const isVisible = !visibleNodeTypes || visibleNodeTypes.has(type)
            const count = nodeCounts?.[type] || 0

            if (onToggleNodeType) {
              // 필터링 가능한 버튼
              return (
                <button
                  key={type}
                  onClick={() => onToggleNodeType(type)}
                  className={`flex items-center gap-2 w-full px-2 py-1.5 rounded transition-all
                             ${isVisible
                               ? 'bg-theme-surface hover:bg-theme-hover'
                               : 'bg-theme-bg opacity-50'}`}
                >
                  <span
                    className={`w-3 h-3 rounded-full transition-transform ${isVisible ? 'scale-100' : 'scale-75'}`}
                    style={{ backgroundColor: isVisible ? color.fill : '#52525b' }}
                  />
                  <span className={`text-xs flex-1 text-left ${isVisible ? 'text-text-secondary' : 'text-text-muted'}`}>
                    {color.label}
                  </span>
                  <span className={`text-xs font-mono ${isVisible ? 'text-text-muted' : 'text-text-muted/50'}`}>
                    {count}
                  </span>
                  {isVisible ? (
                    <svg className="w-3 h-3 text-accent-success" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-3 h-3 text-text-muted" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              )
            }

            // 범례 (필터링 불가)
            return (
              <div key={type} className="flex items-center gap-2 px-2 py-1">
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color.fill }}
                />
                <span className="text-xs text-text-secondary">{color.label}</span>
              </div>
            )
          })}
        </div>

        {/* 전체 선택/해제 버튼 */}
        {onToggleNodeType && visibleNodeTypes && (
          <div className="mt-3 pt-2 border-t border-theme-border flex gap-2">
            <button
              onClick={() => {
                nodeTypes.forEach(type => {
                  if (!visibleNodeTypes.has(type)) {
                    onToggleNodeType(type)
                  }
                })
              }}
              className="flex-1 text-xs py-1.5 px-2 bg-green-500/10 text-green-400 rounded hover:bg-green-500/20 border border-green-500/20 hover:border-green-500/40 transition-colors"
            >
              전체 선택
            </button>
            <button
              onClick={() => {
                nodeTypes.forEach(type => {
                  if (visibleNodeTypes.has(type) && visibleNodeTypes.size > 1) {
                    onToggleNodeType(type)
                  }
                })
              }}
              className="flex-1 text-xs py-1.5 px-2 bg-blue-500/10 text-blue-400 rounded hover:bg-blue-500/20 border border-blue-500/20 hover:border-blue-500/40 transition-colors"
            >
              회사만
            </button>
          </div>
        )}
      </div>
    </div>
  )
})
