"""Test graph flow with detailed logging."""
import uuid
from app.agents.graph import build_graph
from app.mcp.tools import create_pipeline_run

# Build graph
graph = build_graph()

# Create pipeline run
pipeline_run_id = str(uuid.uuid4())
disruption_id = '3cb526d7-434a-130e-8c6e-a6ad2fe938e4'

create_pipeline_run.invoke({
    'pipeline_run_id': pipeline_run_id,
    'disruption_id': disruption_id,
})

# Initial state
state = {
    'pipeline_run_id': pipeline_run_id,
    'disruption_id': disruption_id,
    'step': 'start'
}

print("Starting graph execution...")
print(f"Initial step: {state['step']}\n")

# Execute with streaming to see each step
for i, s in enumerate(graph.stream(state, {"recursion_limit": 100})):
    print(f"Step {i+1}:")
    for key, value in s.items():
        if key == 'step':
            print(f"  Node: {key} -> {value}")
        elif isinstance(value, dict) and 'step' in value:
            print(f"  Node: {key}")
            print(f"    Next step: {value.get('step')}")
            print(f"    Keys: {list(value.keys())}")
    print()

print("\\nFinal execution complete")
