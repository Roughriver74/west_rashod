# Russian Language Support for AutoClaude

## Overview

Добавить поддержку русского языка для ответов и описаний задач Claude в проекте. Создание файла `CLAUDE.md` в корне проекта с инструкциями для Claude Code для автоматического использования русского языка.

## Workflow Type

**simple** - Single file creation with immediate effect on Claude's behavior.

## Task Scope

### Files to Create
- `CLAUDE.md` - Project-level instructions file for Claude Code

### Change Details
Создать файл `CLAUDE.md` в корне проекта с инструкциями для Claude:
- Отвечать на русском языке
- Формировать описания задач на русском языке
- Использовать русский язык во всех коммуникациях с пользователем

This file is automatically loaded by Claude Code when working in this project directory.

### Implementation Content

```markdown
# Project Instructions

## Язык / Language
**Всегда отвечай на русском языке.**

Все ответы, описания задач, комментарии к коммитам и коммуникации с пользователем должны быть на русском языке.

## Правила
- Используй русский язык по умолчанию
- Код и названия переменных остаются на английском языке
- Комментарии к коду могут быть на русском языке
- Сообщения коммитов на русском языке
```

## Success Criteria

- [ ] Файл CLAUDE.md создан в корне проекта
- [ ] Claude отвечает на русском языке в этом проекте
- [ ] Описания задач формируются на русском языке

## Notes

- Файл CLAUDE.md является стандартным способом настройки поведения Claude Code для проекта
- Настройки сохраняются автоматически и будут работать во всех будущих сессиях
