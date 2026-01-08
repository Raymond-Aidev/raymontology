import { useEffect, useRef, useState, useCallback } from 'react'
import { colors } from '../../constants/colors'

interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
  /** 최소 높이 (vh 단위) */
  minHeight?: number
  /** 최대 높이 (vh 단위) */
  maxHeight?: number
}

export default function BottomSheet({
  isOpen,
  onClose,
  children,
  title,
  minHeight = 35,
  maxHeight = 80,
}: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [startY, setStartY] = useState(0)
  const [currentHeight, setCurrentHeight] = useState(minHeight)
  const [translateY, setTranslateY] = useState(0)

  // 열릴 때 초기 높이 설정
  useEffect(() => {
    if (isOpen) {
      setCurrentHeight(minHeight)
      setTranslateY(0)
    }
  }, [isOpen, minHeight])

  // 드래그 시작
  const handleDragStart = useCallback((clientY: number) => {
    setIsDragging(true)
    setStartY(clientY)
  }, [])

  // 드래그 중
  const handleDragMove = useCallback((clientY: number) => {
    if (!isDragging) return

    const deltaY = startY - clientY
    const newTranslateY = Math.max(
      -(maxHeight - minHeight),
      Math.min(100, -deltaY / window.innerHeight * 100)
    )
    setTranslateY(newTranslateY)
  }, [isDragging, startY, maxHeight, minHeight])

  // 드래그 종료
  const handleDragEnd = useCallback(() => {
    if (!isDragging) return
    setIsDragging(false)

    // 아래로 많이 드래그하면 닫기
    if (translateY > 20) {
      onClose()
      return
    }

    // 위로 드래그하면 확장
    if (translateY < -10) {
      setCurrentHeight(maxHeight)
    } else {
      setCurrentHeight(minHeight)
    }
    setTranslateY(0)
  }, [isDragging, translateY, maxHeight, minHeight, onClose])

  // 터치 이벤트
  const handleTouchStart = (e: React.TouchEvent) => {
    handleDragStart(e.touches[0].clientY)
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    handleDragMove(e.touches[0].clientY)
  }

  const handleTouchEnd = () => {
    handleDragEnd()
  }

  // 마우스 이벤트 (테스트용)
  const handleMouseDown = (e: React.MouseEvent) => {
    handleDragStart(e.clientY)
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      handleDragMove(e.clientY)
    }

    const handleMouseUp = () => {
      handleDragEnd()
    }

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, handleDragMove, handleDragEnd])

  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const effectiveHeight = currentHeight - translateY

  return (
    <>
      {/* 백드롭 */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          zIndex: 40,
        }}
        onClick={onClose}
      />

      {/* 바텀시트 */}
      <div
        ref={sheetRef}
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          backgroundColor: colors.white,
          borderTopLeftRadius: '16px',
          borderTopRightRadius: '16px',
          boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.15)',
          height: `${effectiveHeight}vh`,
          maxHeight: `${maxHeight}vh`,
          transition: isDragging ? 'none' : 'height 0.3s ease-out',
        }}
      >
        {/* 드래그 핸들 */}
        <div
          style={{
            padding: '12px 0',
            cursor: 'grab',
            touchAction: 'none',
          }}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onMouseDown={handleMouseDown}
        >
          <div style={{
            width: '36px',
            height: '4px',
            backgroundColor: colors.gray100,
            borderRadius: '2px',
            margin: '0 auto',
          }} />
        </div>

        {/* 헤더 */}
        {title && (
          <div style={{
            padding: '0 16px 12px',
            borderBottom: `1px solid ${colors.gray100}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h3 style={{
              fontSize: '16px',
              fontWeight: '600',
              color: colors.gray900,
              margin: 0,
            }}>
              {title}
            </h3>
            <button
              onClick={onClose}
              style={{
                padding: '4px 8px',
                fontSize: '20px',
                color: colors.gray500,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              ×
            </button>
          </div>
        )}

        {/* 컨텐츠 */}
        <div style={{
          overflowY: 'auto',
          height: `calc(${effectiveHeight}vh - ${title ? '80px' : '40px'})`,
        }}>
          {children}
        </div>
      </div>
    </>
  )
}
