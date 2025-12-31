import { colors } from '../constants/colors'

interface ListItemProps {
  title: string
  description: string
  isLast?: boolean
  onClick?: () => void
}

/**
 * 리스트 아이템 컴포넌트
 * 제목과 설명을 가진 클릭 가능한 리스트 아이템
 */
export function ListItem({
  title,
  description,
  isLast = false,
  onClick
}: ListItemProps) {
  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      role="button"
      tabIndex={0}
      aria-label={`${title}: ${description}`}
      style={{
        padding: '16px 4px',
        borderBottom: isLast ? 'none' : `1px solid ${colors.gray100}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        cursor: onClick ? 'pointer' : 'default',
        minHeight: '72px',
      }}
    >
      <div>
        <div style={{
          fontSize: '16px',
          fontWeight: '500',
          color: colors.gray900,
          marginBottom: '2px'
        }}>
          {title}
        </div>
        <div style={{
          fontSize: '14px',
          color: colors.gray500,
        }}>
          {description}
        </div>
      </div>
      {onClick && (
        <div
          style={{
            color: colors.gray500,
            fontSize: '18px',
            marginLeft: '12px'
          }}
          aria-hidden="true"
        >
          ›
        </div>
      )}
    </div>
  )
}

export default ListItem
