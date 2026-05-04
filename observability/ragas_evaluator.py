"""
Ragas-based quality evaluation for LLM responses (Phase 4)
Evalúa answer_relevancy y faithfulness automáticamente
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

try:
    from ragas.metrics import answer_relevancy, faithfulness
    from ragas import evaluate
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False


@dataclass
class EvalResult:
    """Resultado de evaluación de una respuesta"""
    query_id: str
    timestamp: str
    answer_relevancy: float  # 0.0 - 1.0
    faithfulness: float      # 0.0 - 1.0
    ragas_available: bool    # Si la evaluación usó ragas o LLM fallback


class RagasEvaluator:
    """
    Evaluador de calidad de respuestas usando Ragas (con fallback a LLM-as-a-judge)

    Métricas:
    - answer_relevancy: ¿Qué tan relevante es la respuesta a la pregunta?
    - faithfulness: ¿Es la respuesta fiel al contexto/herramientas?
    """

    def __init__(self, llm=None):
        """
        Inicializar evaluador

        Args:
            llm: Instancia de ChatOpenAI (opcional, para fallback LLM-as-a-judge)
        """
        self.results: List[EvalResult] = []
        self.llm = llm
        self.ragas_available = RAGAS_AVAILABLE

        if not RAGAS_AVAILABLE:
            print("[Warning] Ragas not available. Using LLM-as-a-judge fallback.")

    def evaluate(
        self,
        question: str,
        answer: str,
        context: str = ""
    ) -> EvalResult:
        """
        Evaluar calidad de una respuesta

        Args:
            question: La pregunta del usuario
            answer: La respuesta del agente
            context: Contexto relevante (ej: resultados de tools)

        Returns:
            EvalResult con scores de relevancia y faithfulness
        """
        query_id = str(len(self.results))
        timestamp = datetime.now().isoformat()

        if self.ragas_available:
            try:
                return self._evaluate_with_ragas(query_id, timestamp, question, answer, context)
            except Exception as e:
                print(f"[Warning] Ragas evaluation failed: {e}. Using fallback.")
                return self._evaluate_with_llm_fallback(query_id, timestamp, question, answer)
        else:
            return self._evaluate_with_llm_fallback(query_id, timestamp, question, answer)

    def _evaluate_with_ragas(
        self,
        query_id: str,
        timestamp: str,
        question: str,
        answer: str,
        context: str
    ) -> EvalResult:
        """
        Evaluar usando Ragas (requiere ragas instalado)
        """
        try:
            # Crear dataset para Ragas
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [[context]] if context else [[]]
            }

            dataset = Dataset.from_dict(data)

            # Evaluar answer_relevancy
            relevancy_result = evaluate(dataset, metrics=[answer_relevancy])
            answer_relevancy_score = relevancy_result["answer_relevancy"][0]

            # Evaluar faithfulness (requiere contextos)
            faithfulness_score = 0.5  # Default si no hay contexto
            if context:
                try:
                    faith_result = evaluate(dataset, metrics=[faithfulness])
                    faithfulness_score = faith_result["faithfulness"][0]
                except Exception:
                    # Si faithfulness falla, usar LLM fallback
                    faithfulness_score = self._llm_judge_faithfulness(question, answer, context)

            result = EvalResult(
                query_id=query_id,
                timestamp=timestamp,
                answer_relevancy=answer_relevancy_score,
                faithfulness=faithfulness_score,
                ragas_available=True
            )

            self.results.append(result)
            return result

        except Exception as e:
            print(f"[Warning] Ragas evaluation error: {e}")
            raise

    def _evaluate_with_llm_fallback(
        self,
        query_id: str,
        timestamp: str,
        question: str,
        answer: str
    ) -> EvalResult:
        """
        Evaluar usando LLM-as-a-judge (fallback cuando Ragas no disponible)
        """
        relevancy = self._llm_judge_relevancy(question, answer)
        faithfulness = self._llm_judge_faithfulness(question, answer, "")

        result = EvalResult(
            query_id=query_id,
            timestamp=timestamp,
            answer_relevancy=relevancy,
            faithfulness=faithfulness,
            ragas_available=False
        )

        self.results.append(result)
        return result

    def _llm_judge_relevancy(self, question: str, answer: str) -> float:
        """
        Usar el LLM para evaluar relevancia (0.0 - 1.0)
        """
        if not self.llm:
            return 0.5  # Default si no hay LLM configurado

        try:
            prompt = f"""Rate how relevant the following answer is to the question on a scale of 0 to 1.

Question: {question}

Answer: {answer}

Respond with ONLY a number between 0 and 1 (e.g., 0.85). No other text."""

            response = self.llm.invoke(prompt)
            score_text = response.content.strip()

            # Extraer número
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))  # Clamp entre 0 y 1
            except ValueError:
                return 0.5

        except Exception as e:
            print(f"[Warning] LLM relevancy judgment failed: {e}")
            return 0.5

    def _llm_judge_faithfulness(self, question: str, answer: str, context: str) -> float:
        """
        Usar el LLM para evaluar faithfulness (0.0 - 1.0)
        """
        if not self.llm:
            return 0.5

        try:
            context_text = f"Context: {context}\n\n" if context else ""
            prompt = f"""Rate how faithful/accurate the following answer is on a scale of 0 to 1.

{context_text}Question: {question}

Answer: {answer}

Respond with ONLY a number between 0 and 1 (e.g., 0.85). No other text."""

            response = self.llm.invoke(prompt)
            score_text = response.content.strip()

            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))
            except ValueError:
                return 0.5

        except Exception as e:
            print(f"[Warning] LLM faithfulness judgment failed: {e}")
            return 0.5

    def get_session_avg(self) -> Dict[str, float]:
        """
        Obtener promedios de la sesión
        """
        if not self.results:
            return {"answer_relevancy": 0.0, "faithfulness": 0.0}

        avg_relevancy = sum(r.answer_relevancy for r in self.results) / len(self.results)
        avg_faithfulness = sum(r.faithfulness for r in self.results) / len(self.results)

        return {
            "answer_relevancy": avg_relevancy,
            "faithfulness": avg_faithfulness,
            "queries_evaluated": len(self.results)
        }

    def get_eval_report(self) -> str:
        """
        Generar reporte formateado de evaluaciones
        """
        if not self.results:
            return "No evaluations yet"

        stats = self.get_session_avg()

        # Min/Max
        relevancies = [r.answer_relevancy for r in self.results]
        faithfulnesses = [r.faithfulness for r in self.results]

        min_relevancy = min(relevancies) if relevancies else 0
        max_relevancy = max(relevancies) if relevancies else 0
        min_faithfulness = min(faithfulnesses) if faithfulnesses else 0
        max_faithfulness = max(faithfulnesses) if faithfulnesses else 0

        backend = "Ragas" if self.results[0].ragas_available else "LLM-as-a-judge (Ragas not available)"

        report = f"""
RAGAS QUALITY EVALUATION ({backend})
======================================
Queries evaluated:   {stats['queries_evaluated']}

Answer Relevancy
  Average:           {stats['answer_relevancy']:.2f}
  Min:               {min_relevancy:.2f}
  Max:               {max_relevancy:.2f}

Faithfulness
  Average:           {stats['faithfulness']:.2f}
  Min:               {min_faithfulness:.2f}
  Max:               {max_faithfulness:.2f}

Overall Quality Score: {(stats['answer_relevancy'] + stats['faithfulness']) / 2:.2f}
"""
        return report

    def reset(self):
        """Limpiar todos los resultados"""
        self.results.clear()
