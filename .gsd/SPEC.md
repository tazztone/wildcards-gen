# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
Harden the core extraction engine and streamline the UI for a focused, "one-shot" generation experience where settings are clear and execution is reliable.

## Goals
- **Fix & Verify**: Resolve the `TypeError` caused by missing argument handling in dataset modules.
- **Interface Hardening**: Implement comprehensive signature/integration tests to catch parameter mismatches early.
- **UI Streamlining**: Reclaim vertical space by removing the obsolete "Analysis" report and history panels.
- **Layout Refinement**: Rearrange the "CV Datasets" tab into a cleaner, more intuitive 2-column layout.
- **Educational UX**: Add/improve info tooltips for all Smart Tuning settings.

## Success Criteria
- [ ] Dataset generation completes successfully for ImageNet, Tencent, and Open Images with various Smart Tuning settings.
- [ ] New test suite `tests/test_signatures.py` validates that all dataset handlers accept the full range of parameters passed from the GUI.
- [ ] "Analysis" and "Run History" sections are removed from the GUI.
- [ ] CV Datasets tab displays a balanced 2-column configuration.
- [ ] All Smart Tuning sliders and checkboxes have descriptive `info` text.
