# Workspace UI Design System

This folder contains the reusable CSS foundation for the planned Workspace UI.

Files:

- `workspace-ui-base.css`: shared component and layout layer
- `workspace-theme-moss.css`: moss console theme tokens
- `workspace-theme-slate.css`: slate lab theme tokens
- `workspace-theme-ink.css`: ink signal theme tokens
- `workspace-theme.css`: compatibility wrapper that loads the default moss theme
- `index.html`: design-system preview page

Current purpose:

- establish one reusable visual language for workspace-console prototypes
- prevent each HTML review artifact from inventing its own palette and component rules
- compare multiple color directions on top of the same component system
- support the `Workspace UI Readiness` milestone with a reusable CSS base before a framework-specific component library exists

Current default direction:

- `Moss Console` is the selected default theme direction for ongoing workspace-console prototype work
- the shared base now also carries reusable stage-3 primitives for inference boards, clarification cards, contract previews, tags, and JSON inspection blocks
- the shared base now also carries stage-4 confirmation primitives for summary rows, decision bands, execution-mapping cards, and confirmation payload actions
- the shared base now also carries stage-5 remediation primitives for blocked-draft next-step routing, named path options, and explicit request-or-fallback actions
- the shared base now also carries stage-6 single-flow primitives for converged draft journeys, thread-plus-system-work presentation, and cross-stage progression cues
- the shared base now also carries stage-7 adapter primitives for operator-action clusters, event logs, and parallel state projections around one draft object
- the shared base now also carries stage-8 queue-monitor primitives for run tables, lifecycle timelines, and operator status stacks
- the shared base now also carries stage-9 evidence-browser primitives for artifact cards, replay-linked evidence lists, and structured review metadata
- the shared base now also carries stage-10 evidence-query primitives for query shells, facet stats, result-card browsing, and metadata-backed search review
- the shared base now also carries stage-11 integrated-shell primitives for cross-surface shell grids, mini metrics, surface status cards, and message metadata inside one operator flow
- the shared base now also carries stage-12 runtime-bridge primitives for compact form fields and API-connection controls inside the same workspace-console language

Update rule:

- keep updating the design system, but only in a controlled way
- in principle, every component that enters the Workspace UI main flow and has reusable value should be added to the shared design system
- add or change base primitives when the same interaction pattern appears across multiple workspace screens
- when a screen introduces a reusable component, move it into the shared layer rather than leaving it as page-local CSS
- allow page-local styling only for layout experiments or one-off review artifacts that are not yet proven reusable
- do not add one-off page styling to the shared layer unless it is becoming a reusable console component
- when the base layer changes, keep the theme variants and review prototypes aligned in the same turn

Current boundary:

- this is a frontend foundation artifact, not a completed product UI
- it supports the planned conversational workspace flow, but does not itself mean the workspace product surface is complete
