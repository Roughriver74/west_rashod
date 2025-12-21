import type { TablePaginationConfig } from 'antd'

/**
 * Get responsive card styles based on screen size
 */
export function getResponsiveCardStyle(isMobile: boolean, isSmallScreen: boolean) {
  if (isMobile) {
    return {
      padding: '12px',
      marginBottom: '8px',
    }
  }

  if (isSmallScreen) {
    return {
      padding: '16px',
      marginBottom: '12px',
    }
  }

  return {
    padding: '20px',
    marginBottom: '16px',
  }
}

/**
 * Get responsive pagination configuration
 */
export function getResponsivePagination(
  isMobile: boolean,
  isSmallScreen: boolean
): TablePaginationConfig {
  if (isMobile) {
    return {
      pageSize: 10,
      showSizeChanger: false,
      showQuickJumper: false,
      simple: true,
      size: 'small',
    }
  }

  if (isSmallScreen) {
    return {
      pageSize: 20,
      showSizeChanger: true,
      showQuickJumper: false,
      size: 'small',
      pageSizeOptions: ['10', '20', '50'],
    }
  }

  return {
    pageSize: 50,
    showSizeChanger: true,
    showQuickJumper: true,
    size: 'default',
    pageSizeOptions: ['10', '20', '50', '100'],
  }
}

/**
 * Get responsive column width
 */
export function getResponsiveColumnWidth(
  baseWidth: number,
  isMobile: boolean,
  isSmallScreen: boolean
): number {
  if (isMobile) {
    return Math.min(baseWidth, 120)
  }

  if (isSmallScreen) {
    return Math.min(baseWidth, 150)
  }

  return baseWidth
}
