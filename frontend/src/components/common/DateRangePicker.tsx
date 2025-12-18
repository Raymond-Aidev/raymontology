import { useCallback, useState } from 'react'

// 사업보고서 연도 범위 (report_years)
export interface DateRange {
  startDate: Date | null
  endDate: Date | null
  reportYears?: number[]  // 사업보고서 연도 목록 (예: [2025], [2023, 2024, 2025])
}

interface DateRangePickerProps {
  onChange: (range: DateRange) => void
  className?: string
  defaultPreset?: '1y' | '3y'  // 기본 선택 프리셋
}

// 프리셋 타입
type PresetType = '1y' | '3y'

// 현재 연도 (2025년 기준)
const CURRENT_YEAR = new Date().getFullYear()

const presets: { key: PresetType; label: string; description: string; getRange: () => DateRange }[] = [
  {
    key: '1y',
    label: '최근 1년',
    description: `${CURRENT_YEAR}년 사업보고서`,
    getRange: () => ({
      startDate: new Date(CURRENT_YEAR, 0, 1),
      endDate: new Date(),
      reportYears: [CURRENT_YEAR],  // 2025년 사업보고서만
    }),
  },
  {
    key: '3y',
    label: '최근 3년',
    description: `${CURRENT_YEAR - 3}~${CURRENT_YEAR}년 사업보고서`,
    getRange: () => ({
      startDate: new Date(CURRENT_YEAR - 3, 0, 1),
      endDate: new Date(),
      reportYears: [CURRENT_YEAR - 3, CURRENT_YEAR - 2, CURRENT_YEAR - 1, CURRENT_YEAR],  // 2022, 2023, 2024, 2025년
    }),
  },
]

export default function DateRangePicker({
  onChange,
  className = '',
  defaultPreset = '1y',  // 기본값: 최근 1년
}: DateRangePickerProps) {
  // 기본값으로 '1y' (최근 1년) 선택
  const [activePreset, setActivePreset] = useState<PresetType>(defaultPreset)

  const handlePresetClick = useCallback(
    (preset: typeof presets[0]) => {
      setActivePreset(preset.key)
      onChange(preset.getRange())
    },
    [onChange]
  )

  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {/* 프리셋 버튼 */}
      <div className="flex gap-1">
        {presets.map((preset) => (
          <button
            key={preset.key}
            onClick={() => handlePresetClick(preset)}
            title={preset.description}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              activePreset === preset.key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400 hover:text-blue-600'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  )
}
