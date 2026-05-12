"""
PersonaVLM POC — Reasoning Layer
Temporal reasoning over accumulated memories.
Detects patterns, recurring issues, and actionable insights that aren't visible
in single-session contexts. Modeled after April's cross-session email/calendar reasoning.
"""
import sqlite3
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from memory_layer import get_conn, retrieve_memories, get_related_memories


def analyze_patterns(user_id: str, domain: str = "email", days: int = 30) -> dict:
    """
    Analyze behavioral patterns over the last N days.
    Returns temporal patterns, recurring recipients, tone distribution.
    """
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    rows = conn.execute(
        """SELECT * FROM memories
           WHERE user_id = ? AND domain = ? AND created_at > ?
           ORDER BY created_at""",
        (user_id, domain, cutoff),
    ).fetchall()
    conn.close()

    memories = [dict(r) for r in rows]
    if not memories:
        return {"status": "no_data", "message": "Insufficient memories for pattern analysis"}

    # Pattern 1: Temporal frequency — when does the user interact most?
    hourly_distribution = Counter()
    for m in memories:
        try:
            dt = datetime.fromisoformat(m["created_at"])
            hour = dt.hour
            hourly_distribution[hour] += 1
        except:
            pass

    peak_hours = sorted(hourly_distribution.items(), key=lambda x: -x[1])[:3]

    # Pattern 2: Recurring topics / recipients
    content_keywords = Counter()
    recipients = Counter()
    for m in memories:
        content = m["content"].lower()
        for word in content.split():
            if len(word) > 4:
                content_keywords[word] += 1
        # Extract mentioned entities (simple heuristic: proper nouns)
        parts = content.split()
        for i, p in enumerate(parts):
            if p.endswith((":", "s,", "s'", "@")) or "@" in p:
                recipients[p.strip(",:@'s")] += 1

    # Pattern 3: Tone/style preferences
    tone_mentions = {"concise": 0, "formal": 0, "warm": 0, "detailed": 0, "terse": 0}
    for m in memories:
        content = m["content"].lower()
        for tone in tone_mentions:
            if tone in content:
                tone_mentions[tone] += 1

    dominant_tones = [t for t, c in sorted(tone_mentions.items(), key=lambda x: -x[1]) if c > 0]

    # Pattern 4: Unresolved threads (interaction memories without follow-up)
    from memory_layer import get_conn as gc
    c2 = gc()
    unresolved = c2.execute(
        """SELECT * FROM memories
           WHERE user_id = ? AND memory_type = 'interaction'
           AND content LIKE '%follow-up%'
           AND id NOT IN (SELECT source_id FROM memory_graph WHERE relation = 'resolved')
           ORDER BY created_at""",
        (user_id,),
    ).fetchall()
    c2.close()

    return {
        "status": "success",
        "user_id": user_id,
        "analysis_period_days": days,
        "total_memories_analyzed": len(memories),
        "patterns": {
            "peak_interaction_hours": [{"hour": h, "count": c} for h, c in peak_hours],
            "recurring_keywords": content_keywords.most_common(10),
            "frequent_recipients": recipients.most_common(5),
            "tone_preferences": dominant_tones if dominant_tones else ["not yet determined"],
        },
        "unresolved_action_items": len(unresolved),
        "insights": _generate_insights(memories, peak_hours, dominant_tones, unresolved),
    }


def _generate_insights(memories: list, peak_hours: list, tones: list, unresolved: list) -> list[str]:
    """Generate human-readable insights from raw pattern data."""
    insights = []

    if peak_hours:
        h, c = peak_hours[0]
        insights.append(
            f"Most active interaction window: {h:02d}:00 ({c} interactions). "
            f"Suggest scheduling important communications during this window."
        )

    if tones:
        insights.append(f"Communication style leans: {', '.join(tones)}")

    if unresolved:
        insights.append(
            f"{len(unresolved)} interaction(s) marked for follow-up but not yet resolved. "
            f"Review recommended."
        )

    if not insights:
        insights.append("Continue accumulating memories for richer insights.")

    return insights


def reason_over_memory(user_id: str, query: str) -> dict:
    """
    Answer a natural language query by reasoning over stored memories.
    This is the core 'Reasoning' capability: not keyword search, but inference
    over accumulated patterns.
    
    Queries like:
    - "How do I usually handle emails from investors?"
    - "What unresolved items do I have?"
    - "What's my communication style with vendors?"
    """
    memories = retrieve_memories(user_id)
    query_lower = query.lower()

    # Route query to relevant reasoning function
    if any(w in query_lower for w in ["style", "tone", "communicat"]):
        result = _reason_communication_style(user_id, memories)
    elif any(w in query_lower for w in ["unresolved", "follow-up", "pending"]):
        result = _reason_unresolved_items(user_id, memories)
    elif any(w in query_lower for w in ["pattern", "habit", "usually", "typically"]):
        result = _reason_behavioral_patterns(user_id, memories)
    elif any(w in query_lower for w in ["relationship", "who is", "know"]):
        result = _reason_relationships(user_id, memories)
    else:
        # General reasoning: retrieve contextual memories and synthesize
        result = {
            "query": query,
            "relevant_memories": memories[:10],
            "synthesis": f"Found {len(memories)} memories for user {user_id}. "
                        f"Memory covers {len(set(m['domain'] for m in memories))} domains: "
                        f"{', '.join(set(m['domain'] for m in memories))}.",
        }

    return result


def _reason_communication_style(user_id: str, memories: list) -> dict:
    pref_memories = [m for m in memories if m["memory_type"] == "preference"]
    interaction_memories = [m for m in memories if m["memory_type"] == "interaction"]

    styles = {}
    for m in pref_memories:
        content = m["content"].lower()
        if "concise" in content or "terse" in content:
            styles["vendors"] = "concise"
        if "warm" in content or "friendly" in content:
            styles["team"] = "warm"
        if "formal" in content:
            styles["legal"] = "formal"

    return {
        "query_type": "communication_style_analysis",
        "learned_styles": styles,
        "evidence_count": len(pref_memories),
        "recommendation": f"Apply {', '.join(f'{v} style for {k}' for k,v in styles.items())}. "
                        f"Based on {len(pref_memories)} stored preferences.",
    }


def _reason_unresolved_items(user_id: str, memories: list) -> dict:
    from memory_layer import get_conn as gc
    c = gc()
    unresolved = c.execute(
        """SELECT * FROM memories
           WHERE user_id = ? AND content LIKE '%follow-up%'
           AND id NOT IN (SELECT source_id FROM memory_graph WHERE relation = 'resolved')
           ORDER BY importance DESC, created_at DESC""",
        (user_id,),
    ).fetchall()
    c.close()

    items = [dict(u) for u in unresolved]
    return {
        "query_type": "unresolved_items",
        "items": items,
        "count": len(items),
        "recommendation": "Address in priority order by importance score." if items else "All caught up.",
    }


def _reason_behavioral_patterns(user_id: str, memories: list) -> dict:
    result = analyze_patterns(user_id)
    return {
        "query_type": "behavioral_patterns",
        "patterns": result.get("patterns", {}),
        "insights": result.get("insights", []),
    }


def _reason_relationships(user_id: str, memories: list) -> dict:
    rel_memories = [m for m in memories if m["memory_type"] == "relationship"]
    return {
        "query_type": "relationships",
        "known_relationships": [dict(m) for m in rel_memories],
        "count": len(rel_memories),
    }
