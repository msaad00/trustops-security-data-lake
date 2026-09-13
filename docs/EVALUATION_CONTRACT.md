# Evaluation contract

Unknown named rules, malformed inline predicates and duplicate control IDs are rejected before normalization publishes its output. Invalid rules never fall back to a different rule or produce a passing verdict. The prior published lake remains available when mapping validation fails.

Both direct evaluation and catalog preflight use the same validator. Validation covers recognized operators, nonempty boolean compositions, integer violation bounds, severity values, freshness states, boolean evidence presence and finite coverage thresholds from zero to one. An omitted rule retains the documented default; an explicitly invalid rule raises `PolicyError` with its control ID.

Validation checks all supplied mappings, including controls with no matching evidence in the current batch. Duplicate IDs are rejected because selecting whichever definition appears last would make rule selection ambiguous.

This preflight does not make multi-file publication transactional. Interrupted writes and generation-level consistency are separate publication concerns.
