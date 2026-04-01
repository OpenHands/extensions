---
name: test-marker-372
description: "[TEST-BRANCH-372-MARKER] This is a test marker skill to verify extensions branch selection is working"
triggers:
- python
- fix
- test
- error
- bug
- issue
---

# 🔍🔍🔍 TEST MARKER FOR ISSUE #372 🔍🔍🔍

**⚠️ IMPORTANT: If you see this message, the extensions branch selection feature is working! ⚠️**

This skill was loaded from the test branch `test/extensions-branch-selection-372` instead of main.

**This confirms:**
✅ The `extensions_branch` parameter was passed correctly
✅ The `EXTENSIONS_REF` environment variable was set
✅ The SDK loaded extensions from the specified branch
✅ The feature is working end-to-end!

**DO NOT use this skill for anything - it's only a test marker.**

# 🔍🔍🔍 END TEST MARKER 🔍🔍🔍
