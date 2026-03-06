"""Test RAG queries against the knowledge base."""

from app.rag.knowledge_base import KnowledgeBase


def main():
    kb = KnowledgeBase()
    
    queries = [
        "How do I handle a late truck delivery?",
        "What are the SLA requirements for VIP customers?",
        "Can I substitute a product for an out-of-stock item?",
        "Too many orders came in at once, what should I do?",
    ]
    
    print("=" * 60)
    print("RAG QUERY TEST RESULTS")
    print("=" * 60)
    
    for q in queries:
        print(f"\n🔍 Query: {q}")
        print("-" * 50)
        results = kb.search_domain_knowledge(q, n_results=2)
        
        if not results:
            print("  No results found.")
            continue
            
        for i, r in enumerate(results):
            title = r.get("title", "N/A")
            dist = r.get("distance", 0)
            content = r.get("content", "")[:150]
            print(f"  [{i+1}] {title}")
            print(f"      Distance: {dist:.4f}")
            print(f"      Content: {content}...")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
