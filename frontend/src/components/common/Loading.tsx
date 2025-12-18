interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  fullScreen?: boolean
  overlay?: boolean
}

const sizeClasses = {
  sm: 'w-5 h-5 border-2',
  md: 'w-10 h-10 border-4',
  lg: 'w-16 h-16 border-4',
}

const textSizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
}

export function Loading({
  size = 'md',
  text,
  fullScreen = false,
  overlay = false,
}: LoadingProps) {
  const spinner = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`
          ${sizeClasses[size]}
          border-blue-600 border-t-transparent
          rounded-full animate-spin
        `}
      />
      {text && (
        <p className={`text-gray-500 ${textSizeClasses[size]}`}>{text}</p>
      )}
    </div>
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white z-50">
        {spinner}
      </div>
    )
  }

  if (overlay) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
        {spinner}
      </div>
    )
  }

  return spinner
}

// 페이지 로딩용 프리셋
export function PageLoading({ text = '로딩 중...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loading size="lg" text={text} />
    </div>
  )
}

// 인라인 로딩용 프리셋
export function InlineLoading({ text }: { text?: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      {text && <span className="text-sm text-gray-500">{text}</span>}
    </span>
  )
}

// 버튼 내부 로딩용
export function ButtonLoading() {
  return (
    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
  )
}

export default Loading
