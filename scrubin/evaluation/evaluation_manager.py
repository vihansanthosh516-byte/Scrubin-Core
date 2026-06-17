"""EvaluationManager – orchestrates the deterministic self‑evaluation pipeline.
The manager wires together each deterministic engine in the order prescribed by
Phase 8.5 and returns a single immutable ``EvaluationSnapshot``.
"""

from __future__ import annotations

from typing import Any, Tuple

from .system_evaluator import SystemEvaluator
from .decision_quality_engine import DecisionQualityEngine
from .physiology_coherence_engine import PhysiologyCoherenceEngine
from .knowledge_validation_engine import KnowledgeValidationEngine
from .memory_alignment_engine import MemoryAlignmentEngine
from .learning_effectiveness_engine import LearningEffectivenessEngine
from .simulation_drift_engine import SimulationDriftEngine
from .correction_engine import CorrectionEngine
from .models import (
    EvaluationSnapshot,
    SystemHealthReport,
    DecisionQualityReport,
    PhysiologyCoherenceReport,
    KnowledgeConsistencyReport,
    MemoryAlignmentReport,
    LearningEffectivenessReport,
    SimulationDriftReport,
    CorrectionSet,
)


class EvaluationManager:
    """Top‑level deterministic evaluator for Phase 8.5.

    The ``evaluate`` method accepts snapshots for each major subsystem and any
    auxiliary data required by the downstream engines.  All processing is pure
    and returns new immutable objects; input arguments are never mutated.
    """

    @staticmethod
    def evaluate(
        executive_snapshot: Any = None,
        physiology_snapshot: Any = None,
        knowledge_snapshot: Any = None,
        memory_snapshot: Any = None,
        learning_snapshot: Any = None,
        simulation_snapshot: Any = None,
        stabilization_snapshot: Any = None,
        # Additional data for decision quality
        executive_goals: Tuple[Any, ...] = (),
        executive_decisions: Tuple[Any, ...] = (),
        outcome_forecasts: Tuple[Any, ...] = (),
        risk_assessments: Tuple[Any, ...] = (),
        # Optional expected simulation snapshot for drift comparison
        expected_simulation_snapshot: Any = None,
    ) -> EvaluationSnapshot:
        # 1. System health validation
        health_report: SystemHealthReport = SystemEvaluator.evaluate(
            executive_snapshot=executive_snapshot,
            physiology_snapshot=physiology_snapshot,
            knowledge_snapshot=knowledge_snapshot,
            memory_snapshot=memory_snapshot,
            learning_snapshot=learning_snapshot,
            simulation_snapshot=simulation_snapshot,
            stabilization_snapshot=stabilization_snapshot,
        )

        # 2. Decision quality assessment
        decision_report: DecisionQualityReport = DecisionQualityEngine.evaluate(
            goals=executive_goals,
            decisions=executive_decisions,
            forecasts=outcome_forecasts,
            risks=risk_assessments,
        )

        # 3. Physiology coherence
        phys_report: PhysiologyCoherenceReport = PhysiologyCoherenceEngine.evaluate(
            physiology_snapshot=physiology_snapshot
        )

        # 4. Knowledge validation
        knowledge_report: KnowledgeConsistencyReport = KnowledgeValidationEngine.evaluate(
            knowledge_snapshot=knowledge_snapshot
        )

        # 5. Memory alignment
        memory_report: MemoryAlignmentReport = MemoryAlignmentEngine.evaluate(
            memory_snapshot=memory_snapshot
        )

        # 6. Learning effectiveness
        learning_report: LearningEffectivenessReport = LearningEffectivenessEngine.evaluate(
            learning_snapshot=learning_snapshot
        )

        # 7. Simulation drift
        simulation_report: SimulationDriftReport = SimulationDriftEngine.evaluate(
            actual_snapshot=simulation_snapshot,
            expected_snapshot=expected_simulation_snapshot,
        )

        # 8. Deterministic correction generation
        correction_set: CorrectionSet = CorrectionEngine.generate(
            health_report,
            decision_report,
            phys_report,
            knowledge_report,
            memory_report,
            learning_report,
            simulation_report,
        )

        # Assemble final snapshot
        return EvaluationSnapshot(
            health_report=health_report,
            decision_quality_report=decision_report,
            physiology_coherence_report=phys_report,
            knowledge_consistency_report=knowledge_report,
            memory_alignment_report=memory_report,
            learning_effectiveness_report=learning_report,
            simulation_drift_report=simulation_report,
            correction_set=correction_set,
        )
