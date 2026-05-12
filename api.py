"""
PersonaVLM POC — FastAPI Server
Three endpoints demonstrating:
  POST /remember  → Store multimodal memories (Remembering)
  POST /reason    → Query temporal reasoning over memories (Reasoning)  
  POST /align     → Adapt output to user patterns (Response Alignment)
  
Plus demo endpoints for quick validation.
"""
from fastapi import FastAPI
from pydantic import BaseModel
from memory_layer import create_user, store_memory, retrieve_memories, init_db
from reasoning_layer import analyze_patterns, reason_over_memory
from alignment_layer import ResponseAligner, demo_alignment_scenarios

app = FastAPI(title="PersonaVLM POC", version="0.1.0")

# --- Request Models ---
class RememberRequest(BaseModel):
    user_id: str
    memory_type: str  # preference | interaction | relationship | pattern
    domain: str       # email | calendar | voice | etc.
    content: str
    importance: float = 0.5
    session_id: str = ""
    modality: str = "text"  # text | voice | image | video

class ReasonRequest(BaseModel):
    user_id: str
    query: str
    domain: str = ""
    days: int = 30

class AlignRequest(BaseModel):
    user_id: str
    draft: str
    recipient_context: str = ""


@app.on_event("startup")
def startup():
    init_db()


# ========== DEMO: Seed a user with realistic data ==========
@app.post("/demo/seed")
def demo_seed():
    """Create a demo user with realistic memories (April assistant scenario)."""
    user_id = "demo_user_001"
    create_user(user_id, "Alex Chen")

    # Preferences
    prefs = [
        ("preference", "email", "Use concise, terse tone with vendors — they only need the facts", 0.8),
        ("preference", "email", "Write warm, friendly emails to team members and co-founders", 0.7),
        ("preference", "email", "Use formal tone for legal and compliance communications", 0.6),
        ("preference", "email", "Sign off emails with 'Best' not 'Regards'", 0.9),
        ("preference", "calendar", "Always defer 1:1 meetings to Thursday mornings when possible", 0.7),
        ("preference", "calendar", "Internal meetings before external ones when resolving conflicts", 0.8),
    ]
    for mtype, domain, content, imp in prefs:
        store_memory(user_id, mtype, domain, content, imp)

    # Relationships
    rels = [
        ("relationship", "email", "Sarah K. is the VP of Engineering — direct manager. Always cc on engineering updates", 0.9),
        ("relationship", "email", "Rohit from Product team — handles API integrations. Prefers Slack over email", 0.7),
        ("relationship", "email", "Investor contact: Marcus at Sequoia — formal, quarterly updates expected", 0.8),
        ("relationship", "email", "Sarah from accounting — handles invoices, not to be confused with Sarah K.", 0.6),
    ]
    for mtype, domain, content, imp in rels:
        store_memory(user_id, mtype, domain, content, imp)

    # Interactions
    interactions = [
        ("interaction", "email", "Replied to Marcus investor thread. Mentioned follow-up needed by Friday", 0.5),
        ("interaction", "email", "Scheduled all-hands for Thursday 10am. Resolved calendar conflict with vendor call", 0.4),
        ("interaction", "voice", "Dictated reply to Rohit about API deadline — moved to Friday", 0.3),
        ("interaction", "email", "Sent pricing inquiry to AWS vendor. Follow-up needed on enterprise discount", 0.6),
        ("interaction", "calendar", "Deferred team sync from Tuesday to Thursday morning as per preference", 0.5),
    ]
    for mtype, domain, content, imp in interactions:
        store_memory(user_id, mtype, domain, content, imp)

    # Cross-link: investor thread follow-up
    from memory_layer import link_memories, get_conn
    conn = get_conn()
    follow_ups = conn.execute(
        "SELECT id FROM memories WHERE content LIKE '%follow-up%'",
    ).fetchall()
    conn.close()
    if len(follow_ups) >= 2:
        link_memories(follow_ups[0][0], follow_ups[1][0], "related_to", 0.7)

    return {
        "status": "seeded",
        "user_id": user_id,
        "total_memories_stored": len(prefs) + len(rels) + len(interactions),
        "message": "Demo user created with realistic April assistant memories",
    }


