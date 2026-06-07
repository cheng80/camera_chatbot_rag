# Project Instructions

## Technical Evidence Documentation

When adding, replacing, or materially changing project technology, retrieval logic,
LLM/model behavior, evaluation criteria, or generated evidence artifacts, update
[docs/project/technical_evidence_matrix.md](docs/project/technical_evidence_matrix.md)
in the same change.

Keep the evidence matrix report-ready:

- Link the implementation files that prove the technology is actually used.
- Link evaluation outputs or runtime artifacts when the change affects quality,
  latency, token usage, JSON stability, retrieval, or answer generation.
- Update the current caveat or conclusion when the technical recommendation
  changes.
- Do not copy secrets from `.env`; reference setting names only.
