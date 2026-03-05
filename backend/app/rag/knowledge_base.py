"""
Knowledge Base - Chroma vector database for RAG.
Stores disruption history, decisions, and outcomes for semantic retrieval.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

# Lazy imports to handle missing dependencies gracefully
_chroma_client = None
_embedding_function = None


def _get_chroma():
    """Lazy load Chroma client."""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            from chromadb.config import Settings
            
            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
            _chroma_client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
        except ImportError:
            print("chromadb not installed, RAG features disabled")
            return None
    return _chroma_client


def _get_embedding_function():
    """Get embedding function for vector similarity."""
    global _embedding_function
    if _embedding_function is None:
        try:
            from chromadb.utils import embedding_functions
            
            # Use default embedding function (all-MiniLM-L6-v2)
            # Can be replaced with Bedrock embeddings for production
            _embedding_function = embedding_functions.DefaultEmbeddingFunction()
        except ImportError:
            print("sentence-transformers not installed, using default embeddings")
            return None
    return _embedding_function


class KnowledgeBase:
    """
    RAG Knowledge Base for supply chain disruption intelligence.
    
    Collections:
    - disruptions: Past disruption events with outcomes
    - decisions: Human decisions and overrides
    - scenarios: Recommended actions and their effectiveness
    - domain_knowledge: Supply chain best practices
    """
    
    COLLECTIONS = {
        "disruptions": "Past disruption events with causes, impacts, and resolutions",
        "decisions": "Human decisions, approvals, and overrides with rationale",
        "scenarios": "Generated scenarios and their effectiveness scores",
        "domain_knowledge": "Supply chain best practices and industry knowledge",
    }
    
    def __init__(self):
        self.client = _get_chroma()
        self.embed_fn = _get_embedding_function()
        self._collections = {}
        
        if self.client:
            self._init_collections()
    
    def _init_collections(self):
        """Initialize or get existing collections."""
        for name in self.COLLECTIONS:
            try:
                self._collections[name] = self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.embed_fn,
                    metadata={"description": self.COLLECTIONS[name]},
                )
            except Exception as e:
                print(f"Failed to create collection {name}: {e}")
    
    @property
    def available(self) -> bool:
        """Check if RAG is available."""
        return self.client is not None and len(self._collections) > 0
    
    def add_disruption(
        self,
        disruption_id: str,
        disruption_type: str,
        severity: int,
        description: str,
        impact_summary: str,
        resolution: str,
        outcome: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Store a disruption event for future retrieval.
        
        Args:
            disruption_id: Unique identifier
            disruption_type: Type (supplier_delay, demand_surge, etc.)
            severity: 1-5 severity scale
            description: What happened
            impact_summary: Orders/SKUs affected
            resolution: How it was resolved
            outcome: Results (cost, time, satisfaction)
            metadata: Additional structured data
        """
        if not self.available:
            return False
        
        try:
            collection = self._collections["disruptions"]
            
            # Create rich document for embedding
            document = f"""
            Disruption Type: {disruption_type}
            Severity: {severity}/5
            Description: {description}
            Impact: {impact_summary}
            Resolution: {resolution}
            Outcome: {outcome}
            """.strip()
            
            meta = {
                "disruption_type": disruption_type,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }
            
            collection.upsert(
                ids=[disruption_id],
                documents=[document],
                metadatas=[meta],
            )
            return True
            
        except Exception as e:
            print(f"Failed to add disruption: {e}")
            return False
    
    def add_decision(
        self,
        decision_id: str,
        pipeline_run_id: str,
        agent_name: str,
        decision_type: str,
        input_context: str,
        output_decision: str,
        human_action: str,
        rationale: str,
        effectiveness_score: Optional[float] = None,
    ) -> bool:
        """
        Store a decision record for learning from human overrides.
        
        Args:
            decision_id: Unique identifier
            pipeline_run_id: Associated pipeline run
            agent_name: Agent that made recommendation
            decision_type: approve/reject/override
            input_context: What was considered
            output_decision: What was decided
            human_action: Human's action (approved/rejected/modified)
            rationale: Why this decision was made
            effectiveness_score: Optional post-hoc effectiveness rating
        """
        if not self.available:
            return False
        
        try:
            collection = self._collections["decisions"]
            
            document = f"""
            Agent: {agent_name}
            Context: {input_context}
            AI Recommendation: {output_decision}
            Human Action: {human_action}
            Rationale: {rationale}
            """.strip()
            
            meta = {
                "pipeline_run_id": pipeline_run_id,
                "agent_name": agent_name,
                "decision_type": decision_type,
                "human_action": human_action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if effectiveness_score is not None:
                meta["effectiveness_score"] = effectiveness_score
            
            collection.upsert(
                ids=[decision_id],
                documents=[document],
                metadatas=[meta],
            )
            return True
            
        except Exception as e:
            print(f"Failed to add decision: {e}")
            return False
    
    def add_domain_knowledge(
        self,
        knowledge_id: str,
        category: str,
        title: str,
        content: str,
        source: str = "internal",
    ) -> bool:
        """
        Add supply chain domain knowledge for RAG context.
        
        Args:
            knowledge_id: Unique identifier
            category: Category (best_practice, regulation, policy, etc.)
            title: Knowledge item title
            content: Full content
            source: Source of knowledge
        """
        if not self.available:
            return False
        
        try:
            collection = self._collections["domain_knowledge"]
            
            document = f"{title}\n\n{content}"
            
            meta = {
                "category": category,
                "title": title,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            collection.upsert(
                ids=[knowledge_id],
                documents=[document],
                metadatas=[meta],
            )
            return True
            
        except Exception as e:
            print(f"Failed to add domain knowledge: {e}")
            return False
    
    def search_similar_disruptions(
        self,
        query: str,
        n_results: int = 5,
        disruption_type: Optional[str] = None,
        min_severity: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Find similar past disruptions for context.
        
        Args:
            query: Natural language description of current situation
            n_results: Number of results to return
            disruption_type: Filter by type
            min_severity: Minimum severity level
            
        Returns:
            List of similar disruption records with similarity scores
        """
        if not self.available:
            return []
        
        try:
            collection = self._collections["disruptions"]
            
            where_filter = None
            if disruption_type or min_severity:
                conditions = []
                if disruption_type:
                    conditions.append({"disruption_type": disruption_type})
                if min_severity:
                    conditions.append({"severity": {"$gte": min_severity}})
                
                if len(conditions) == 1:
                    where_filter = conditions[0]
                else:
                    where_filter = {"$and": conditions}
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
            
            return self._format_results(results)
            
        except Exception as e:
            print(f"Failed to search disruptions: {e}")
            return []
    
    def search_relevant_decisions(
        self,
        query: str,
        n_results: int = 5,
        agent_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Find relevant past decisions for learning.
        
        Args:
            query: Current decision context
            n_results: Number of results
            agent_name: Filter by agent
            
        Returns:
            List of relevant decision records
        """
        if not self.available:
            return []
        
        try:
            collection = self._collections["decisions"]
            
            where_filter = None
            if agent_name:
                where_filter = {"agent_name": agent_name}
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
            
            return self._format_results(results)
            
        except Exception as e:
            print(f"Failed to search decisions: {e}")
            return []
    
    def search_domain_knowledge(
        self,
        query: str,
        n_results: int = 3,
        category: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Search domain knowledge base.
        
        Args:
            query: Topic or question
            n_results: Number of results
            category: Filter by category
            
        Returns:
            List of relevant knowledge items
        """
        if not self.available:
            return []
        
        try:
            collection = self._collections["domain_knowledge"]
            
            where_filter = None
            if category:
                where_filter = {"category": category}
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
            
            return self._format_results(results)
            
        except Exception as e:
            print(f"Failed to search domain knowledge: {e}")
            return []
    
    def get_context_for_agent(
        self,
        agent_name: str,
        current_situation: str,
        disruption_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get comprehensive RAG context for an agent's decision.
        
        Args:
            agent_name: Name of the requesting agent
            current_situation: Description of current situation
            disruption_type: Type of disruption being handled
            
        Returns:
            Combined context from all knowledge sources
        """
        context = {
            "similar_disruptions": [],
            "relevant_decisions": [],
            "domain_knowledge": [],
            "rag_available": self.available,
        }
        
        if not self.available:
            return context
        
        # Get similar past disruptions
        context["similar_disruptions"] = self.search_similar_disruptions(
            query=current_situation,
            n_results=3,
            disruption_type=disruption_type,
        )
        
        # Get relevant past decisions by this agent
        context["relevant_decisions"] = self.search_relevant_decisions(
            query=current_situation,
            n_results=3,
            agent_name=agent_name,
        )
        
        # Get relevant domain knowledge
        context["domain_knowledge"] = self.search_domain_knowledge(
            query=current_situation,
            n_results=2,
        )
        
        return context
    
    def _format_results(self, results: dict) -> list[dict[str, Any]]:
        """Format Chroma results into clean list of dicts."""
        formatted = []
        
        if not results or not results.get("ids"):
            return formatted
        
        ids = results["ids"][0] if results["ids"] else []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        for i, doc_id in enumerate(ids):
            formatted.append({
                "id": doc_id,
                "content": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": 1 - (distances[i] if i < len(distances) else 0),
            })
        
        return formatted
    
    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {
            "available": self.available,
            "collections": {},
        }
        
        if not self.available:
            return stats
        
        for name, collection in self._collections.items():
            try:
                stats["collections"][name] = {
                    "count": collection.count(),
                    "description": self.COLLECTIONS.get(name, ""),
                }
            except Exception:
                stats["collections"][name] = {"count": 0, "error": True}
        
        return stats


# Singleton instance
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """Get singleton knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
