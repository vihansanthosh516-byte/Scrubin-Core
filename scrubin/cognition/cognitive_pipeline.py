"""Deterministic cognitive integration pipeline.

Executes the full chain of cognition layers in strict order, ensuring each layer
only consumes the output of its immediate predecessor. The function is side‑
effecting – it mutates the provided stores according to deterministic rules.
"""

from __future__ import annotations

from typing import Any

# Import sub‑components – all are deterministic and have no external side effects.
from .graph_builder import update_graph
from .meta_pattern_engine import update_meta_patterns
from .executive_engine import update_executive


def run_cognitive_pipeline(
    world: Any,
    memory_store: Any,
    fact_store: Any,
    belief_store: Any,
    reflection_store: Any,
    graph_store: Any,
    counterfactual_store: Any,
    meta_store: Any,
    plan_store: Any,
    executive_store: Any,
) -> None:
    """Run the deterministic cognitive pipeline.

    The steps are executed in the exact order required by Phase 4.0:

    1. ``update_graph`` – builds the knowledge graph from current beliefs and
       reflections.
    2. ``update_meta_patterns`` – extracts meta‑patterns from reflections and
       stored counterfactual results.
    3. (Optional) ``Counterfactual`` analysis – in this deterministic setup the
       store is assumed to already contain any needed scenarios; no new work is
       performed.
    4. ``update_executive`` – creates deterministic executive goals from the
       meta‑patterns, beliefs and plans.

    The function deliberately does **not** invoke planning or counterfactual
    generation – those are handled elsewhere (e.g., the orchestrator) to keep
    the pipeline a thin deterministic wrapper.
    """
    # 1. Knowledge‑graph construction
    update_graph(belief_store, reflection_store, graph_store)

    # 2. Meta‑pattern extraction (uses reflections and counterfactuals)
    update_meta_patterns(
        reflection_store=reflection_store,
        counterfactual_store=counterfactual_store,
        knowledge_graph=graph_store,
        meta_store=meta_store,
    )

    # 3. Executive goal generation – deterministic based on current stores
    update_executive(meta_store, belief_store, plan_store, executive_store)

    # The pipeline is deliberately lightweight – additional stages such as
    # counterfactual scenario execution are expected to be triggered elsewhere.
    return None


# ---------------------------------------------------------------------
# Dependency verification – simple static analysis
# ---------------------------------------------------------------------
def verify_dependencies() -> None:
    """Verify that each cognition layer only depends on its predecessor.

    The function encodes a whitelist of allowed dependencies and prints warnings
    for any import that violates the rule set. It is *purely* diagnostic – it does
    not raise exceptions.
    """
    # Mapping of layer → allowed downstream consumers (by module name prefix).
    allowed = {
        "episode": ["fact"],
        "fact": ["belief"],
        "belief": ["reflection", "graph"],
        "reflection": ["graph", "meta"],
        "graph": ["counterfactual", "meta"],
        "counterfactual": ["meta"],
        "meta": ["plan"],
        "plan": ["executive"],
        "executive": [],
    }

    # Very naive static check – iterate over all cognition modules and look for
    # ``import`` statements that reference another layer.
    import os, re
    base = os.path.dirname(__file__)
    pattern = re.compile(r"from\s+scrubin\.cognition\.([a-z_]+)\s+import")
    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for match in pattern.finditer(content):
                src = match.group(1)
                # Determine current module name (without path)
                cur = os.path.splitext(f)[0]
                # If the current module is not in allowed, warn.
                allowed_targets = allowed.get(cur, [])
                if src not in allowed_targets:
                    print(f"[DependencyWarning] {cur}.py imports {src}.py – not a permitted dependency")


# ---------------------------------------------------------------------
# Simple DAG representation for visualization purposes
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class PipelineNode:
    name: str
    children: Tuple["PipelineNode", ...] = ()

def build_pipeline_dag() -> PipelineNode:
    """Construct a deterministic DAG representing the cognition pipeline.

    Returns the root ``PipelineNode`` (Episode) whose ``children`` chain follows
    the prescribed order. The structure is immutable and can be inspected for
    testing or documentation purposes.
    """
    exec_node = PipelineNode(name="Executive")
    plan_node = PipelineNode(name="Plan", children=(exec_node,))
    meta_node = PipelineNode(name="Meta", children=(plan_node,))
    counter_node = PipelineNode(name="Counterfactual", children=(meta_node,))
    graph_node = PipelineNode(name="Graph", children=(counter_node,))
    refl_node = PipelineNode(name="Reflection", children=(graph_node,))
    belief_node = PipelineNode(name="Belief", children=(refl_node,))
    fact_node = PipelineNode(name="Fact", children=(belief_node,))
    episode_node = PipelineNode(name="Episode", children=(fact_node,))
    return episode_node


# ---------------------------------------------------------------------
# Complexity audit – returns a descriptive mapping of estimated complexities.
# ---------------------------------------------------------------------
def complexity_audit() -> dict:
    """Provide a high‑level complexity overview of each pipeline stage.

    The values are expressed as big‑O strings relative to the number of items
    processed (episodes *E*, facts *F*, beliefs *B*, etc.).
    """
    return {
        "episode_generation": "O(E)",
        "fact_extraction": "O(F) – linear scan of events per tick",
        "belief_merging": "O(B) – deterministic per‑fact update",
        "reflection_generation": "O(B) – grouping by subject",
        "graph_construction": "O(B + R) – iterate beliefs and reflections",
        "counterfactual_replay": "O(C) – deep copy per scenario",
        "meta_extraction": "O(R + C) – linear over reflections & counterfactuals",
        "planning": "O(P * H * A) – beam search over horizon H and actions A",
        "executive_scheduling": "O(G log G) – deterministic sort of goals",
    }
