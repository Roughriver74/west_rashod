# Add Delete Button for Auto Patterns

## Overview

Add a "Удалить" (Delete) button to the auto-detected patterns tables (counterparty and operation patterns) to completely remove unwanted patterns from the list. Since patterns are auto-computed from historical transaction data and cannot be truly deleted, we implement "soft delete" via blocking rules with special markers.

## Workflow Type

**simple** - Single file modification with straightforward implementation.

## Task Scope

### Files to Modify
- `frontend/src/pages/CategorizationRulesPage.tsx` - Add delete button and handler for patterns

### Change Details
Currently the patterns tables only have:
- "+ Правило" (Create rule from pattern)
- "Отключить" (Disable pattern - creates a blocking rule)

The user wants to completely remove unwanted patterns. Since patterns are auto-computed from historical data and cannot be truly deleted, we need to:

1. Add a "Удалить" button to both `counterpartyColumns` and `operationColumns`
2. When clicked, create a blocking rule (similar to "Отключить") but with a special note marking it as "deleted"
3. Filter out patterns that have matching "deleted" blocking rules from the display

### Implementation Approach
- Add `handleDeletePattern` function that creates a blocking rule with `notes` containing "🗑️ Удалённый паттерн"
- Add filter logic to exclude patterns that have matching deletion rules from `manualRules`
- Add "Удалить" button with `DeleteOutlined` icon and red styling

## Success Criteria

- [ ] "Удалить" button appears in patterns tables next to "Отключить"
- [ ] Clicking delete removes the pattern from the visible list
- [ ] A blocking rule with deletion marker is created in "Ручные правила"
- [ ] No console errors

## Notes

- Patterns are computed from historical transaction data, not stored as records
- True deletion would require deleting underlying transactions (not desired)
- Using blocking rules with special markers is the cleanest approach
