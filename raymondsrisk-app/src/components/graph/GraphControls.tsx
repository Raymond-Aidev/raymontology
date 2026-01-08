import type { NodeType } from '../../types/graph'
import { nodeTypeColors } from '../../types/graph'
import { colors } from '../../constants/colors'

interface GraphControlsProps {
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  visibleNodeTypes?: Set<NodeType>
  onToggleNodeType?: (type: NodeType) => void
  nodeCounts?: Record<NodeType, number>
}

export default function GraphControls({
  onZoomIn,
  onZoomOut,
  onReset,
  visibleNodeTypes,
  onToggleNodeType,
  nodeCounts,
}: GraphControlsProps) {
  const nodeTypes: NodeType[] = ['company', 'officer', 'subscriber', 'cb', 'shareholder', 'affiliate']

  return (
    <div style={{
      position: 'absolute',
      top: '12px',
      left: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      zIndex: 10,
    }}>
      {/* 줌 컨트롤 */}
      <div style={{
        backgroundColor: colors.white,
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        overflow: 'hidden',
      }}>
        <button
          onClick={onZoomIn}
          style={{
            width: '36px',
            height: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            borderBottom: `1px solid ${colors.gray100}`,
            backgroundColor: colors.white,
            color: colors.gray600,
            fontSize: '18px',
            cursor: 'pointer',
          }}
          aria-label="확대"
        >
          +
        </button>
        <button
          onClick={onZoomOut}
          style={{
            width: '36px',
            height: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            borderBottom: `1px solid ${colors.gray100}`,
            backgroundColor: colors.white,
            color: colors.gray600,
            fontSize: '18px',
            cursor: 'pointer',
          }}
          aria-label="축소"
        >
          −
        </button>
        <button
          onClick={onReset}
          style={{
            width: '36px',
            height: '36px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            backgroundColor: colors.white,
            color: colors.gray600,
            fontSize: '14px',
            cursor: 'pointer',
          }}
          aria-label="초기화"
        >
          ↺
        </button>
      </div>

      {/* 범례 */}
      <div style={{
        backgroundColor: colors.white,
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: '10px',
      }}>
        <div style={{
          fontSize: '11px',
          fontWeight: '600',
          color: colors.gray500,
          marginBottom: '8px',
          textTransform: 'uppercase',
        }}>
          {onToggleNodeType ? '필터' : '범례'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {nodeTypes.map(type => {
            const color = nodeTypeColors[type]
            const isVisible = !visibleNodeTypes || visibleNodeTypes.has(type)
            const count = nodeCounts?.[type] || 0

            if (count === 0 && !onToggleNodeType) return null

            if (onToggleNodeType) {
              return (
                <button
                  key={type}
                  onClick={() => onToggleNodeType(type)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 6px',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: isVisible ? colors.gray50 : colors.gray100,
                    opacity: isVisible ? 1 : 0.5,
                    cursor: 'pointer',
                    width: '100%',
                  }}
                >
                  <span style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: isVisible ? color.fill : colors.gray500,
                  }} />
                  <span style={{
                    flex: 1,
                    fontSize: '11px',
                    color: isVisible ? colors.gray900 : colors.gray500,
                    textAlign: 'left',
                  }}>
                    {color.label}
                  </span>
                  <span style={{
                    fontSize: '11px',
                    color: colors.gray500,
                    fontFamily: 'monospace',
                  }}>
                    {count}
                  </span>
                </button>
              )
            }

            return (
              <div key={type} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '2px 0',
              }}>
                <span style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: color.fill,
                }} />
                <span style={{
                  fontSize: '11px',
                  color: colors.gray600,
                }}>
                  {color.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
