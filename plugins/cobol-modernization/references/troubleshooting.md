# Troubleshooting Guide

## COBOL doesn't compile after mainframe removal

- Check FILE STATUS is declared for all files
- Ensure CLOSE statements in all code paths
- Verify paragraph names match PERFORM statements

## Java tests fail

- Compare output byte-by-byte with golden files
- Check decimal precision (use BigDecimal)
- Verify character encoding matches COBOL

## Missing functionality

- Check the migration mapping for coverage gaps
- Review `mainframe_dependency_removal_plan.md` for skipped items
