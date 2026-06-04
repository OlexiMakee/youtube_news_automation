"""
Extract Memory OS specific nodes and edges into memory_os/memory_graph.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_MEMORY = ROOT / "memory"
OS_MEMORY = ROOT / "memory_os" / "memory_graph"

def is_os_node(node_id: str) -> bool:
    prefixes = [
        "architecture.memory_os.",
        "memos.",
        "memory.compaction.",
        "workflow.control_plane.",
        "workflow.handoff.",
        "system.cli."
    ]
    for p in prefixes:
        if node_id.startswith(p):
            return True
    return False

def extract():
    OS_MEMORY.mkdir(parents=True, exist_ok=True)
    
    main_nodes_file = MAIN_MEMORY / "nodes.jsonl"
    main_edges_file = MAIN_MEMORY / "edges.jsonl"
    
    os_nodes_file = OS_MEMORY / "nodes.jsonl"
    os_edges_file = OS_MEMORY / "edges.jsonl"
    
    # Load all nodes
    all_nodes = []
    if main_nodes_file.exists():
        with open(main_nodes_file, "r") as f:
            for line in f:
                if line.strip():
                    all_nodes.append(json.loads(line))
                    
    main_nodes = []
    os_nodes = []
    os_ids = set()
    
    for n in all_nodes:
        if is_os_node(n["id"]):
            os_nodes.append(n)
            os_ids.add(n["id"])
        else:
            main_nodes.append(n)
            
    # Load all edges
    all_edges = []
    if main_edges_file.exists():
        with open(main_edges_file, "r") as f:
            for line in f:
                if line.strip():
                    all_edges.append(json.loads(line))
                    
    main_edges = []
    os_edges = []
    
    for e in all_edges:
        if e["source"] in os_ids or e["target"] in os_ids:
            # If any end of the edge is in OS, we consider it part of the OS memory graph
            os_edges.append(e)
        else:
            main_edges.append(e)
            
    # Write back
    with open(main_nodes_file, "w") as f:
        for n in main_nodes:
            f.write(json.dumps(n) + "\n")
            
    with open(main_edges_file, "w") as f:
        for e in main_edges:
            f.write(json.dumps(e) + "\n")
            
    # Write new
    with open(os_nodes_file, "w") as f:
        for n in os_nodes:
            f.write(json.dumps(n) + "\n")
            
    with open(os_edges_file, "w") as f:
        for e in os_edges:
            f.write(json.dumps(e) + "\n")

    print(f"Extracted {len(os_nodes)} nodes and {len(os_edges)} edges to memory_os/memory_graph.")

if __name__ == "__main__":
    extract()
