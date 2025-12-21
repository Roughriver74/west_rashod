# Specification: Integrate Automatic Sync Settings into 1C Sync Page

## Overview

The frontend currently has two separate sync-related pages: `Sync1CPage` for manual synchronization controls and `SyncSettingsPage` for automatic sync configuration. Users on the main sync page (`/sync-1c`) have no visibility into auto-sync settings or status, making it difficult to understand if automatic synchronization is configured and when it will run. This feature will integrate auto-sync settings visibility and controls into the main 1C Sync page, providing a unified sync management experience.

## Workflow Type

**Type**: feature

**Rationale**: This is a new UI enhancement that adds auto-sync settings integration to an existing page. It requires frontend changes to display auto-sync status and settings, with the backend already having all necessary endpoints in place.

## Task Scope

### Services Involved
- **frontend** (primary) - Add auto-sync status card and settings integration to Sync1CPage
- **backend** (reference only) - Existing sync-settings API endpoints will be consumed (no changes needed)

### This Task Will:
- [ ] Add an auto-sync status/settings card to `Sync1CPage.tsx`
- [ ] Display current auto-sync configuration (enabled/disabled, interval/time, last sync status)
- [ ] Add a link to full sync settings page for detailed configuration
- [ ] Show real-time sync interval information and next scheduled sync time
- [ ] Provide quick toggle to enable/disable auto-sync from main sync page

### Out of Scope:
- Backend API changes (already complete)
- Full sync settings editing (available on dedicated SyncSettingsPage)
- Google Sheets integration (not part of this project)
- Celery/scheduler backend modifications

## Service Context

### Frontend

**Tech Stack:**
- Language: TypeScript
- Framework: React with Vite
- UI Library: Ant Design (antd) ^5.14.0
- State Management: @tanstack/react-query ^5.17.0
- HTTP Client: Axios ^1.6.5
- Date Library: dayjs

**Entry Point:** `src/App.tsx`

**How to Run:**
```bash
cd frontend && npm run dev
```

**Port:** 3000

**Key directories:**
- `src/pages/` - Page components
- `src/api/` - API client functions
- `src/components/` - Shared components
- `src/contexts/` - React contexts

### Backend

**Tech Stack:**
- Language: Python 3.13
- Framework: FastAPI
- ORM: SQLAlchemy
- Task Queue: Celery with Redis
- Database: PostgreSQL

**How to Run:**
```bash
cd backend && uvicorn app.main:app --reload --port 8005
```

**Port:** 8005 (API via `VITE_API_URL`)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `frontend/src/pages/Sync1CPage.tsx` | frontend | Add auto-sync status card component showing current settings and last sync info |
| `frontend/src/api/syncSettings.ts` | frontend | May need additional utility functions for computed values (next sync time) |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `frontend/src/pages/SyncSettingsPage.tsx` | Auto-sync form structure, status display patterns, API integration |
| `frontend/src/api/syncSettings.ts` | Sync settings API types and functions |
| `frontend/src/pages/Sync1CPage.tsx` | Existing page layout, card structure, mutation patterns |

## Patterns to Follow

### Card Layout Pattern

From `Sync1CPage.tsx`:

```tsx
<Card
  title={
    <Space>
      <SettingOutlined />
      <span>Автоматическая синхронизация</span>
    </Space>
  }
>
  <Space direction="vertical" style={{ width: '100%' }}>
    {/* Content */}
  </Space>
</Card>
```

**Key Points:**
- Cards use Space with icon and title
- Vertical spacing within card content
- Full width for internal components

### Status Display Pattern

From `SyncSettingsPage.tsx`:

```tsx
const getStatusTag = (status: string | null) => {
  if (!status) return null;

  switch (status) {
    case 'SUCCESS':
      return <Tag icon={<CheckCircleOutlined />} color="success">Успешно</Tag>;
    case 'FAILED':
      return <Tag icon={<CloseCircleOutlined />} color="error">Ошибка</Tag>;
    case 'IN_PROGRESS':
      return <Tag icon={<LoadingOutlined />} color="processing">Выполняется</Tag>;
    default:
      return <Tag>{status}</Tag>;
  }
};
```

**Key Points:**
- Use Tag component for status indicators
- Include appropriate icons
- Use semantic colors (success, error, processing)

### API Query Pattern

From existing pages:

```tsx
import { useQuery, useMutation } from '@tanstack/react-query';

const { data: settings, isLoading, refetch } = useQuery({
  queryKey: ['syncSettings'],
  queryFn: syncSettingsApi.getSettings,
});

const updateMutation = useMutation({
  mutationFn: syncSettingsApi.updateSettings,
  onSuccess: () => {
    refetch();
    message.success('Настройки обновлены');
  },
});
```

**Key Points:**
- Use @tanstack/react-query v5 patterns
- Include queryKey for caching
- Handle success/error states
- Refetch after mutations

## Requirements

### Functional Requirements

