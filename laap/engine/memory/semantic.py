"""LAAP Memory Engine — Semantic Memory (语义记忆)
Store concepts, knowledge, and relations as a semantic network/graph
"""
from __future__ import annotations
import time, json, uuid, logging, threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("engine.memory.semantic")

class RelationType(str, Enum):
    IS_A = "is_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    RELATED_TO = "related_to"
    OPPOSITE_OF = "opposite_of"
    PREREQUISITE = "prerequisite"
    DERIVED_FROM = "derived_from"
    USED_FOR = "used_for"
    LOCATED_IN = "located_in"
    CREATED_BY = "created_by"
    SIMILAR_TO = "similar_to"
    INSTANCE_OF = "instance_of"
    PROPERTY_OF = "property_of"

@dataclass
class ConceptNode:
    id: str = field(default_factory=lambda: f"cpt_{uuid.uuid4().hex[:10]}")
    name: str = ""
    description: str = ""
    attributes: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    confidence: float = 0.5
    source: str = ""

@dataclass
class Relation:
    source_id: str = ""
    target_id: str = ""
    type: RelationType = RelationType.RELATED_TO
    weight: float = 1.0
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

class ConceptGraph:
    def __init__(self):
        self._nodes: Dict[str, ConceptNode] = {}
        self._relations: Dict[str, List[Relation]] = defaultdict(list)
        self._inverse_relations: Dict[str, List[Relation]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def add_node(self, node: ConceptNode) -> str:
        with self._lock:
            self._nodes[node.id] = node
        return node.id
    
    def add_relation(self, source_id: str, target_id: str, rel_type: RelationType, weight: float = 1.0, confidence: float = 0.5):
        rel = Relation(source_id=source_id, target_id=target_id, type=rel_type, weight=weight, confidence=confidence)
        with self._lock:
            self._relations[source_id].append(rel)
            self._inverse_relations[target_id].append(rel)
    
    def get_relations(self, node_id: str, rel_type: Optional[RelationType] = None) -> List[Relation]:
        rels = self._relations.get(node_id, [])
        if rel_type:
            rels = [r for r in rels if r.type == rel_type]
        return rels
    
    def get_related_nodes(self, node_id: str, rel_type: Optional[RelationType] = None, depth: int = 1) -> Set[str]:
        result = set()
        queue = [(node_id, 0)]
        visited = {node_id}
        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue
            rels = self.get_relations(current, rel_type)
            for r in rels:
                if r.target_id not in visited:
                    visited.add(r.target_id)
                    result.add(r.target_id)
                    queue.append((r.target_id, d + 1))
            inv_rels = self._inverse_relations.get(current, [])
            if rel_type:
                inv_rels = [r for r in inv_rels if r.type == rel_type]
            for r in inv_rels:
                if r.source_id not in visited:
                    visited.add(r.source_id)
                    result.add(r.source_id)
                    queue.append((r.source_id, d + 1))
        return result
    
    def find_path(self, from_id: str, to_id: str, max_depth: int = 5) -> List[str]:
        queue = [[from_id]]
        visited = {from_id}
        while queue:
            path = queue.pop(0)
            current = path[-1]
            if current == to_id:
                return path
            if len(path) >= max_depth:
                continue
            rels = self._relations.get(current, [])
            for r in rels:
                if r.target_id not in visited:
                    visited.add(r.target_id)
                    queue.append(path + [r.target_id])
            for r in self._inverse_relations.get(current, []):
                if r.source_id not in visited:
                    visited.add(r.source_id)
                    queue.append(path + [r.source_id])
        return []

class SemanticMemory:
    def __init__(self):
        self.graph = ConceptGraph()
        self._name_index: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def store_concept(self, name: str, description: str = "", attributes: Dict = None, source: str = "") -> str:
        with self._lock:
            node = ConceptNode(name=name, description=description, attributes=attributes or {}, source=source)
            self.graph.add_node(node)
            self._name_index[name.lower()] = node.id
        return node.id
    
    def relate(self, source_name: str, target_name: str, rel_type: RelationType, weight: float = 1.0):
        src = self._name_index.get(source_name.lower())
        tgt = self._name_index.get(target_name.lower())
        if src and tgt:
            self.graph.add_relation(src, tgt, rel_type, weight)
    
    def query(self, concept_name: str) -> Optional[ConceptNode]:
        """查询概念 — 支持精确匹配和模糊匹配"""
        cid = self._name_index.get(concept_name.lower())
        if cid:
            node = self.graph._nodes.get(cid)
            if node:
                node.access_count += 1
                return node
        # 模糊匹配
        query_lower = concept_name.lower()
        for name, cid in self._name_index.items():
            if query_lower in name or name in query_lower:
                node = self.graph._nodes.get(cid)
                if node:
                    node.access_count += 1
                    return node
        return None
    
    def get_context(self, concept_name: str, depth: int = 1) -> Dict:
        cid = self._name_index.get(concept_name.lower())
        if not cid:
            return {"concept": concept_name, "found": False}
        node = self.graph._nodes.get(cid)
        related_ids = self.graph.get_related_nodes(cid, depth=depth)
        related = []
        for rid in related_ids:
            rn = self.graph._nodes.get(rid)
            if rn:
                rels = self.graph.get_relations(cid)
                rtypes = [r.type.value for r in rels if r.target_id == rid]
                related.append({"name": rn.name, "relations": rtypes})
        return {
            "concept": concept_name,
            "found": True,
            "description": node.description if node else "",
            "attributes": node.attributes if node else {},
            "related_concepts": related,
        }
    
    def infer_relation(self, from_name: str, to_name: str) -> Optional[str]:
        src = self._name_index.get(from_name.lower())
        tgt = self._name_index.get(to_name.lower())
        if src and tgt:
            path = self.graph.find_path(src, tgt)
            if path:
                names = []
                for nid in path:
                    node = self.graph._nodes.get(nid)
                    names.append(node.name if node else nid)
                return " -> ".join(names)
        return None

class KnowledgeExtractor:
    def extract(self, text: str) -> List[Dict]:
        import re
        triples = []
        patterns = [
            (r"(.+?) is (?:a|an) (.+?)[\.!?]", RelationType.IS_A),
            (r"(.+?) (?:contains|has|includes) (.+?)[\.!?]", RelationType.PART_OF),
            (r"(.+?) (?:causes|leads to|results in) (.+?)[\.!?]", RelationType.CAUSES),
            (r"(.+?) (?:uses|utilizes) (.+?)[\.!?]", RelationType.USED_FOR),
            (r"(.+?) is (?:located in|on|at) (.+?)[\.!?]", RelationType.LOCATED_IN),
        ]
        for pattern, rel_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                triples.append({"source": m[0].strip(), "relation": rel_type.value, "target": m[1].strip()})
        return triples

class AssociationEngine:
    def __init__(self, semantic_memory: SemanticMemory):
        self.semantic = semantic_memory
    
    def spread_activation(self, seed_concepts: List[str], threshold: float = 0.1, decay: float = 0.5) -> List[Tuple[str, float]]:
        activation = {}
        queue = []
        for c in seed_concepts:
            cid = self.semantic._name_index.get(c.lower())
            if cid:
                activation[cid] = 1.0
                queue.append((cid, 1.0))
        while queue:
            cid, level = queue.pop(0)
            if level < threshold:
                continue
            rels = self.semantic.graph._relations.get(cid, [])
            for r in rels:
                new_level = level * decay * r.weight
                if r.target_id not in activation or activation[r.target_id] < new_level:
                    activation[r.target_id] = new_level
                    queue.append((r.target_id, new_level))
        result = []
        for cid, act in sorted(activation.items(), key=lambda x: -x[1]):
            node = self.semantic.graph._nodes.get(cid)
            if node:
                result.append((node.name, act))
        return result
