import { useEffect, useRef, useState, useCallback } from 'react'

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
  minHeight = 30,
  maxHeight = 85,
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

  // 마우스 이벤트 (데스크톱 테스트용)
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
        className="fixed inset-0 bg-black/50 z-40 md:hidden"
        onClick={onClose}
      />

      {/* 바텀시트 */}
      <div
        ref={sheetRef}
        className={`fixed bottom-0 left-0 right-0 z-50 bg-dark-card border-t border-dark-border rounded-t-2xl md:hidden
                   ${isDragging ? '' : 'transition-all duration-300 ease-out'}`}
        style={{
          height: `${effectiveHeight}vh`,
          maxHeight: `${maxHeight}vh`,
        }}
      >
        {/* 드래그 핸들 */}
        <div
          className="py-3 cursor-grab active:cursor-grabbing touch-none"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onMouseDown={handleMouseDown}
        >
          <div className="w-10 h-1 bg-dark-border rounded-full mx-auto" />
        </div>

        {/* 헤더 */}
        {title && (
          <div className="px-4 pb-3 border-b border-dark-border flex items-center justify-between">
            <h3 className="font-semibold text-text-primary">{title}</h3>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-dark-hover text-text-muted"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* 컨텐츠 */}
        <div className="overflow-y-auto" style={{ height: `calc(${effectiveHeight}vh - ${title ? '80px' : '40px'})` }}>
          {children}
        </div>
      </div>
    </>
  )
}
