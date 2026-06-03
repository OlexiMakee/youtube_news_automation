import json
from pathlib import Path
from typing import List, Dict, Set, Any, Optional
from app.services.memory_os.interfaces import IMemosConfig, IMemoryStorage
from app.services.memory_os.config import MemosConfig
from app.services.memory_os.storage import FileSystemMemoryStorage

class MemorySearcher:
    """Queries Memory OS nodes, codebase symbols, and traverses graph relations."""

    def __init__(self, config: Optional[IMemosConfig] = None, storage: Optional[IMemoryStorage] = None):
        self.config = config or MemosConfig()
        self.storage = storage or FileSystemMemoryStorage()

    def _load_nodes(self) -> List[Dict[str, Any]]:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        return self.storage.load_jsonl(nodes_file)

    def _load_edges(self) -> List[Dict[str, Any]]:
        edges_file = self.config.memory_dir / "edges.jsonl"
        return self.storage.load_jsonl(edges_file)

    def _load_snapshot(self) -> Dict[str, Any]:
        snapshot_file = self.config.snapshot_file
        return self.storage.load_json(snapshot_file)

    def traverse_graph(self, start_node_ids: Set[str], depth: int, 
                       nodes_by_id: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> Set[str]:
        visited = set(start_node_ids)
        current_level = set(start_node_ids)

        for _ in range(depth):
            next_level = set()
            for node_id in current_level:
                node = nodes_by_id.get(node_id)
                if node and "related_nodes" in node:
                    for rel in node["related_nodes"]:
                        if rel not in visited:
                            next_level.add(rel)
                            visited.add(rel)

                for edge in edges:
                    if edge["source"] == node_id and edge["target"] not in visited:
                        next_level.add(edge["target"])
                        visited.add(edge["target"])
                    elif edge["target"] == node_id and edge["source"] not in visited:
                        next_level.add(edge["source"])
                        visited.add(edge["source"])

            current_level = next_level
            if not current_level:
                break

        return visited

    def traverse_dependencies(self, start_files: Set[str], depth: int, 
                              items_by_file: Dict[str, Dict[str, Any]]) -> Set[str]:
        visited = set(start_files)
        current_level = set(start_files)

        for _ in range(depth):
            next_level = set()
            for filepath in current_level:
                item = items_by_file.get(filepath)
                if not item:
                    continue
                dependencies = item.get("meta", {}).get("dependencies", [])
                for dep in dependencies:
                    dep_lower = dep.lower()
                    for other_file in items_by_file:
                        other_name = Path(other_file).stem.lower()
                        other_mod = other_file.replace(".py", "").replace("/", ".").lower()
                        if (dep_lower == other_name or 
                            dep_lower in other_file.lower().split("/") or 
                            dep_lower == other_mod or 
                            other_mod.endswith("." + dep_lower)):
                            if other_file not in visited:
                                next_level.add(other_file)
                                visited.add(other_file)
            current_level = next_level
            if not current_level:
                break
        return visited

    def search_memory(self, query: str, depth: int = 1) -> List[Dict[str, Any]]:
        nodes = self._load_nodes()
        edges = self._load_edges()
        snapshot = self._load_snapshot()

        query_lower = query.strip().lower()

        # 1. Search memory nodes
        nodes_by_id = {node["id"]: node for node in nodes}
        matched_node_ids = set()
        for node in nodes:
            if (query_lower in node["id"].lower() or 
                query_lower in node["summary"].lower() or 
                any(query_lower in ev.lower() for ev in node["evidence"]) or
                query_lower in node["type"].lower()):
                matched_node_ids.add(node["id"])

        all_matched_node_ids = self.traverse_graph(matched_node_ids, depth, nodes_by_id, edges)
        matched_nodes = [nodes_by_id[nid] for nid in all_matched_node_ids if nid in nodes_by_id]

        # 2. Search codebase items
        items = snapshot.get("items", [])
        items_by_file = {item["meta"]["file"]: item for item in items}

        exact_files = set()
        lexical_files = set()

        for item in items:
            meta = item.get("meta", {})
            filepath = meta.get("file", "")
            filepath_lower = filepath.lower()

            if query_lower == filepath_lower or query_lower == Path(filepath).name.lower() or query_lower == Path(filepath).stem.lower():
                exact_files.add(filepath)
                continue

            matched_class = False
            for cls_info in meta.get("classes", []):
                cls_name = cls_info.split(":")[0].lower()
                if query_lower == cls_name or query_lower in cls_name:
                    exact_files.add(filepath)
                    matched_class = True
                    break
            if matched_class:
                continue

            matched_func = False
            for func_info in meta.get("functions", []):
                func_name = func_info.split(":")[0].lower()
                if query_lower == func_name or query_lower in func_name:
                    exact_files.add(filepath)
                    matched_func = True
                    break
            if matched_func:
                continue

            matched_route = False
            for route_info in meta.get("routes", []):
                route_path = route_info.split(" ")[0].lower()
                if query_lower == route_path or query_lower in route_path:
                    exact_files.add(filepath)
                    matched_route = True
                    break
            if matched_route:
                continue

            matched_heading = False
            for heading in meta.get("headings", []):
                if query_lower == heading.lower() or query_lower in heading.lower():
                    exact_files.add(filepath)
                    matched_heading = True
                    break
            if matched_heading:
                continue

            matched_dep = False
            for dep in meta.get("dependencies", []):
                if query_lower == dep.lower():
                    exact_files.add(filepath)
                    matched_dep = True
                    break
            if matched_dep:
                continue

            if query_lower in item.get("vector_text", "").lower():
                lexical_files.add(filepath)

        traversed_files = self.traverse_dependencies(exact_files, depth, items_by_file)

        def to_node_shape(fp: str, rank: int, match_type: str) -> Dict[str, Any]:
            item = items_by_file[fp]
            meta = item["meta"]
            return {
                "id": f"file:{fp}",
                "type": "code_file",
                "summary": item.get("vector_text", ""),
                "evidence": [fp],
                "status": "verified",
                "freshness": snapshot.get("generated_at", ""),
                "trust": "verified",
                "related_nodes": [],
                "classes": meta.get("classes", []),
                "functions": meta.get("functions", []),
                "routes": meta.get("routes", []),
                "dependencies": meta.get("dependencies", []),
                "headings": meta.get("headings", []),
                "match_type": match_type,
                "rank": rank,
                "layer": meta.get("layer", "")
            }

        results_code = []

        for f in exact_files:
            results_code.append(to_node_shape(f, 1, "exact_symbol"))

        for f in traversed_files - exact_files:
            results_code.append(to_node_shape(f, 2, "code_dependency"))

        for f in lexical_files - traversed_files - exact_files:
            results_code.append(to_node_shape(f, 3, "lexical"))

        return matched_nodes + results_code
