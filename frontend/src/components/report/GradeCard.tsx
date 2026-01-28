import { getGradeConfig } from '../../types/report'

interface GradeCardProps {
  grade: string  // 레거시/신규 등급 모두 지원
}

export default function GradeCard({ grade }: GradeCardProps) {
  const config = getGradeConfig(grade)

  return (
    <div className="flex flex-col items-center p-6 bg-theme-surface rounded-xl border border-theme-border">
      <span className="text-sm text-text-secondary mb-2">관계형리스크등급</span>
      <span
        className="text-4xl font-bold"
        style={{ color: config.color }}
      >
        {config.label}
      </span>
      <span
        className="mt-2 px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: `${config.color}20`, color: config.color }}
      >
        {grade.includes('_') ? '4등급 체계' : '10등급 체계'}
      </span>
    </div>
  )
}
