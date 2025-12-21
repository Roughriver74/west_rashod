import React, { useMemo, useCallback } from 'react'
import {
	Table,
	Card,
	Space,
	Typography,
	Row,
	Col,
	TableProps,
	Skeleton,
	Empty,
} from 'antd'
import type { ColumnsType, ColumnType } from 'antd/es/table'
import { useIsMobile, useIsSmallScreen } from '@/hooks/useMediaQuery'
import {
	getResponsiveCardStyle,
	getResponsivePagination,
} from '@/utils/responsive'

const { Text } = Typography

export interface ResponsiveTableProps<T = any> extends TableProps<T> {
	/**
	 * Layout mode on mobile devices
	 * - 'card': Display each row as a card (best for 5-10 columns)
	 * - 'compact': Show table with reduced columns (best for 3-5 important columns)
	 * - 'scroll': Keep table but allow horizontal scroll (default)
	 */
	mobileLayout?: 'card' | 'compact' | 'scroll'

	/**
	 * Columns to show in compact mode (by key)
	 * If not provided, shows first 3 columns
	 */
	compactColumns?: string[]

	/**
	 * Custom card renderer for mobile
	 */
	renderMobileCard?: (record: T, index: number) => React.ReactNode

	/**
	 * Number of skeleton cards/rows to show while loading (mobile only)
	 * Default: 3
	 */
	skeletonCount?: number
}

/**
 * ResponsiveTable - Responsive wrapper around Ant Design Table
 *
 * Automatically switches layout based on screen size:
 * - Desktop: Full table
 * - Mobile: Card layout, Compact table, or Scrollable table
 *
 * @example
 * ```tsx
 * <ResponsiveTable
 *   columns={columns}
 *   dataSource={data}
 *   mobileLayout="card"
 *   sticky={{ offsetHeader: isMobile ? 48 : 64 }}
 * />
 * ```
 */
