"""
RAG Knowledge Base API routes.
Provides endpoints for managing and querying the knowledge base.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user
from app.db.models import User
from app.rag import get_knowledge_base

router = APIRouter(prefix="/api/rag", tags=["rag"])


# Request/Response Models
class DisruptionKnowledge(BaseModel):
    """Add a disruption record to knowledge base."""
    disruption_id: str
    disruption_type: str
    severity: int = Field(ge=1, le=5)
    description: str
    impact_summary: str
    resolution: str
    outcome: str
    metadata: Optional[dict] = None


class DecisionKnowledge(BaseModel):
    """Add a decision record to knowledge base."""
    decision_id: str
    pipeline_run_id: str
    agent_name: str
    decision_type: str
    input_context: str
    output_decision: str
    human_action: str
    rationale: str
    effectiveness_score: Optional[float] = None


class DomainKnowledge(BaseModel):
    """Add domain knowledge to knowledge base."""
    knowledge_id: str
    category: str
    title: str
    content: str
    source: str = "internal"


class SearchQuery(BaseModel):
    """Search query parameters."""
    query: str
    n_results: int = Field(default=5, ge=1, le=20)
    filters: Optional[dict] = None


class KBStatsResponse(BaseModel):
    """Knowledge base statistics."""
    available: bool
    collections: dict


# Routes
@router.get("/stats", response_model=KBStatsResponse)
async def get_kb_stats(current_user: User = Depends(get_current_user)):
    """Get knowledge base statistics."""
    kb = get_knowledge_base()
    return kb.get_stats()


@router.get("/health")
async def rag_health():
    """Check RAG system health."""
    kb = get_knowledge_base()
    return {
        "status": "healthy" if kb.available else "unavailable",
        "available": kb.available,
        "message": "Chroma vector DB ready" if kb.available else "Chroma not configured",
    }


@router.post("/disruptions")
async def add_disruption_knowledge(
    data: DisruptionKnowledge,
    current_user: User = Depends(get_current_user),
):
    """Add a disruption record to the knowledge base for future reference."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    success = kb.add_disruption(
        disruption_id=data.disruption_id,
        disruption_type=data.disruption_type,
        severity=data.severity,
        description=data.description,
        impact_summary=data.impact_summary,
        resolution=data.resolution,
        outcome=data.outcome,
        metadata=data.metadata,
    )
    
    if success:
        return {"status": "added", "disruption_id": data.disruption_id}
    raise HTTPException(status_code=500, detail="Failed to add disruption")


@router.post("/decisions")
async def add_decision_knowledge(
    data: DecisionKnowledge,
    current_user: User = Depends(get_current_user),
):
    """Add a decision record for learning from human overrides."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    success = kb.add_decision(
        decision_id=data.decision_id,
        pipeline_run_id=data.pipeline_run_id,
        agent_name=data.agent_name,
        decision_type=data.decision_type,
        input_context=data.input_context,
        output_decision=data.output_decision,
        human_action=data.human_action,
        rationale=data.rationale,
        effectiveness_score=data.effectiveness_score,
    )
    
    if success:
        return {"status": "added", "decision_id": data.decision_id}
    raise HTTPException(status_code=500, detail="Failed to add decision")


@router.post("/domain-knowledge")
async def add_domain_knowledge_route(
    data: DomainKnowledge,
    current_user: User = Depends(get_current_user),
):
    """Add supply chain domain knowledge."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    success = kb.add_domain_knowledge(
        knowledge_id=data.knowledge_id,
        category=data.category,
        title=data.title,
        content=data.content,
        source=data.source,
    )
    
    if success:
        return {"status": "added", "knowledge_id": data.knowledge_id}
    raise HTTPException(status_code=500, detail="Failed to add knowledge")


