import React, { useMemo } from 'react'
import { Card, Empty, Spin, Tooltip } from 'antd'
import type { ActivityHeatmapPoint } from '../../types/bankTransaction'

interface Props {
  data: ActivityHeatmapPoint[]
  loading?: boolean
}

const dayLabels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

const ActivityHeatmapChart: React.FC<Props> = ({ data, loading }) => {
  const matrix = useMemo(() => {
    const base: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
    const totals: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
    data.forEach((point) => {
      base[point.day_of_week][point.hour] = point.transaction_count
      totals[point.day_of_week][point.hour] = Number(point.total_amount)
    })
    const maxCount = Math.max(...base.flat(), 0)
    const maxAmount = Math.max(...totals.flat(), 0)
    return { counts: base, totals, maxCount, maxAmount }
  }, [data])

  if (loading) {
    return (
      <Card title="Тепловая карта активности">
        <div style={{ minHeight: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title="Тепловая карта активности">
        <Empty description="Недостаточно данных для анализа" />
      </Card>
    )
  }

  const getColor = (value: number) => {
    if (matrix.maxCount === 0) return '#f5f5f5'
    const intensity = value / matrix.maxCount
    const hue = 200 - intensity * 140
    return `hsl(${hue}, 70%, ${70 - intensity * 30}%)`
  }

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(val)

  return (
    <Card title="Тепловая карта активности (дни недели × часы)">
      <div style={{ display: 'grid', gridTemplateColumns: '60px repeat(24, 1fr)', gap: 4 }}>
        <div />
        {Array.from({ length: 24 }).map((_, hour) => (
          <div key={`hour-${hour}`} style={{ textAlign: 'center', fontSize: 11, color: '#8c8c8c' }}>
            {hour}
          </div>
        ))}
        {dayLabels.map((label, dayIdx) => (
          <React.Fragment key={label}>
            <div style={{ textAlign: 'right', paddingRight: 8, fontWeight: 500 }}>{label}</div>
            {matrix.counts[dayIdx].map((value, hourIdx) => (
              <Tooltip
                key={`${dayIdx}-${hourIdx}`}
                title={
                  value === 0
                    ? 'Нет транзакций'
                    : `${value} транз. • ${formatCurrency(matrix.totals[dayIdx][hourIdx])}`
                }
              >
                <div
                  style={{
                    height: 28,
                    borderRadius: 4,
                    background: value === 0 ? '#f5f5f5' : getColor(value),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 11,
                    color: value === 0 ? '#bfbfbf' : '#262626',
                  }}
                >
                  {value > 0 ? value : ''}
                </div>
              </Tooltip>
            ))}
          </React.Fragment>
        ))}
      </div>
    </Card>
  )
}

export default ActivityHeatmapChart