export function ResponsiveTable<T extends Record<string, any>>({
	mobileLayout = 'scroll',
	compactColumns,
	renderMobileCard,
	columns = [],
	dataSource = [],
	scroll,
	sticky,
	skeletonCount = 3,
	loading,
	...restProps
}: ResponsiveTableProps<T>) {
	const isMobile = useIsMobile()
	const isSmallScreen = useIsSmallScreen()

	// Skeleton loading for mobile card layout
	const skeletonCards = useMemo(() => {
		if (!isMobile || mobileLayout !== 'card' || !loading) return null

		const cardStyle = getResponsiveCardStyle(isMobile, isSmallScreen)

		return (
			<Space direction='vertical' style={{ width: '100%' }} size='middle'>
				{Array.from({ length: skeletonCount }).map((_, index) => (
					<Card
						key={`skeleton-${index}`}
						size='small'
						style={{
							width: '100%',
							marginBottom: cardStyle.marginBottom,
						}}
						styles={{ body: { padding: cardStyle.padding } }}
					>
						<Skeleton active paragraph={{ rows: 3 }} />
					</Card>
				))}
			</Space>
		)
	}, [isMobile, isSmallScreen, mobileLayout, loading, skeletonCount])

	// Default card renderer - MUST be declared before cardLayout useMemo
	// useCallback to avoid unnecessary re-renders
	const defaultCardRenderer = useCallback(
		(record: T, _index: number) => {
			return (
				<Space direction='vertical' style={{ width: '100%', overflow: 'hidden' }} size='small'>
					{(columns as ColumnsType<T>).map((col: ColumnType<T>) => {
						if (!col.dataIndex && !col.render) return null

						const key = Array.isArray(col.dataIndex)
							? col.dataIndex.join('.')
							: String(col.dataIndex || col.key)

						let value: React.ReactNode
						if (col.render) {
							value = col.render(record[key], record, _index) as React.ReactNode
						} else {
							value = record[key]
						}

						// Для колонок с действиями - рендерим по-особому
						const isActionsColumn = key === 'actions' || col.key === 'actions'

						return (
							<Row key={key} gutter={[8, 8]} style={{ width: '100%' }}>
								<Col span={isActionsColumn ? 24 : 10}>
									<Text strong style={{ wordBreak: 'break-word', fontSize: isActionsColumn ? 13 : 14 }}>
										{col.title as string}:
									</Text>
								</Col>
								<Col span={isActionsColumn ? 24 : 14} style={{ overflow: 'hidden' }}>
									<div style={{ 
										wordBreak: 'break-word', 
										overflowWrap: 'break-word',
										overflow: 'hidden',
										// Для кнопок - делаем их wrap
										...(isActionsColumn ? { display: 'flex', flexWrap: 'wrap', gap: 4 } : {})
									}}>
										{value}
									</div>
								</Col>
							</Row>
						)
					})}
				</Space>
			)
		},
		[columns]
	)

	// Card Layout for Mobile
	const cardLayout = useMemo(() => {
		if (!isMobile || mobileLayout !== 'card') return null

		const renderCard = renderMobileCard || defaultCardRenderer
		const cardStyle = getResponsiveCardStyle(isMobile, isSmallScreen)

		if (dataSource.length === 0) {
			return <Empty description='Нет данных' />
		}

		return (
			<Space direction='vertical' style={{ width: '100%', overflow: 'hidden' }} size='middle'>
				{dataSource.map((record, index) => (
					<Card
						key={record.key || record.id || index}
						size='small'
						hoverable
						style={{
							width: '100%',
							marginBottom: cardStyle.marginBottom,
							overflow: 'hidden',
							maxWidth: '100%',
						}}
						styles={{ 
							body: {
								padding: cardStyle.padding,
								overflow: 'hidden',
								maxWidth: '100%',
							}
						}}
					>
						{renderCard(record, index)}
					</Card>
				))}
			</Space>
		)
	}, [
		isMobile,
		isSmallScreen,
		mobileLayout,
		dataSource,
		renderMobileCard,
		defaultCardRenderer,
	])

	// Compact Layout (show only important columns)
	const compactTableColumns = useMemo(() => {
		if (!isSmallScreen || mobileLayout !== 'compact') return columns

		if (compactColumns && compactColumns.length > 0) {
			return (columns as ColumnsType<T>).filter(col => {
				const key = col.key || ('dataIndex' in col ? col.dataIndex : undefined)
				return compactColumns.includes(String(key))
			})
		}

		// Show first 3 columns by default
		return (columns as ColumnsType<T>).slice(0, 3)
	}, [isSmallScreen, mobileLayout, columns, compactColumns])

	// Adjust scroll and sticky for mobile
	const responsiveScroll = useMemo(() => {
		if (!scroll) return undefined

		if (isMobile) {
			return {
				...scroll,
				x: mobileLayout === 'scroll' ? scroll.x : undefined,
				y: 400, // Reduce height on mobile
			}
		}

		return scroll
	}, [isMobile, mobileLayout, scroll])

	const responsiveSticky = useMemo(() => {
		if (!sticky) return undefined

		if (isMobile) {
			if (typeof sticky === 'object') {
				return {
					...sticky,
					offsetHeader: 48, // Mobile header height
				}
			}
			return sticky
		}

		return sticky
	}, [isMobile, sticky])

	// Calculate pagination config BEFORE any conditional returns (React Hooks rule)
	const responsivePaginationConfig = useMemo(() => {
		if (restProps.pagination === false) return false

		const defaultPagination = getResponsivePagination(isMobile, isSmallScreen)

		return {
			...defaultPagination,
			...restProps.pagination,
			pageSize:
				(restProps.pagination as any)?.pageSize || defaultPagination.pageSize,
		}
	}, [isMobile, isSmallScreen, restProps.pagination])

	// Render card layout on mobile
	if (isMobile && mobileLayout === 'card') {
		if (loading && skeletonCards) {
			return <>{skeletonCards}</>
		}
		return <>{cardLayout}</>
	}

	// Render compact or scroll table

	return (
		<Table<T>
			{...restProps}
			loading={loading}
			columns={mobileLayout === 'compact' ? compactTableColumns : columns}
			dataSource={dataSource}
			scroll={responsiveScroll}
			sticky={responsiveSticky}
			pagination={responsivePaginationConfig}
			locale={{
				emptyText: <Empty description='Нет данных' />,
			}}
		/>
	)
}

export default ResponsiveTable
