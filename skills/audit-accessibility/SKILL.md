---
name: audit-accessibility
description: Audit web applications for accessibility compliance with WCAG guidelines. Identifies barriers for users with disabilities and provides fixes to improve inclusivity.
triggers:
- /audit-accessibility
- /a11y-audit
- /wcag-check
---

# Audit Accessibility

Ensure web applications are accessible to users with disabilities.

## Process

1. **Automated checks**: Scan for common accessibility violations
2. **Manual review**: Assess keyboard navigation, screen reader compatibility
3. **Report issues**: Catalog violations with WCAG references
4. **Implement fixes**: Provide code changes to resolve issues

## WCAG Compliance Areas

### Perceivable
- Images have alt text
- Videos have captions
- Color is not the only indicator
- Sufficient color contrast
- Text can be resized

### Operable
- All functionality keyboard accessible
- Focus indicators visible
- No keyboard traps
- Skip navigation links
- Sufficient time limits

### Understandable
- Language declared
- Consistent navigation
- Clear error messages
- Form labels and instructions

### Robust
- Valid HTML markup
- ARIA used correctly
- Compatible with assistive technologies

## Common Issues

### Missing or Poor Alt Text
```html
<!-- Bad -->
<img src="chart.png">

<!-- Good -->
<img src="chart.png" alt="Sales increased 25% from Q1 to Q2">
```

### Insufficient Color Contrast
- Text must have 4.5:1 contrast ratio (normal text)
- Large text needs 3:1 ratio

### Missing Form Labels
```html
<!-- Bad -->
<input type="email" placeholder="Email">

<!-- Good -->
<label for="email">Email</label>
<input type="email" id="email">
```

### Non-Keyboard Accessible
- onClick without onKeyDown
- Custom controls without keyboard support
- Missing tabIndex for interactive elements

## Output Format

For each issue:
1. **Severity**: Critical, Serious, Moderate, Minor
2. **WCAG Criterion**: e.g., 1.1.1 Non-text Content
3. **Location**: Component/element affected
4. **Description**: What the issue is
5. **Fix**: Code change to resolve the issue