@router.post("/search/disruptions")
async def search_disruptions(
    query: SearchQuery,
    current_user: User = Depends(get_current_user),
):
    """Search for similar past disruptions."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    disruption_type = query.filters.get("disruption_type") if query.filters else None
    min_severity = query.filters.get("min_severity") if query.filters else None
    
    results = kb.search_similar_disruptions(
        query=query.query,
        n_results=query.n_results,
        disruption_type=disruption_type,
        min_severity=min_severity,
    )
    
    return {"results": results, "count": len(results)}


@router.post("/search/decisions")
async def search_decisions(
    query: SearchQuery,
    current_user: User = Depends(get_current_user),
):
    """Search for relevant past decisions."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    agent_name = query.filters.get("agent_name") if query.filters else None
    
    results = kb.search_relevant_decisions(
        query=query.query,
        n_results=query.n_results,
        agent_name=agent_name,
    )
    
    return {"results": results, "count": len(results)}


@router.post("/search/knowledge")
async def search_knowledge(
    query: SearchQuery,
    current_user: User = Depends(get_current_user),
):
    """Search domain knowledge base."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    category = query.filters.get("category") if query.filters else None
    
    results = kb.search_domain_knowledge(
        query=query.query,
        n_results=query.n_results,
        category=category,
    )
    
    return {"results": results, "count": len(results)}


@router.post("/context/{agent_name}")
async def get_agent_context(
    agent_name: str,
    situation: str,
    disruption_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive RAG context for an agent's decision."""
    kb = get_knowledge_base()
    
    context = kb.get_context_for_agent(
        agent_name=agent_name,
        current_situation=situation,
        disruption_type=disruption_type,
    )
    
    return context


@router.post("/seed-knowledge")
async def seed_knowledge(current_user: User = Depends(get_current_user)):
    """Seed knowledge base with example supply chain best practices."""
    kb = get_knowledge_base()
    
    if not kb.available:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    # Seed with supply chain best practices
    knowledge_items = [
        {
            "knowledge_id": "bp_001",
            "category": "best_practice",
            "title": "Supplier Delay Response Protocol",
            "content": """When facing supplier delays:
1. Assess impact on customer SLAs immediately
2. Check alternative suppliers and existing inventory
3. Consider expedited shipping for VIP orders
4. Communicate proactively with affected customers
5. Document root cause for future prevention
Cost threshold for manager approval: >$5,000 total impact""",
            "source": "internal_handbook",
        },
        {
            "knowledge_id": "bp_002",
            "category": "best_practice",
            "title": "Demand Surge Management",
            "content": """Handling unexpected demand spikes:
1. Prioritize by customer tier (VIP > Premium > Standard)
2. Activate safety stock at regional DCs
3. Consider partial fulfillment with backorder
4. Temporary expedited supplier orders
5. Update demand forecasting models
SLA risk tolerance: 10% for standard, 2% for VIP orders""",
            "source": "internal_handbook",
        },
        {
            "knowledge_id": "bp_003",
            "category": "policy",
            "title": "Product Substitution Rules",
            "content": """Substitution approval guidelines:
- Same category, equal or higher quality: Auto-approve
- Lower price point: Requires customer notification
- Different brand: Requires explicit approval
- Medical/safety items: Never substitute without pharmacy review
- Penalty costs apply: Track substitution_penalty_pct""",
            "source": "policy_document",
        },
        {
            "knowledge_id": "bp_004",
            "category": "regulation",
            "title": "SLA Compliance Requirements",
            "content": """Service Level Agreement standards:
- VIP orders: 99% on-time delivery required
- Expedited: 95% on-time, 2-day shipping
- Standard: 90% on-time, 5-7 day shipping
Breach penalties: $50 per day for VIP, $20 for expedited
Proactive communication reduces penalties by 50%""",
            "source": "legal_compliance",
        },
    ]
    
    added = 0
    for item in knowledge_items:
        if kb.add_domain_knowledge(**item):
            added += 1
    
    return {
        "status": "seeded",
        "items_added": added,
        "total_items": len(knowledge_items),
    }
