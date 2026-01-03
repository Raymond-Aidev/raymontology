import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { getRiskLevel, riskLevelConfig } from '../../types/report'

interface RiskGaugeProps {
  score: number
  size?: number
  label?: string
}

export default function RiskGauge({ score, size = 200, label = '종합 리스크' }: RiskGaugeProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const riskLevel = getRiskLevel(score)
  const config = riskLevelConfig[riskLevel]

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = size
    const radius = Math.min(width, size * 0.7 * 2) / 2 - 20
    const cx = width / 2
    const cy = size * 0.7 - 10  // 반원 위치 (아래 점수/라벨 공간 확보)

    // 배경 호 (다크 테마용 색상)
    const arcBackground = d3.arc()
      .innerRadius(radius - 20)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(Math.PI / 2)

    svg.append('path')
      .attr('d', arcBackground as never)
      .attr('transform', `translate(${cx}, ${cy})`)
      .attr('fill', '#262626')  // dark-border 색상

    // 값 호 (색상)
    const scoreAngle = -Math.PI / 2 + (score / 100) * Math.PI
    const arcValue = d3.arc()
      .innerRadius(radius - 20)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(scoreAngle)

    svg.append('path')
      .attr('d', arcValue as never)
      .attr('transform', `translate(${cx}, ${cy})`)
      .attr('fill', config.color)

    // 눈금
    const ticks = [0, 25, 50, 75, 100]
    ticks.forEach(tick => {
      const angle = -Math.PI / 2 + (tick / 100) * Math.PI
      const x1 = cx + (radius + 5) * Math.cos(angle)
      const y1 = cy + (radius + 5) * Math.sin(angle)
      const x2 = cx + (radius + 12) * Math.cos(angle)
      const y2 = cy + (radius + 12) * Math.sin(angle)

      svg.append('line')
        .attr('x1', x1)
        .attr('y1', y1)
        .attr('x2', x2)
        .attr('y2', y2)
        .attr('stroke', '#52525b')  // text-muted 색상
        .attr('stroke-width', 1)

      const textX = cx + (radius + 25) * Math.cos(angle)
      const textY = cy + (radius + 25) * Math.sin(angle)

      svg.append('text')
        .attr('x', textX)
        .attr('y', textY)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('fill', '#a1a1aa')  // text-secondary 색상
        .attr('font-size', '10px')
        .text(tick)
    })

    // 중앙 점수 - 반원 차트 아래로 위치 조정
    svg.append('text')
      .attr('x', cx)
      .attr('y', cy + 30)
      .attr('text-anchor', 'middle')
      .attr('fill', config.color)
      .attr('font-size', '36px')
      .attr('font-weight', 'bold')
      .text(score)

    // 라벨 - 점수 바로 아래
    svg.append('text')
      .attr('x', cx)
      .attr('y', cy + 55)
      .attr('text-anchor', 'middle')
      .attr('fill', '#a1a1aa')  // text-secondary 색상
      .attr('font-size', '12px')
      .text(label)

  }, [score, size, config.color, label])

  return (
    <div className="flex flex-col items-center">
      <svg ref={svgRef} width={size} height={size * 1.0} />
      <div
        className="mt-2 px-3 py-1 rounded-full text-sm font-medium"
        style={{ backgroundColor: `${config.color}20`, color: config.color }}
      >
        {config.label}
      </div>
    </div>
  )
}
