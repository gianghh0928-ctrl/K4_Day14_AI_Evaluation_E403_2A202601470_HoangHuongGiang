"""
Day 14 — AI Evaluation & Benchmarking Pipeline
AICB-P1: AI Practical Competency Program, Phase 1

Solution module containing completed evaluation core.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Task 1 — Data Models (Golden Dataset + Evaluation Results)
# ---------------------------------------------------------------------------

@dataclass
class QAPair:
    question: str
    expected_answer: str
    context: str = ""
    metadata: dict = field(default_factory=dict)
    retrieved_contexts: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    qa_pair: QAPair
    actual_answer: str
    faithfulness: float
    relevance: float
    completeness: float
    passed: bool
    failure_type: str | None = None
    context_precision: float | None = None
    context_recall: float | None = None

    def overall_score(self) -> float:
        return (self.faithfulness + self.relevance + self.completeness) / 3.0


# ---------------------------------------------------------------------------
# Task 2 — RAGASEvaluator (Simplified word-overlap heuristic)
# ---------------------------------------------------------------------------
STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "as", "by", "and", "or",
    "it", "its", "this", "that", "these", "those", "from", "into", "than",
}


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    tokens = re.findall(r"\b\w+\b", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


class RAGASEvaluator:

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        answer_tokens = _tokenize(answer)
        if not answer_tokens:
            return 1.0
        context_tokens = _tokenize(context)
        score = len(answer_tokens & context_tokens) / len(answer_tokens)
        return min(max(score, 0.0), 1.0)

    def evaluate_relevance(self, answer: str, question: str) -> float:
        question_tokens = _tokenize(question)
        if not question_tokens:
            return 1.0
        answer_tokens = _tokenize(answer)
        score = len(answer_tokens & question_tokens) / len(question_tokens)
        return min(max(score, 0.0), 1.0)

    def evaluate_completeness(self, answer: str, expected: str) -> float:
        expected_tokens = _tokenize(expected)
        if not expected_tokens:
            return 1.0
        answer_tokens = _tokenize(answer)
        score = len(answer_tokens & expected_tokens) / len(expected_tokens)
        return min(max(score, 0.0), 1.0)

    def evaluate_context_recall(self, contexts: list[str], expected: str) -> float:
        expected_tokens = _tokenize(expected)
        if not expected_tokens:
            return 1.0
        union_tokens: set[str] = set()
        for chunk in contexts:
            union_tokens.update(_tokenize(chunk))
        score = len(expected_tokens & union_tokens) / len(expected_tokens)
        return min(max(score, 0.0), 1.0)

    def evaluate_context_precision(
        self,
        contexts: list[str],
        expected: str,
        relevance_threshold: float = 0.1,
    ) -> float:
        expected_tokens = _tokenize(expected)
        if not expected_tokens:
            return 1.0
        if not contexts:
            return 0.0

        relevant_flags = []
        for chunk in contexts:
            chunk_tokens = _tokenize(chunk)
            cov = len(chunk_tokens & expected_tokens) / len(expected_tokens)
            relevant_flags.append(1 if cov >= relevance_threshold else 0)

        num_relevant = sum(relevant_flags)
        if num_relevant == 0:
            return 0.0

        running_rel = 0
        sum_precision = 0.0
        for k, rel in enumerate(relevant_flags, start=1):
            if rel:
                running_rel += 1
                precision_at_k = running_rel / k
                sum_precision += precision_at_k

        ap = sum_precision / num_relevant
        return min(max(ap, 0.0), 1.0)

    def run_full_eval(
        self,
        answer: str,
        question: str,
        context: str,
        expected: str,
        contexts: list[str] | None = None,
    ) -> EvalResult:
        faithfulness = self.evaluate_faithfulness(answer, context)
        relevance = self.evaluate_relevance(answer, question)
        completeness = self.evaluate_completeness(answer, expected)

        passed = bool(faithfulness >= 0.5 and relevance >= 0.5 and completeness >= 0.5)

        failure_type: str | None = None
        if not passed:
            if faithfulness < 0.3:
                failure_type = "hallucination"
            elif relevance < 0.3:
                failure_type = "irrelevant"
            elif completeness < 0.3:
                failure_type = "incomplete"
            else:
                failure_type = "off_topic"

        context_recall: float | None = None
        context_precision: float | None = None
        if contexts is not None:
            context_recall = self.evaluate_context_recall(contexts, expected)
            context_precision = self.evaluate_context_precision(contexts, expected)

        qa_pair = QAPair(question=question, expected_answer=expected, context=context)

        return EvalResult(
            qa_pair=qa_pair,
            actual_answer=answer,
            faithfulness=faithfulness,
            relevance=relevance,
            completeness=completeness,
            passed=passed,
            failure_type=failure_type,
            context_precision=context_precision,
            context_recall=context_recall,
        )


def rerank_by_overlap(contexts: list[str], query: str) -> list[str]:
    query_tokens = _tokenize(query)
    return sorted(contexts, key=lambda c: len(_tokenize(c) & query_tokens), reverse=True)


# ---------------------------------------------------------------------------
# Task 3 — LLM Judge
# ---------------------------------------------------------------------------

class LLMJudge:

    def __init__(self, judge_llm_fn: Callable[[str], str]) -> None:
        self.judge_llm_fn = judge_llm_fn

    def score_response(
        self,
        question: str,
        answer: str,
        rubric: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = (
            f"Question: {question}\n"
            f"Answer: {answer}\n"
            f"Rubric: {rubric}\n"
            "Please evaluate the answer based on the rubric and return a JSON object."
        )
        response_text = self.judge_llm_fn(prompt)

        scores: dict[str, float] = {}
        reasoning: str = response_text

        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, dict):
                if "scores" in parsed and isinstance(parsed["scores"], dict):
                    scores = {k: float(v) for k, v in parsed["scores"].items()}
                    if "reasoning" in parsed:
                        reasoning = str(parsed["reasoning"])
                else:
                    for k, v in parsed.items():
                        if isinstance(v, (int, float)):
                            scores[k] = float(v)
        except Exception:
            pass

        if not scores:
            scores = {criterion: 0.5 for criterion in rubric}

        return {
            "scores": scores,
            "reasoning": reasoning,
        }

    def detect_bias(self, scores_batch: list[dict[str, Any]]) -> dict[str, Any]:
        if not scores_batch:
            return {
                "positional_bias": False,
                "leniency_bias": False,
                "severity_bias": False,
            }

        all_scores: list[float] = []
        for item in scores_batch:
            scores_dict = item.get("scores", {})
            all_scores.extend(scores_dict.values())

        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            leniency_bias = avg_score > 0.8
            severity_bias = avg_score < 0.3
        else:
            leniency_bias = False
            severity_bias = False

        positional_bias = False
        if len(scores_batch) >= 2:
            first_item_scores = list(scores_batch[0].get("scores", {}).values())
            rest_items_scores = []
            for item in scores_batch[1:]:
                rest_items_scores.extend(item.get("scores", {}).values())

            if first_item_scores and rest_items_scores:
                first_avg = sum(first_item_scores) / len(first_item_scores)
                rest_avg = sum(rest_items_scores) / len(rest_items_scores)
                positional_bias = first_avg > rest_avg

        return {
            "positional_bias": positional_bias,
            "leniency_bias": leniency_bias,
            "severity_bias": severity_bias,
        }


# ---------------------------------------------------------------------------
# Task 4 — Benchmark Runner
# ---------------------------------------------------------------------------

class BenchmarkRunner:

    def run(
        self,
        qa_pairs: list[QAPair],
        agent_fn: Callable[[str], str],
        evaluator: RAGASEvaluator,
    ) -> list[EvalResult]:
        results: list[EvalResult] = []
        for pair in qa_pairs:
            actual_answer = agent_fn(pair.question)
            eval_res = evaluator.run_full_eval(
                answer=actual_answer,
                question=pair.question,
                context=pair.context,
                expected=pair.expected_answer,
                contexts=pair.retrieved_contexts if pair.retrieved_contexts else None,
            )
            eval_res.qa_pair = pair
            results.append(eval_res)
        return results

    def generate_report(self, results: list[EvalResult]) -> dict[str, Any]:
        total = len(results)
        if total == 0:
            return {
                "total": 0,
                "passed": 0,
                "pass_rate": 0.0,
                "avg_faithfulness": 0.0,
                "avg_relevance": 0.0,
                "avg_completeness": 0.0,
                "avg_context_recall": None,
                "avg_context_precision": None,
                "failure_types": {},
            }

        passed_count = sum(1 for r in results if r.passed)
        avg_faithfulness = sum(r.faithfulness for r in results) / total
        avg_relevance = sum(r.relevance for r in results) / total
        avg_completeness = sum(r.completeness for r in results) / total

        recalls = [r.context_recall for r in results if r.context_recall is not None]
        precisions = [r.context_precision for r in results if r.context_precision is not None]

        avg_context_recall = (sum(recalls) / len(recalls)) if recalls else None
        avg_context_precision = (sum(precisions) / len(precisions)) if precisions else None

        failure_types: dict[str, int] = {}
        for r in results:
            if r.failure_type:
                failure_types[r.failure_type] = failure_types.get(r.failure_type, 0) + 1

        return {
            "total": total,
            "passed": passed_count,
            "pass_rate": passed_count / total,
            "avg_faithfulness": avg_faithfulness,
            "avg_relevance": avg_relevance,
            "avg_completeness": avg_completeness,
            "avg_context_recall": avg_context_recall,
            "avg_context_precision": avg_context_precision,
            "failure_types": failure_types,
        }

    def run_regression(self, new_results: list[EvalResult], baseline_results: list[EvalResult]) -> dict[str, Any]:
        new_total = len(new_results)
        base_total = len(baseline_results)

        new_faith = (sum(r.faithfulness for r in new_results) / new_total) if new_total > 0 else 0.0
        new_rel = (sum(r.relevance for r in new_results) / new_total) if new_total > 0 else 0.0
        new_comp = (sum(r.completeness for r in new_results) / new_total) if new_total > 0 else 0.0

        base_faith = (sum(r.faithfulness for r in baseline_results) / base_total) if base_total > 0 else 0.0
        base_rel = (sum(r.relevance for r in baseline_results) / base_total) if base_total > 0 else 0.0
        base_comp = (sum(r.completeness for r in baseline_results) / base_total) if base_total > 0 else 0.0

        regressions: list[str] = []
        if base_faith - new_faith > 0.05:
            regressions.append("faithfulness")
        if base_rel - new_rel > 0.05:
            regressions.append("relevance")
        if base_comp - new_comp > 0.05:
            regressions.append("completeness")

        return {
            "new_avg_faithfulness": new_faith,
            "new_avg_relevance": new_rel,
            "new_avg_completeness": new_comp,
            "baseline_avg_faithfulness": base_faith,
            "baseline_avg_relevance": base_rel,
            "baseline_avg_completeness": base_comp,
            "regressions": regressions,
            "passed": len(regressions) == 0,
        }

    def identify_failures(
        self,
        results: list[EvalResult],
        threshold: float = 0.5,
    ) -> list[EvalResult]:
        failures = []
        for r in results:
            if r.faithfulness < threshold or r.relevance < threshold or r.completeness < threshold:
                failures.append(r)
        return failures


# ---------------------------------------------------------------------------
# Task 5 — Failure Analyzer
# ---------------------------------------------------------------------------

class FailureAnalyzer:

    def categorize_failures(
        self, failures: list[EvalResult]
    ) -> dict[str, int]:
        categories: dict[str, int] = {}
        for f in failures:
            if f.failure_type:
                categories[f.failure_type] = categories.get(f.failure_type, 0) + 1
        return categories

    def find_root_cause(self, failure: EvalResult) -> str:
        f_score = failure.faithfulness
        r_score = failure.relevance
        c_score = failure.completeness

        min_score = min(f_score, r_score, c_score)
        scores = [f_score, r_score, c_score]

        if scores.count(min_score) > 1 and min_score < 0.5:
            return "Multiple issues detected — review full pipeline"

        if min_score == f_score:
            return "Context is missing or irrelevant — improve retrieval"
        elif min_score == r_score:
            return "Answer does not address the question — improve prompt clarity"
        else:
            return "Answer is missing key information — increase context window or improve generation"

    def generate_improvement_log(self, failures: list[EvalResult], suggestions: list[str]) -> str:
        lines = [
            "| Failure ID | Type | Root Cause | Suggested Fix | Status |",
            "|------------|------|------------|---------------|--------|",
        ]
        for i, f in enumerate(failures, start=1):
            fid = f"F{i:03d}"
            ftype = f.failure_type if f.failure_type else "Unknown"
            root_cause = self.find_root_cause(f)
            fix = suggestions[i - 1] if i - 1 < len(suggestions) else (suggestions[0] if suggestions else "Investigate pipeline")
            lines.append(f"| {fid} | {ftype} | {root_cause} | {fix} | Open |")

        return "\n".join(lines)

    def generate_improvement_suggestions(
        self, failures: list[EvalResult]
    ) -> list[str]:
        suggestions: list[str] = []
        cat_counts = self.categorize_failures(failures)

        if cat_counts.get("hallucination", 0) > 0:
            suggestions.append("Implement hallucination checker to filter unsupported claims")
        if cat_counts.get("irrelevant", 0) > 0 or cat_counts.get("off_topic", 0) > 0:
            suggestions.append("Refine prompt clarity and intent classification to address question directly")
        if cat_counts.get("incomplete", 0) > 0:
            suggestions.append("Add few-shot examples showing complete answers to improve completeness")

        default_suggestions = [
            "Increase chunk size in RAG pipeline to reduce context fragmentation",
            "Add few-shot examples showing complete answers to improve completeness",
            "Implement hallucination checker to filter unsupported claims",
        ]

        for ds in default_suggestions:
            if len(suggestions) >= 3:
                break
            if ds not in suggestions:
                suggestions.append(ds)

        return suggestions
