"""
Local tracing for observability (Phase 4)
Registra latencias, tokens, y tool calls sin dependencias externas
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


@dataclass
class TraceEntry:
    """Una entrada de traza de una query"""
    query_id: str
    timestamp: str
    query: str
    tool_called: Optional[str]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    success: bool


class LocalTracer:
    """
    Tracer local que registra métricas de sesión sin plataformas externas
    """

    def __init__(self):
        self.traces: List[TraceEntry] = []
        self._active_queries: Dict[str, float] = {}  # query_id -> start_time

    def start_query(self, query: str) -> str:
        """
        Marcar el inicio de una query

        Args:
            query: El mensaje del usuario

        Returns:
            query_id para usar en end_query()
        """
        query_id = str(uuid.uuid4())[:8]
        self._active_queries[query_id] = time.time()
        return query_id

    def end_query(
        self,
        query_id: str,
        tool_called: Optional[str],
        input_tokens: int,
        output_tokens: int,
        success: bool = True
    ) -> float:
        """
        Marcar el final de una query

        Args:
            query_id: Retornado por start_query()
            tool_called: Nombre de la tool llamada (o None)
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            success: Si la query fue exitosa

        Returns:
            Latencia en milisegundos
        """
        if query_id not in self._active_queries:
            return 0.0

        start_time = self._active_queries.pop(query_id)
        latency_ms = (time.time() - start_time) * 1000

        trace = TraceEntry(
            query_id=query_id,
            timestamp=datetime.now().isoformat(),
            query="[query]",  # No guardar el texto completo para privacidad
            tool_called=tool_called,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success
        )

        self.traces.append(trace)
        return latency_ms

    def get_metrics_report(self) -> str:
        """
        Generar reporte formateado de métricas de la sesión
        """
        if not self.traces:
            return "No queries traced yet"

        # Calcular estadísticas
        total_queries = len(self.traces)
        latencies = [t.latency_ms for t in self.traces]
        successful = sum(1 for t in self.traces if t.success)
        success_rate = (successful / total_queries * 100) if total_queries > 0 else 0

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        # Tool distribution
        tool_counts = defaultdict(int)
        for trace in self.traces:
            tool_name = trace.tool_called or "no_tool"
            tool_counts[tool_name] += 1

        # Tokens
        total_input = sum(t.input_tokens for t in self.traces)
        total_output = sum(t.output_tokens for t in self.traces)
        total_tokens = total_input + total_output
        avg_tokens_per_query = total_tokens / total_queries if total_queries > 0 else 0

        # Formatear reporte
        report = f"""
SESSION PERFORMANCE METRICS
============================
Total queries:      {total_queries}
Success rate:       {success_rate:.0f}%
Avg latency:        {avg_latency:.0f}ms
Min latency:        {min_latency:.0f}ms
Max latency:        {max_latency:.0f}ms
Avg tokens/query:   {avg_tokens_per_query:.0f}

TOOL DISTRIBUTION
================="""

        for tool_name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            pct = (count / total_queries * 100) if total_queries > 0 else 0
            report += f"\n  {tool_name:30} {count:3} ({pct:5.1f}%)"

        report += f"""

TOKEN USAGE
===========
Total input:        {total_input:,}
Total output:       {total_output:,}
Total tokens:       {total_tokens:,}
"""
        return report

    def reset(self):
        """Limpiar todas las trazas"""
        self.traces.clear()
        self._active_queries.clear()
