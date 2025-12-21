# Remove /analytics from Navigation

## Overview

Remove the `/analytics` menu item from the sidebar navigation, keeping `/bank-transactions-analytics` as the primary analytics page. This is a UI navigation change only - the actual `/analytics` page will remain accessible via direct URL.

## Workflow Type

**simple** - Single file modification with minimal risk.

## Task Scope

### Files to Modify
- `frontend/src/components/AppLayout.tsx` - Remove analytics menu item (lines 57-61)

### Change Details
Delete the menu item object for `/analytics` from the `menuItems` array:
```tsx
// REMOVE THIS:
{
  key: '/analytics',
  icon: <LineChartOutlined />,
  label: 'Аналитика',
},
```

The `/bank-transactions-analytics` item remains intact as the comprehensive analytics solution.

### Constraints
- Do NOT delete the `/bank-transactions-analytics` menu item
- Do NOT delete the actual `/analytics` page file
- Navigation-only change

## Success Criteria

- [ ] Sidebar menu no longer shows "Аналитика" item
- [ ] "Аналитика транзакций" menu item still works and navigates correctly
- [ ] No console errors after the change
- [ ] App builds successfully (`npm run build`)

## Notes

- The actual `/analytics` page file is NOT deleted - only hidden from navigation
- Users can still access `/analytics` via direct URL if needed