1. **Auto-Sync Status Display**
   - Description: Show current auto-sync configuration status on Sync1CPage
   - Acceptance: Users can see whether auto-sync is enabled/disabled, current interval or scheduled time, and last sync status without navigating to settings page

2. **Quick Enable/Disable Toggle**
   - Description: Allow users to quickly enable/disable auto-sync from main sync page
   - Acceptance: Switch toggle updates auto_sync_enabled setting via API and reflects change immediately

3. **Last Sync Information**
   - Description: Display last sync timestamp and status
   - Acceptance: Shows last_sync_started_at, last_sync_completed_at, and last_sync_status with appropriate formatting

4. **Next Sync Indicator**
   - Description: Calculate and display when next automatic sync will occur
   - Acceptance: Shows estimated next sync time based on interval or scheduled time settings

5. **Link to Full Settings**
   - Description: Provide navigation to detailed sync settings page
   - Acceptance: Button/link navigates to `/sync-settings` page

### Edge Cases

1. **No Settings Configured** - Display informative message with link to configure settings
2. **Auto-Sync Disabled** - Show disabled state clearly with option to enable
3. **Sync In Progress** - Show loading/progress state with appropriate indicator
4. **API Error** - Handle gracefully with error message and retry option
5. **Permission Denied** - Handle 403 errors for non-admin/manager users

## Implementation Notes

### DO
- Follow the existing card layout pattern in `Sync1CPage.tsx`
- Reuse the `syncSettingsApi` functions from `api/syncSettings.ts`
- Use @tanstack/react-query for data fetching (same pattern as existing code)
- Use Ant Design components (Card, Switch, Tag, Space, Button)
- Use dayjs for date formatting (already imported)
- Keep Russian language for all UI text (matching existing pages)
- Calculate next sync time client-side based on settings

### DON'T
- Create a new API endpoint (use existing `/sync-settings` endpoint)
- Duplicate the full settings form (link to SyncSettingsPage for details)
- Add new dependencies
- Change the existing SyncSettingsPage functionality
- Make backend changes (API is complete)

## Development Environment

### Start Services

```bash
# Start backend
cd backend && uvicorn app.main:app --reload --port 8005

# Start frontend
cd frontend && npm run dev

# Start Redis (required for Celery)
docker-compose up -d redis

# Start Celery worker (for background tasks)
cd backend && celery -A app.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
cd backend && celery -A app.celery_app beat --loglevel=info
```

### Service URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8005
- API Docs: http://localhost:8005/docs

### Required Environment Variables
- `VITE_API_URL`: Frontend API base URL (default: http://localhost:8005/api/v1)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string for Celery

## Success Criteria

The task is complete when:

1. [ ] Auto-sync status card is visible on Sync1CPage
2. [ ] Current auto-sync settings are displayed (enabled status, interval/time)
3. [ ] Last sync information is shown with proper formatting
4. [ ] Quick enable/disable toggle works correctly
5. [ ] Link to full settings page navigates correctly
6. [ ] No console errors in browser
7. [ ] Existing Sync1CPage functionality still works
8. [ ] UI matches existing design patterns (Ant Design, Russian text)

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| AutoSyncCard renders | `frontend/src/pages/Sync1CPage.test.tsx` | Component renders without errors |
| Status tag displays correctly | `frontend/src/pages/Sync1CPage.test.tsx` | Correct tag color/icon for each status |
| Next sync calculation | `frontend/src/utils/syncUtils.test.ts` | Correct calculation of next sync time |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| Load sync settings | frontend ↔ backend | GET /sync-settings returns data and displays correctly |
| Toggle auto-sync | frontend ↔ backend | PUT /sync-settings updates auto_sync_enabled |
| Error handling | frontend ↔ backend | 403/500 errors display appropriate messages |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| View auto-sync status | 1. Login 2. Navigate to /sync-1c 3. View auto-sync card | Auto-sync status is displayed |
| Toggle auto-sync | 1. Navigate to /sync-1c 2. Toggle switch 3. Verify change | Setting updates and persists |
| Navigate to settings | 1. Navigate to /sync-1c 2. Click settings link | Navigates to /sync-settings |

### Browser Verification (if frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Sync1CPage with AutoSync card | `http://localhost:3000/sync-1c` | Auto-sync card renders, toggle works, link works |
| Settings link navigation | `http://localhost:3000/sync-settings` | Navigation from sync-1c works |

### Database Verification (if applicable)
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Sync settings exist | `SELECT * FROM sync_settings WHERE id=1` | Settings row exists with expected values |
| Toggle persists | Toggle auto_sync, verify DB | auto_sync_enabled column updates |

### QA Sign-off Requirements
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Browser verification complete
- [ ] No regressions in existing Sync1CPage functionality
- [ ] No regressions in existing SyncSettingsPage functionality
- [ ] Code follows established patterns (Ant Design, React Query v5)
- [ ] No security vulnerabilities introduced
- [ ] UI text is in Russian matching existing pages
