"""Ingestion strategy + resilient-pull primitives for the compliance data layer.

This package encodes *how* each source is ingested — the velocity/cost decision
(:mod:`strategy`) and the reusable pull primitives (watermark, pagination,
backoff, idempotent merge) the direct-API runners depend on.
"""