# ========== REMEMBER ==========
@app.post("/remember")
def remember(req: RememberRequest):
    """Store a memory (Capability 1: Remembering)."""
    mid = store_memory(
        req.user_id, req.memory_type, req.domain,
        req.content, req.importance, req.session_id,
    )
    return {
        "status": "stored",
        "memory_id": mid,
        "user_id": req.user_id,
        "memory_type": req.memory_type,
        "domain": req.domain,
        "modality": req.modality,
        "importance": req.importance,
    }


# ========== REASON ==========
@app.post("/reason")
def reason(req: ReasonRequest):
    """Query reasoning over accumulated memories (Capability 2: Reasoning)."""
    if req.query == "analyze_patterns":
        result = analyze_patterns(req.user_id, req.domain, req.days)
    else:
        result = reason_over_memory(req.user_id, req.query)
    return result


# ========== ALIGN ==========
@app.post("/align")
def align(req: AlignRequest):
    """Align draft response to user patterns (Capability 3: Response Alignment)."""
    aligner = ResponseAligner(req.user_id)
    result = aligner.align_email(req.draft, req.recipient_context)
    return result


# ========== QUERIES ==========
@app.get("/users")
def list_users():
    """List all users with memory counts."""
    from memory_layer import get_all_users, get_conn
    users = get_all_users()
    conn = get_conn()
    for u in users:
        count = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE user_id = ?",
            (u["user_id"],)
        ).fetchone()[0]
        u["memory_count"] = count
    conn.close()
    return {"users": users}


@app.get("/memories/{user_id}")
def get_memories(user_id: str, limit: int = 20, domain: str = "", memory_type: str = ""):
    """Retrieve memories for a user."""
    memories = retrieve_memories(user_id, domain, memory_type, limit)
    return {"user_id": user_id, "count": len(memories), "memories": memories}


# ========== DEMO: Run full pipeline ==========
@app.post("/demo/full_pipeline")
def demo_pipeline():
    """Run the complete Remember → Reason → Align pipeline."""
    # 1. REMEMBER: Show stored memories
    memories = retrieve_memories("demo_user_001", limit=5)
    remember_demo = {
        "capability": "Remembering",
        "description": "Persistent multimodal memory — stores compressed interaction representations",
        "sample_memories": [
            {"type": m["memory_type"], "content": m["content"], "importance": m["importance"]}
            for m in memories[:5]
        ],
        "total_stored": len(retrieve_memories("demo_user_001")),
    }

    # 2. REASON: Analyze patterns
    reason_demo = {
        "capability": "Reasoning",
        "description": "Temporal reasoning over accumulated memories to find patterns",
        "result": analyze_patterns("demo_user_001", "email"),
    }

    # 3. ALIGN: Align a response
    aligner = ResponseAligner("demo_user_001")
    demo_draft = (
        "Hi there,\n\n"
        "I hope this message finds you well. I am writing to inform you that "
        "we would like to discuss the pricing proposal you sent over last week. "
        "Additionally, we would appreciate it if you could provide us with more "
        "detailed breakdowns of each line item. Furthermore, please let us know "
        "if there are any volume discounts available.\n\n"
        "We look forward to hearing from you at your earliest convenience.\n\n"
        "Best regards,\n"
    )
    align_demo = {
        "capability": "Response Alignment",
        "description": "Adapt output to match individual user patterns",
        "result": aligner.align_email(demo_draft, "vendor"),
    }

    return {
        "pipeline": "Remember → Reason → Align",
        "remember": remember_demo,
        "reason": reason_demo,
        "align": align_demo,
    }


@app.get("/")
def root():
    return {
        "service": "PersonaVLM POC",
        "capabilities": ["Remember", "Reason", "Align"],
        "endpoints": {
            "POST /demo/seed": "Create demo user with realistic memories",
            "POST /demo/full_pipeline": "Run full Remember → Reason → Align pipeline",
            "POST /remember": "Store a memory",
            "POST /reason": "Query reasoning over memories",
            "POST /align": "Align draft to user patterns",
            "GET /users": "List all users",
            "GET /memories/{user_id}": "Get memories for a user",
        },
        "status": "running",
    }
