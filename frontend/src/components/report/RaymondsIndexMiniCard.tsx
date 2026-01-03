/**
 * RaymondsIndex 미니 카드 - 대시보드용 (다크 테마)
 *
 * 관계형 리스크 대시보드에 표시되는 간단한 종합점수/등급 카드
 */
import type { RaymondsIndexGrade } from '../../types/raymondsIndex'
import { getGradeColor } from '../../types/raymondsIndex'

interface RaymondsIndexMiniCardProps {
  score: number
  grade: RaymondsIndexGrade
}

export default function RaymondsIndexMiniCard({ score, grade }: RaymondsIndexMiniCardProps) {
  const gradeColor = getGradeColor(grade)

  // 등급별 라벨
  const getGradeLabel = (grade: RaymondsIndexGrade): string => {
    const labels: Record<RaymondsIndexGrade, string> = {
      'A+': '최우수',
      'A': '우수',
      'B': '양호',
      'C': '보통',
      'D': '주의',
    }
    return labels[grade] || ''
  }

  return (
    <div className="flex flex-col items-center p-6 bg-dark-surface rounded-xl border border-dark-border">
      <span className="text-sm text-text-secondary mb-2">RaymondsIndex</span>
      <div className="flex items-center gap-3 mb-2">
        <span
          className="text-4xl font-bold"
          style={{ color: gradeColor }}
        >
          {score.toFixed(0)}
        </span>
        <span className="text-xl text-text-muted">점</span>
      </div>
      <span
        className="text-3xl font-bold"
        style={{ color: gradeColor }}
      >
        {grade}
      </span>
      <span
        className="mt-2 px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: `${gradeColor}20`, color: gradeColor }}
      >
        {getGradeLabel(grade)}
      </span>
    </div>
  )
}
