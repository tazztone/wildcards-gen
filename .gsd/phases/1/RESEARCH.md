---
phase: 1
level: 1
researched_at: 2026-01-30
---

# Phase 1 Research: GUI Layout Refactoring

## Questions Investigated
1. **How to implement a "Toolbar" layout in Gradio?**
   - We can place `gr.Button` and `gr.Checkbox` inside a `gr.Row()` at the top of the right column.
   - Using `scale` and `min_width` in `gr.Column` within the row can help align them.
2. **How to make the Analysis panel compact?**
   - Wrapping the entire Analysis `gr.Group` in a `gr.Accordion(open=False)` will hide the complexity until needed.
   - We can move the "Stale Warning" to be visible even if the accordion is closed, OR place it inside the header of the accordion (though Gradio header support is limited). Better: keep it as a small indicator outside or just inside.
3. **Where to place the "Generation Completed" status for best visibility?**
   - Placing it immediately below the "Generate" toolbar but above the "Analysis" accordion ensures it's the first thing users see after clicking.

## Findings

### Layout Optimizations
- **Action Toolbar**: Moving the primary action group (Generate, Fast Preview, Download) to the top right creates a clear "Configuration (Left) -> Action (Top Right) -> Output (Bottom Right)" workflow.
- **Visual Hierarchy**: The YAML preview is the secondary output; the primary output is the success status and the file. Swapping their vertical priority (Status above Preview) improves scanability.

### Gradio Components
- `gr.Accordion`: Perfect for the Analysis section.
- `gr.File`: Can be made more compact by limiting height (already done with `height=100`).

## Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Toolbar Placement** | Top of Right Column | Follows IDE patterns; reduces scrolling. |
| **Analysis Layout** | Accordion (Default Closed) | Reduces "noisy" stats that aren't always needed. |
| **Status Placement** | Between Toolbar and Preview | Immediate feedback loop. |

## Patterns to Follow
- **ID-based Styling**: Keep using `elem_id` and `elem_classes` for custom CSS.
- **Modular Events**: Ensure `on_dataset_change` and other event handlers are updated if component references change (though they shouldn't since we are just moving them).

## Risks
- **Mobile/Narrow Screens**: Moving components to a multi-column toolbar might wrap poorly on narrow screens.
- **Mitigation**: Use `min_width=0` or `scale` carefully; Gradio handles wrapping reasonably well.

## Ready for Planning
- [x] Questions answered
- [x] Approach selected
- [x] Dependencies identified
