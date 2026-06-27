# AI Synthetic User Platform Guided Drafts

These are V4 guided draft briefs for evaluating the target users of the
`AI synthetic user x design thinking x user research` SaaS concept.

Reserved draft IDs:

- `su_1101`: Solo founder
- `su_1102`: UX generalist / product designer
- `su_1103`: Startup PM / product lead
- `su_1104`: Enterprise UX researcher / research ops lead
- `su_1105`: Enterprise innovation / strategy manager

Suggested next-step generation commands:

```powershell
python -m ai_validation_swarm.cli.main generate-v4-persona `
  --persona-id su_1101 `
  --backend codex-sdk `
  --output-dir data/personas `
  --guide-file data/personas/.v4_generation/guides/ai-synthetic-user-platform/su_1101.json
```

Repeat with `su_1102` to `su_1105`.
