"""
LangGraph graph builder for multi-agent pipeline.

Uses a Router + Finalizer pattern where:
- Router: LLM-driven routing with deterministic guardrails
- Finalizer: Compile recommendations and complete pipeline
- 4 domain agents: Signal Intake, Constraint Builder, Scenario Generator, Tradeoff Scoring
"""
from langgraph.graph import StateGraph, END

from app.agents.constraint_builder_agent import constraint_builder_node
from app.agents.finalizer_agent import finalizer_node
from app.agents.router_agent import router_node, route_router
from app.agents.scenario_generator_agent import scenario_generator_node
from app.agents.signal_intake_agent import signal_intake_node
from app.agents.state import PipelineState
from app.agents.tradeoff_scoring_agent import tradeoff_scoring_node


def build_graph() -> StateGraph:
    """
    Build the LangGraph state graph with Router + Finalizer pattern.
    
    Architecture:
    - Entry: Router (decides first step)
    - Domain agents return to Router
    - Router decides next step or routes to Finalizer
    - Finalizer compiles results and ends
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(PipelineState)
    
    # Add nodes - 6 single-purpose agents
    workflow.add_node("router", router_node)
    workflow.add_node("finalizer", finalizer_node)
    workflow.add_node("signal_intake", signal_intake_node)
    workflow.add_node("constraint_builder", constraint_builder_node)
    workflow.add_node("scenario_generator", scenario_generator_node)
    workflow.add_node("tradeoff_scoring", tradeoff_scoring_node)
    
    # Set entry point to router
    workflow.set_entry_point("router")
    
    # Add conditional edges from router to agents or finalizer
    workflow.add_conditional_edges(
        "router",
        route_router,
        {
            "signal_intake": "signal_intake",
            "constraint_builder": "constraint_builder",
            "scenario_generator": "scenario_generator",
            "tradeoff_scoring": "tradeoff_scoring",
            "finalizer": "finalizer",
            "END": END,
        },
    )
    
    # All domain agents return to router for next decision
    workflow.add_edge("signal_intake", "router")
    workflow.add_edge("constraint_builder", "router")
    workflow.add_edge("scenario_generator", "router")
    workflow.add_edge("tradeoff_scoring", "router")
    
    # Finalizer ends the pipeline
    workflow.add_edge("finalizer", END)
    
    # Compile and return
    return workflow.compile()
