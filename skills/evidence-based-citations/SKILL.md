---
name: evidence-based-citations
description: Back factual claims and field values with official, verifiable sources. Use when the user asks to fill fields, answer questions, or make claims that must be supported by an exact quote and an official link.
triggers:
- evidence-based
- cite source
- cite sources
- official source
- official link
- official links
- official docs
- official documentation
- verifiable source
---

The user wants every field value or factual claim you produce in the current response to be backed by an official, verifiable source. Apply this skill to the response that triggered it; do not assume it stays active for the rest of the conversation unless the user clearly asks for it to.

## Output format

For each field or claim, respond with exactly these four labeled lines:

- **Field**: the field name (or a short description of the claim)
- **Value**: the value you are assigning (or the claim itself)
- **Quote**: the exact verbatim text from the source that supports the value
- **Source**: the official URL where the quote can be found

When there are multiple fields, repeat the block once per field. Keep blocks separated by a blank line.

## Source selection rules

1. Prefer primary sources, in this order:
   - Official product / project documentation
   - Standards documents (RFCs, W3C specs, ISO standards)
   - Official API references
   - Source code in the project's own repository
2. Accept secondary sources (blog posts, Stack Overflow, forum threads, news articles, third-party tutorials) only as a last resort, and clearly label them as such in **Source**.
3. The **Quote** field must contain text that actually appears at the **Source** URL. Do not paraphrase inside the quote, and do not stitch together text from different parts of the page without making the cut explicit (e.g. with ` … `).
4. If you cannot find an official source for a value, say so explicitly:
   - **Source**: `No official source found.`
   Then either omit the value, mark it as unverified, or ask the user how to proceed. Never invent a quote or URL.

## When to fetch

- If you have a browser / fetch tool available, retrieve the source page and copy the quote directly from it before responding.
- If you do not have a fetch tool, always respond with `Source: No official source found.` rather than citing URLs from memory. LLMs cannot reliably verify URL accuracy or quote fidelity without actually fetching the page, even when a URL feels familiar.

## Example

> User: What HTTP status code indicates a successful request, per the HTTP semantics RFC?

- **Field**: HTTP status code for a successful request (per RFC 9110)
- **Value**: 200 (OK)
- **Quote**: "The 200 (OK) status code indicates that the request has succeeded."
- **Source**: https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.1

## What this skill is not

- It is not a general "be careful with facts" reminder. Apply the strict four-field format only when the user has invoked this skill or is clearly asking for evidence-backed answers.
- It does not change how you write code, edit files, or run tools. It only governs how you report values and claims back to the user.
