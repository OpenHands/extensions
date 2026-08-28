---
name: internationalization
description: Implement internationalization (i18n) and localization (l10n) support including string extraction, translation management, locale handling, and RTL support.
triggers:
- /i18n
- /internationalize
- /add-translations
---

# Internationalization

Add multi-language support and localization capabilities to applications.

## Process

1. **Audit current state**: Identify hardcoded strings and locale-dependent code
2. **Set up i18n framework**: Configure appropriate library for the stack
3. **Extract strings**: Move hardcoded text to translation files
4. **Implement locale handling**: Date, number, and currency formatting
5. **Add RTL support**: Right-to-left language layout support

## Implementation Steps

### String Extraction
- Find all user-facing strings in code
- Extract to translation files (JSON, YAML, PO)
- Add placeholders for dynamic content
- Handle pluralization rules

### i18n Libraries by Stack
- React: react-i18next, react-intl
- Vue: vue-i18n
- Angular: @angular/localize
- Node.js: i18next
- Python: gettext, Babel

### Locale-Dependent Formatting
```javascript
// Numbers
new Intl.NumberFormat('de-DE').format(1234.56) // "1.234,56"

// Currency
new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' })

// Dates
new Intl.DateTimeFormat('fr-FR').format(date) // "31/12/2024"
```

### RTL Support
- CSS logical properties (margin-inline-start vs margin-left)
- Direction-aware icons
- Bidirectional text handling
- Layout mirroring

## Best Practices

- Never concatenate translated strings
- Use ICU message format for complex cases
- Include context for translators
- Test with pseudo-localization
- Consider text expansion (German is ~30% longer than English)

## Output Format

Provide:
1. **Audit results**: Hardcoded strings found
2. **Setup guide**: Framework configuration
3. **Code changes**: String extraction and implementation
4. **Translation files**: Structure for translation keys
