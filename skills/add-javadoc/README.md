# add-javadoc

Add comprehensive JavaDoc documentation to Java classes and methods. Use when documenting Java code, adding API documentation, or improving code documentation.

## Triggers

This skill is activated by the following keywords:

- `javadoc`
- `java documentation`
- `document java`

## Details

This skill guides the agent to add standard JavaDoc comments to all public classes and methods in Java source files.

### Class-Level Documentation

For each public class, the agent will:
- Add a class-level JavaDoc block describing the purpose and responsibility of the class
- Include an `@author` tag if appropriate

### Method-Level Documentation

For each public method, the agent will:
- Add a method-level JavaDoc block describing what the method does
- Include `@param` tags for all parameters with clear descriptions
- Include a `@return` tag describing the return value
- Include `@throws` tags for any checked exceptions

### Style Guidelines

- First sentence should be a concise summary
- Use HTML tags sparingly (prefer plain text)
- Document preconditions and postconditions when relevant
- Include code examples with `{@code ...}` for complex methods

## Example

See [references/example.md](references/example.md) for a before/after example showing undocumented Java code transformed with proper JavaDoc comments.
