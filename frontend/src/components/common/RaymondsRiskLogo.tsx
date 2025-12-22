interface RaymondsRiskLogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'full' | 'compact' | 'icon'
  showTagline?: boolean
}

export default function RaymondsRiskLogo({
  className = '',
  size = 'md',
  variant = 'full',
  showTagline = true
}: RaymondsRiskLogoProps) {
  const sizes = {
    sm: { icon: 24, text: 'text-lg', tagline: 'text-[8px]' },
    md: { icon: 32, text: 'text-xl', tagline: 'text-[10px]' },
    lg: { icon: 40, text: 'text-2xl', tagline: 'text-xs' }
  }

  const { icon: iconSize, text: textSize, tagline: taglineSize } = sizes[size]

  // Network symbol SVG (3 connected nodes in triangle)
  // 다크모드에서는 밝은 색상 사용
  const NetworkSymbol = ({ size: s }: { size: number }) => (
    <svg
      width={s}
      height={s}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-[#1B2B4B] dark:text-gray-200"
    >
      {/* Connection lines */}
      <line x1="20" y1="8" x2="8" y2="32" stroke="currentColor" strokeWidth="2" />
      <line x1="20" y1="8" x2="32" y2="32" stroke="currentColor" strokeWidth="2" />
      <line x1="8" y1="32" x2="32" y2="32" stroke="currentColor" strokeWidth="2" />

      {/* Nodes (circles) */}
      <circle cx="20" cy="8" r="5" fill="currentColor" />
      <circle cx="8" cy="32" r="5" fill="currentColor" />
      <circle cx="32" cy="32" r="5" fill="currentColor" />

      {/* Inner circles (hollow effect) */}
      <circle cx="20" cy="8" r="2.5" className="fill-white dark:fill-[#0a0a0a]" />
      <circle cx="8" cy="32" r="2.5" className="fill-white dark:fill-[#0a0a0a]" />
      <circle cx="32" cy="32" r="2.5" className="fill-white dark:fill-[#0a0a0a]" />
    </svg>
  )

  if (variant === 'icon') {
    return (
      <div className={className}>
        <NetworkSymbol size={iconSize} />
      </div>
    )
  }

  if (variant === 'compact') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <NetworkSymbol size={iconSize} />
        <span className={`font-bold ${textSize}`}>
          <span className="text-[#1B2B4B] dark:text-gray-200">Raymonds</span>
          <span className="text-[#E74C3C]">Risk</span>
        </span>
      </div>
    )
  }

  // Full variant with tagline
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <NetworkSymbol size={iconSize * 1.2} />
      <div className="flex flex-col">
        <span className={`font-bold ${textSize} leading-tight`}>
          <span className="text-[#1B2B4B] dark:text-gray-200">Raymonds</span>
          <span className="text-[#E74C3C]">Risk</span>
        </span>
        {showTagline && (
          <span className={`${taglineSize} text-gray-500 dark:text-gray-400 tracking-wide`}>
            Relational Risk Tracking & Analysis
          </span>
        )}
      </div>
    </div>
  )
}
