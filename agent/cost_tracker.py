"""
Cost Tracker for FinOps - Token consumption tracking and cost projection
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class CostTracker:
    """
    Rastrear consumo de tokens y proyectar costos

    Soporta múltiples modelos y calcula proyecciones automáticas
    """

    # Precios por 1M tokens (precios de OpenAI a febrero 2025)
    COST_PER_TOKEN = {
        "gpt-4o-mini": {
            "input": 0.15 / 1_000_000,    # $0.15 per 1M input tokens
            "output": 0.60 / 1_000_000,   # $0.60 per 1M output tokens
        },
        "gpt-4o": {
            "input": 2.50 / 1_000_000,
            "output": 10.00 / 1_000_000,
        },
        "groq-llama": {
            "input": 0.05 / 1_000_000,    # ~10x más barato
            "output": 0.08 / 1_000_000,
        },
    }

    def __init__(self, default_model: str = "gpt-4o-mini", monthly_queries_estimate: int = 300):
        """
        Inicializar tracker

        Args:
            default_model: Modelo por defecto para precios
            monthly_queries_estimate: Estimación de queries por mes (para proyecciones)
        """
        self.default_model = default_model
        self.monthly_queries_estimate = monthly_queries_estimate

        # Registro de todas las llamadas
        self.calls: List[Dict[str, Any]] = []

        # Acumuladores por sesión
        self.session_cost = 0.0
        self.session_tokens = {"input": 0, "output": 0}
        self.queries_count = 0

        # Timestamp de inicio
        self.session_start = datetime.now()

    def record(self, call_name: str, model: str, input_tokens: int, output_tokens: int) -> None:
        """
        Registrar una llamada al LLM

        Args:
            call_name: Nombre de la llamada (e.g., "route", "generate")
            model: Modelo usado (e.g., "gpt-4o-mini")
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
        """
        if model not in self.COST_PER_TOKEN:
            # Si no existe el modelo, usar el default
            model = self.default_model

        # Calcular costo de esta llamada
        cost_in = input_tokens * self.COST_PER_TOKEN[model]["input"]
        cost_out = output_tokens * self.COST_PER_TOKEN[model]["output"]
        total_cost = cost_in + cost_out

        # Registrar
        call_record = {
            "timestamp": datetime.now(),
            "call_name": call_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_input": cost_in,
            "cost_output": cost_out,
            "total_cost": total_cost,
        }

        self.calls.append(call_record)

        # Acumular
        self.session_cost += total_cost
        self.session_tokens["input"] += input_tokens
        self.session_tokens["output"] += output_tokens

    def get_query_cost(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
        """
        Calcular costo de una query específica

        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de salida
            model: Modelo (usa default si None)

        Returns:
            Costo en USD
        """
        if model is None:
            model = self.default_model
        if model not in self.COST_PER_TOKEN:
            model = self.default_model

        cost_in = input_tokens * self.COST_PER_TOKEN[model]["input"]
        cost_out = output_tokens * self.COST_PER_TOKEN[model]["output"]
        return cost_in + cost_out

    def get_query_summary(self, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """
        Resumen de costo para una query

        Returns:
            Dict con: query_cost, session_cost, total_tokens
        """
        query_cost = self.get_query_cost(input_tokens, output_tokens)
        return {
            "query_cost": query_cost,
            "session_cost": self.session_cost,
            "total_tokens": input_tokens + output_tokens,
        }

    def get_session_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la sesión"""
        total_tokens = self.session_tokens["input"] + self.session_tokens["output"]

        return {
            "queries_count": len(self.calls),
            "total_tokens": total_tokens,
            "input_tokens": self.session_tokens["input"],
            "output_tokens": self.session_tokens["output"],
            "session_cost": self.session_cost,
            "avg_cost_per_query": self.session_cost / len(self.calls) if self.calls else 0,
        }

    def _get_groq_equivalent_cost(self) -> float:
        """
        Calcular costo equivalente si se usara Groq en lugar de OpenAI
        Usa los mismos tokens pero con precios de Groq
        """
        groq_model = "groq-llama"
        input_cost = self.session_tokens["input"] * self.COST_PER_TOKEN[groq_model]["input"]
        output_cost = self.session_tokens["output"] * self.COST_PER_TOKEN[groq_model]["output"]
        return input_cost + output_cost

    def get_projection(self) -> Dict[str, Any]:
        """
        Proyectar costos basado en consumo actual

        Returns:
            Dict con: monthly_cost, yearly_cost, queries_per_day, monthly_estimate
        """
        if not self.calls:
            return {
                "monthly_cost": 0.0,
                "yearly_cost": 0.0,
                "queries_per_day": 0.0,
                "monthly_estimate": self.monthly_queries_estimate,
            }

        # Costo promedio por query (basado en los datos reales)
        avg_cost_per_query = self.session_cost / len(self.calls)

        # Proyectar
        monthly_cost = avg_cost_per_query * self.monthly_queries_estimate
        yearly_cost = monthly_cost * 12
        queries_per_day = self.monthly_queries_estimate / 30

        return {
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
            "queries_per_day": queries_per_day,
            "monthly_estimate": self.monthly_queries_estimate,
        }

    def get_session_report(self) -> str:
        """
        Generar reporte completo de sesión con tabla formateada

        Returns:
            String con reporte en formato tabla
        """
        stats = self.get_session_stats()
        proj = self.get_projection()
        groq_cost = self._get_groq_equivalent_cost()

        # Diferencia
        savings = self.session_cost - groq_cost
        savings_pct = (savings / self.session_cost * 100) if self.session_cost > 0 else 0

        report = f"""
╔════════════════════════════════════════════╗
║  SESSION COST & TOKEN ANALYSIS             ║
╠════════════════════════════════════════════╣
║  Queries procesadas:  {stats['queries_count']:>4}              ║
║  Total Tokens:        {stats['total_tokens']:>4,}              ║
║    - Input:           {stats['input_tokens']:>4,}              ║
║    - Output:          {stats['output_tokens']:>4,}              ║
║  Costo sesión:        ${stats['session_cost']:.4f}              ║
║  Costo promedio:      ${stats['avg_cost_per_query']:.4f}/query    ║
╠════════════════════════════════════════════╣
║  PROYECCIONES (~{proj['monthly_estimate']} queries/mes)   ║
║  Costo mensual:       ${proj['monthly_cost']:.2f}              ║
║  Costo anual:         ${proj['yearly_cost']:.2f}              ║
╠════════════════════════════════════════════╣
║  COMPARATIVA DE PROVIDERS                  ║
║  OpenAI (actual):     ${self.session_cost:.4f}              ║
║  Groq (llama):        ${groq_cost:.4f}              ║
║  Ahorro potencial:    {savings_pct:.0f}% más barato          ║
╚════════════════════════════════════════════╝
"""
        return report

    def reset(self) -> None:
        """Resetear el tracker para nueva sesión"""
        self.calls.clear()
        self.session_cost = 0.0
        self.session_tokens = {"input": 0, "output": 0}
        self.queries_count = 0
        self.session_start = datetime.now()
