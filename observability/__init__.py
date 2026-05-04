"""
Observability module for Phase 4

Provides:
- LocalTracer: local tracing without external dependencies
- RagasEvaluator: quality evaluation with Ragas (+ LLM fallback)
"""

from .tracer import LocalTracer
from .ragas_evaluator import RagasEvaluator

__all__ = ["LocalTracer", "RagasEvaluator"]
