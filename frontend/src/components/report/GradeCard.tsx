import type { InvestmentGrade } from '../../types/report'
import { gradeConfig } from '../../types/report'

interface GradeCardProps {
  grade: InvestmentGrade
}

export default function GradeCard({ grade }: GradeCardProps) {
  const config = gradeConfig[grade]

  return (
    <div className="flex flex-col items-center p-6 bg-theme-surface rounded-xl border border-theme-border">
      <span className="text-sm text-text-secondary mb-2">관계형리스크등급</span>
      <span
        className="text-5xl font-bold"
        style={{ color: config.color }}
      >
        {grade}
      </span>
      <span
        className="mt-2 px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: `${config.color}20`, color: config.color }}
      >
        {config.label}
      </span>
    </div>
  )
}
