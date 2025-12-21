/**
 * Хук для получения доступных годов для выбора в интерфейсе
 */
import { useMemo } from 'react'

export const useAvailableYears = () => {
  const years = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return Array.from({ length: 5 }, (_, i) => currentYear - 2 + i)
  }, [])

  return { years }
}

/**
 * Получить опции для Select компонента Ant Design
 */
export const useAvailableYearsOptions = () => {
  const { years } = useAvailableYears()

  const options = years.map((year) => ({
    value: year,
    label: year.toString(),
  }))

  return { options, isLoading: false, years }
}
