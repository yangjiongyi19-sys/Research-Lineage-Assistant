"""Query understanding, decomposition, expansion, and iterative query generation."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_KNOWN_TECH = {
    "llm": "LLM (Large Language Models)",
    "large language model": "LLM (Large Language Models)",
    "transformer": "Transformer",
    "codebert": "CodeBERT",
    "unixcoder": "UniXcoder",
    "gpt": "GPT",
}

_DOMAIN_HINTS = {
    "漏洞": "vulnerability detection",
    "vulnerability": "vulnerability detection",
    "security": "security analysis",
    "代码": "code analysis",
    "code": "code analysis",
}


def build_query_plan(query: str, iterations: int = 0, analysis_gaps: List[str] | None = None) -> Dict[str, Any]:
    semantic = parse_query_intent(query)
    sub_questions = decompose_query(query, semantic, iterations, analysis_gaps or [])
    expanded_queries = expand_sub_questions(sub_questions, semantic)
    return {
        "semantic": semantic,
        "sub_questions": sub_questions,
        "expanded_queries": expanded_queries,
    }


def parse_query_intent(query: str) -> Dict[str, Any]:
    lower = query.lower()
    core_tech = _detect_core_tech(lower)
    application_domain = _detect_domain(query, lower)
    sub_domain = _detect_subdomains(query, lower)

    return {
        "task_type": "research/survey",
        "core_tech": core_tech,
        "application_domain": application_domain,
        "sub_domain": sub_domain,
        "expected_output": [
            "methods",
            "datasets",
            "evaluation",
            "limitations",
            "recent work",
        ],
    }


def decompose_query(
    query: str,
    semantic: Dict[str, Any],
    iterations: int,
    analysis_gaps: List[str],
) -> List[Dict[str, str]]:
    topic = _english_topic(query, semantic)
    questions = [
        ("overview", f"{topic} survey"),
        ("methods", f"{topic} methods"),
        ("models", f"{semantic['core_tech']} for {semantic['application_domain']}"),
        ("datasets", f"datasets benchmarks for {semantic['application_domain']}"),
        ("evaluation", f"evaluation metrics for {semantic['application_domain']}"),
        ("limitations", f"limitations of {semantic['core_tech']} in {semantic['application_domain']}"),
        ("recent_work", f"recent papers 2023 2024 2025 {topic}"),
    ]

    if _is_vulnerability_topic(semantic):
        questions.extend(
            [
                ("cwe", "CWE classification LLM vulnerability detection"),
                ("bigvul", "BigVul Devign dataset vulnerability detection"),
                ("static_analysis", "hybrid static analysis LLM vulnerability detection"),
            ]
        )

    if iterations > 0:
        for gap in analysis_gaps[:5]:
            questions.append(("gap", gap))

    return [{"id": key, "query": value} for key, value in questions]


def expand_sub_questions(
    sub_questions: List[Dict[str, str]],
    semantic: Dict[str, Any],
) -> List[Dict[str, Any]]:
    expanded = []
    for question in sub_questions:
        base = question["query"]
        variants = _variants_for_question(base, question["id"], semantic)
        expanded.append(
            {
                "id": question["id"],
                "base_query": base,
                "academic_queries": variants["academic"],
                "web_queries": variants["web"],
            }
        )
    return expanded


def generate_gap_queries(analysis_results: List[Dict[str, Any]], semantic: Dict[str, Any]) -> List[str]:
    combined_points = " ".join(
        " ".join(result.get("key_points", [])) for result in analysis_results
    ).lower()
    gaps: List[str] = []

    expected_terms = {
        "datasets": "benchmark datasets",
        "evaluation": "precision recall f1 evaluation metrics",
        "limitations": "limitations hallucination false positives",
        "recent work": "recent papers 2024 2025",
    }
    if _is_vulnerability_topic(semantic):
        expected_terms.update(
            {
                "cwe": "CWE classification vulnerability detection",
                "bigvul": "BigVul Devign vulnerability detection dataset details",
            }
        )

    for key, query in expected_terms.items():
        if key not in combined_points:
            gaps.append(query)

    return gaps


def _detect_core_tech(lower: str) -> str:
    for key, value in _KNOWN_TECH.items():
        if key in lower:
            return value
    if "大模型" in lower or "语言模型" in lower:
        return "LLM (Large Language Models)"
    return "AI models"


def _detect_domain(query: str, lower: str) -> str:
    for key, value in _DOMAIN_HINTS.items():
        if key in lower or key in query:
            return value
    return query


def _detect_subdomains(query: str, lower: str) -> List[str]:
    subdomains: List[str] = []
    if "漏洞" in query or "vulnerability" in lower:
        subdomains.extend(
            [
                "code vulnerability detection",
                "security analysis",
                "CWE classification",
            ]
        )
    if not subdomains:
        subdomains.extend(["methods", "benchmarks", "applications"])
    return subdomains


def _english_topic(query: str, semantic: Dict[str, Any]) -> str:
    if _is_vulnerability_topic(semantic):
        return f"{semantic['core_tech']} vulnerability detection"
    cleaned = re.sub(r"\s+", " ", query).strip()
    return cleaned or f"{semantic['core_tech']} {semantic['application_domain']}"


def _is_vulnerability_topic(semantic: Dict[str, Any]) -> bool:
    domain = semantic.get("application_domain", "").lower()
    subdomains = " ".join(semantic.get("sub_domain", [])).lower()
    return "vulnerability" in domain or "vulnerability" in subdomains


def _variants_for_question(base: str, question_id: str, semantic: Dict[str, Any]) -> Dict[str, List[str]]:
    academic = [
        base,
        f"{base} paper",
        f"{base} survey",
    ]
    web = [
        f"{base} blog",
        f"{base} explanation",
        f"{base} tutorial analysis",
    ]

    if question_id == "datasets":
        academic.extend(
            [
                f"BigVul dataset {semantic['application_domain']}",
                f"Devign dataset {semantic['application_domain']}",
                f"benchmark datasets {semantic['application_domain']}",
            ]
        )
        web.append(f"{semantic['application_domain']} dataset comparison")
    elif question_id == "evaluation":
        academic.extend(
            [
                f"precision recall f1 {semantic['application_domain']}",
                f"evaluation metrics {semantic['application_domain']}",
            ]
        )
    elif question_id == "limitations":
        academic.extend(
            [
                f"limitations hallucination {semantic['core_tech']} {semantic['application_domain']}",
                f"false positives false negatives {semantic['application_domain']}",
            ]
        )
        web.append(f"{semantic['core_tech']} {semantic['application_domain']} limitations discussion")
    elif question_id == "recent_work":
        academic.extend(
            [
                f"2024 {semantic['core_tech']} {semantic['application_domain']}",
                f"2025 {semantic['core_tech']} {semantic['application_domain']}",
            ]
        )

    return {
        "academic": _dedupe_strings(academic)[:5],
        "web": _dedupe_strings(web)[:4],
    }


def _dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        normalized = " ".join(value.split())
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output
