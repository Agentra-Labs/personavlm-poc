"""
PersonaVLM POC — Full Pipeline Test
Runs the complete Remember → Reason → Align pipeline and prints results.
This demonstrates all 3 capabilities in action.
"""
import httpx
import json
import sys

BASE = "http://localhost:8090"

def pretty(d, indent=0):
    """Pretty print JSON-like dict."""
    lines = []
    if isinstance(d, dict):
        for k, v in d.items():
            prefix = "  " * indent
            lines.append(f"{prefix}{k}:")
            lines.extend(pretty(v, indent + 1))
    elif isinstance(d, list):
        for item in d:
            lines.extend(pretty(item, indent))
    else:
        return ["  " * indent + str(d)[:200]]
    return lines


def main():
    print("=" * 60)
    print("  PersonaVLM POC — Full Pipeline Demo")
    print("=" * 60)
    print()

    # Check server is running
    try:
        r = httpx.get(f"{BASE}/", timeout=5)
        if r.status_code != 200:
            print(f"ERROR: Server returned {r.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: Cannot reach server at {BASE} — is it running?")
        print(f"  Start with: cd ~/src/personavlm-poc && uv run uvicorn api:app --port 8090")
        sys.exit(1)

    # Step 1: SEED
    print("① SEEDING demo user (April assistant scenario)...")
    r = httpx.post(f"{BASE}/demo/seed", timeout=10)
    seed = r.json()
    print(f"  User: {seed['user_id']} — {seed['message']}")
    print(f"  Total memories stored: {seed['total_memories_stored']}")
    print()

    # Step 2: REMEMBER
    print("② REMEMBER — Stored memories")
    r = httpx.get(f"{BASE}/memories/demo_user_001?limit=5", timeout=10)
    mems = r.json()
    for m in mems["memories"]:
        print(f"  [{m['memory_type'].upper():15s}] ({m['importance']}) {m['content'][:80]}...")
    print()

    # Step 3: REASON
    print("③ REASON — Pattern analysis over accumulated memories")
    r = httpx.post(f"{BASE}/reason", json={
        "user_id": "demo_user_001",
        "query": "analyze_patterns",
        "domain": "email",
        "days": 30,
    }, timeout=10)
    reason = r.json()
    patterns = reason.get("patterns", {})
    print(f"  Peak hours: {patterns.get('peak_interaction_hours', [])}")
    print(f"  Tone preferences: {patterns.get('tone_preferences', [])}")
    print(f"  Recurring keywords: {patterns.get('recurring_keywords', [])[:5]}")
    print(f"  Unresolved items: {reason.get('unresolved_action_items', 0)}")
    for insight in reason.get("insights", []):
        print(f"  ↳ {insight}")
    print()

    # Step 4: REASON (Natural language query)
    print("④ REASON — Natural language query: 'What is my communication style?'")
    r = httpx.post(f"{BASE}/reason", json={
        "user_id": "demo_user_001",
        "query": "What is my communication style?",
    }, timeout=10)
    style_reason = r.json()
    print(f"  Query type: {style_reason.get('query_type')}")
    print(f"  Learned style: {style_reason.get('learned_styles', {})}")
    print(f"  Recommendation: {style_reason.get('recommendation', '')[:150]}")
    print()

    # Step 5: ALIGN
    print("⑤ ALIGN — Response alignment on a draft email")
    draft = (
        "Hi there,\n\n"
        "I hope this message finds you well. I am writing to inform you that "
        "we would like to discuss the pricing proposal you sent over last week. "
        "Additionally, we would appreciate it if you could provide us with more "
        "detailed breakdowns of each line item. Furthermore, please let us know "
        "if there are any volume discounts available.\n\n"
        "We look forward to hearing from you at your earliest convenience.\n\n"
        "Best regards,\n"
    )
    r = httpx.post(f"{BASE}/align", json={
        "user_id": "demo_user_001",
        "draft": draft,
        "recipient_context": "vendor",
    }, timeout=10)
    align_result = r.json()
    print(f"  Applied preferences: {json.dumps(align_result['applied_preferences'], indent=4)}")
    print(f"  Changes: {align_result['changes_made']}")
    print(f"  Original length: {len(align_result['original'].split())} words")
    print(f"  Aligned length: {len(align_result['aligned'].split())} words")
    print()
    print("  ─── Aligned Email ───")
    print(align_result['aligned'])
    print("  ─── End Aligned ───")
    print()

    # Step 6: FULL PIPELINE
    print("⑥ FULL PIPELINE — Remember → Reason → Align summary")
    r = httpx.post(f"{BASE}/demo/full_pipeline", timeout=10)
    pipeline = r.json()
    print(f"  Pipeline: {pipeline['pipeline']}")
    print(f"  Remember: {pipeline['remember']['total_stored']} memories stored")
    print(f"  Reason: {len(pipeline['reason']['result'].get('insights', []))} insights generated")
    print(f"  Align: {len(pipeline['align']['result']['changes_made'])} adaptations made")
    print()

    print("=" * 60)
    print("  Pipeline complete. All 3 PersonaVLM capabilities demonstrated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
