from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

from config import Settings


def normalize_bridge_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(ascii_text.lower().replace("_", " ").replace("-", " ").split())


def _load_bridge_file(path: str, mtime: int) -> Dict[str, Any]:
    # mtime participates in the cache key.
    _ = mtime
    raw = Path(path).read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw) or {}
    return parsed if isinstance(parsed, dict) else {}


@lru_cache(maxsize=8)
def _cached_bridge_file(path: str, mtime: int) -> Dict[str, Any]:
    return _load_bridge_file(path, mtime)


def load_semantic_bridges(settings: Settings) -> List[Dict[str, Any]]:
    bridge_path = settings.resolved_knowledge_dir / "_system" / "semantic-bridges.yaml"
    if not bridge_path.exists():
        return []
    parsed = _cached_bridge_file(str(bridge_path), int(bridge_path.stat().st_mtime))
    concepts = parsed.get("concepts") or []
    if isinstance(concepts, dict):
        concepts = [{"id": key, **(value or {})} for key, value in concepts.items()]
    output: List[Dict[str, Any]] = []
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        bridge_id = str(concept.get("id") or "").strip()
        if not bridge_id:
            continue
        aliases = [str(item).strip() for item in concept.get("aliases") or [] if str(item).strip()]
        expansion_terms = [str(item).strip() for item in concept.get("expansion_terms") or [] if str(item).strip()]
        target_sources = [str(item).strip().replace("\\", "/").strip("/") for item in concept.get("target_sources") or [] if str(item).strip()]
        active_contexts = [str(item).strip().lower() for item in concept.get("active_contexts") or [] if str(item).strip()]
        output.append(
            {
                "id": bridge_id,
                "label": str(concept.get("label") or bridge_id),
                "aliases": aliases,
                "aliases_normalized": [normalize_bridge_text(item) for item in aliases],
                "expansion_terms": expansion_terms,
                "expansion_terms_normalized": [normalize_bridge_text(item) for item in expansion_terms],
                "target_sources": target_sources,
                "target_sources_normalized": {_normalize_source(item) for item in target_sources},
                "active_contexts": active_contexts,
                "priority_boost": float(concept.get("priority_boost") or 0.0),
                "notes": str(concept.get("notes") or ""),
            }
        )
    return output


def _normalize_source(source: str) -> str:
    clean = (source or "").replace("\\", "/").strip("/")
    if clean.startswith("knowledge/"):
        clean = clean[len("knowledge/") :]
    return clean.lower()


def resolve_semantic_bridges(settings: Settings, query: str, active_context: str | None) -> Dict[str, Any]:
    normalized_query = normalize_bridge_text(query)
    normalized_context = normalize_bridge_text(active_context or "")
    matched: List[Dict[str, Any]] = []
    for bridge in load_semantic_bridges(settings):
        alias_hits = [alias for alias in bridge["aliases_normalized"] if alias and alias in normalized_query]
        context_hit = normalized_context and normalized_context in bridge.get("active_contexts", [])
        if alias_hits or context_hit:
            matched.append({**bridge, "matched_aliases": alias_hits, "matched_context": bool(context_hit)})

    expansion_terms: List[str] = []
    target_sources: Set[str] = set()
    for bridge in matched:
        for term in bridge.get("expansion_terms") or []:
            if term not in expansion_terms:
                expansion_terms.append(term)
        target_sources.update(bridge.get("target_sources_normalized") or set())

    variants: List[str] = []
    for item in [query, *expansion_terms]:
        clean = str(item or "").strip()
        if not clean:
            continue
        if normalize_bridge_text(clean) not in {normalize_bridge_text(existing) for existing in variants}:
            variants.append(clean)

    return {
        "matched": matched,
        "bridge_ids": [bridge["id"] for bridge in matched],
        "expansion_terms": expansion_terms,
        "target_sources": sorted(target_sources),
        "query_variants": variants[:8] or [query],
    }


def semantic_bridge_document_score(metadata: Dict[str, Any], content: str, bridge_context: Dict[str, Any] | None) -> Dict[str, Any]:
    if not bridge_context:
        return {"boost": 0.0, "bridge_ids": [], "match_reason": ""}
    source = _normalize_source(str(metadata.get("source") or ""))
    haystack = normalize_bridge_text(
        " ".join(
            [
                str(metadata.get("source") or ""),
                str(metadata.get("title") or ""),
                str(metadata.get("category") or ""),
                str(metadata.get("tags") or ""),
                str(metadata.get("summary") or ""),
                content[:1800],
            ]
        )
    )
    bridge_ids: List[str] = []
    reasons: List[str] = []
    boost = 0.0
    for bridge in bridge_context.get("matched") or []:
        bridge_boost = float(bridge.get("priority_boost") or 0.0)
        targets = bridge.get("target_sources_normalized") or set()
        expansion_hits = [term for term in bridge.get("expansion_terms_normalized") or [] if term and term in haystack]
        target_hit = source in targets
        if not target_hit and targets:
            target_hit = any(source.endswith("/" + target) or target.endswith("/" + source) for target in targets)
        if target_hit:
            boost += bridge_boost
            bridge_ids.append(str(bridge["id"]))
            reasons.append(f"ponte {bridge['id']} -> fonte alvo")
        elif expansion_hits:
            boost += bridge_boost * 0.35
            bridge_ids.append(str(bridge["id"]))
            reasons.append(f"ponte {bridge['id']} -> termo relacionado")
    return {
        "boost": round(boost, 4),
        "bridge_ids": sorted(set(bridge_ids)),
        "match_reason": "; ".join(dict.fromkeys(reasons)),
    }
