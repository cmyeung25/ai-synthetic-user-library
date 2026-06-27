# Prototype Validation Clickable Demo

This engineering demo shows the current Milestone 8 prototype-validation surface without requiring a live LLM backend.

It demonstrates:

- clickable prototype manifest execution
- observed action trace capture
- prototype-validation transcript generation
- prototype-validation insight synthesis
- explicit observed-action evidence boundary

Run it from the repo root:

```powershell
python .\scripts\run_prototype_validation_clickable_demo.py
```

Expected outputs are written under `demo_runs/interviews/<session_id>/`:

- `transcript.md`
- `insights.md`
- `stimulus_analysis.json`
- `observed_action_trace.json`
- `insight_report.json`

The clickable manifest used by the demo lives at:

- `demo/prototype_validation_clickable/prototype-clickable-manifest.json`

This is still synthetic evidence. It is useful for validating the platform contract and artifact shape, not for claiming human usability proof.
