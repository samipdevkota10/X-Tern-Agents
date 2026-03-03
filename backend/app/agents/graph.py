"""
LangGraph graph builder for multi-agent pipeline.
"""
from langgraph.graph import StateGraph, END

from app.agents.constraint_builder_agent import constraint_builder_node
from app.agents.scenario_generator_agent import scenario_generator_node
from app.agents.signal_intake_agent import signal_intake_node
from app.agents.state import PipelineState
from app.agents.supervisor import route_supervisor, supervisor_node
from app.agents.tradeoff_scoring_agent import tradeoff_scoring_node


def build_graph() -> StateGraph:
    """
    Build the LangGraph state graph with supervisor pattern.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    workflow = StateGraph(PipelineState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("signal_intake", signal_intake_node)
    workflow.add_node("constraint_builder", constraint_builder_node)
    workflow.add_node("scenario_generator", scenario_generator_node)
    workflow.add_node("tradeoff_scoring", tradeoff_scoring_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "signal_intake": "signal_intake",
            "constraint_builder": "constraint_builder",
            "scenario_generator": "scenario_generator",
            "tradeoff_scoring": "tradeoff_scoring",
            "END": END,
        },
    )
    
    # Add edges back to supervisor from each agent
    workflow.add_edge("signal_intake", "supervisor")
    workflow.add_edge("constraint_builder", "supervisor")
    workflow.add_edge("scenario_generator", "supervisor")
    workflow.add_edge("tradeoff_scoring", "supervisor")
    
    # Compile and return
    return workflow.compile()
