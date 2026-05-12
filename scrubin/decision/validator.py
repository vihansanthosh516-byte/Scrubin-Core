import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from scrubin.core.orchestrator import Orchestrator
from scrubin.core.config import ConfigLayer
from scrubin.core.ledger import LoggedEvent
from scrubin.agents.simulation import SimulationAgent
from scrubin.agents.vitals import VitalsAgent
from scrubin.agents.procedure import ProcedureAgent
from scrubin.models.intents import ActionIntent
from scrubin.tester.checks.structure import StructureCheck
from scrubin.tester.checks.physiology import PhysiologyCheck
from scrubin.tester.checks.causality import CausalityCheck
from scrubin.tester.checks.recovery import RecoveryCheck
from scrubin.tester.scoring import ScoreEngine
from scrubin.tester.models import TestFinding
from scrubin.tester.profiles.registry import PROFILES, StressProfile

DEFAULT_HORIZONS = [1, 3, 5, 10]
DEFAULT_WEIGHTS = {1: 0.2, 3: 0.3, 5: 0.3, 10: 0.2}
DEFAULT_SEEDS = [42, 137, 999]


@dataclass
class ValidationResult:
    decision_score: int
    baseline_score: int
    delta: int
    verdict: str
    decision_action: str
    decision_details: dict
    baseline_details: dict
    deltas: dict = field(default_factory=dict)
    weighted_delta: float = 0.0
    confidence: str = "low"
    seeds_used: list = field(default_factory=list)
    per_seed_deltas: dict = field(default_factory=dict)


def _score_ledger(ledger, config=None):
    findings = []
    findings += StructureCheck().run(ledger)
    findings += PhysiologyCheck().run(ledger)
    findings += CausalityCheck(config=config).run(ledger)
    findings += RecoveryCheck(config=config).run(ledger)
    return ScoreEngine().compute(findings), findings


def _build_agents(profile_name):
    from scrubin.tester.runner import _ProfiledVitalsAgent, _ProfiledComplicationAgent, _NoOpProcedureAgent
    profile_cls = PROFILES.get(profile_name, StressProfile)
    profile = profile_cls()
    vitals_agent = _ProfiledVitalsAgent(profile)
    complication_agent = _ProfiledComplicationAgent(profile)
    proc_enabled = profile.procedure_enabled
    procedure_agent = ProcedureAgent() if proc_enabled else _NoOpProcedureAgent()
    return vitals_agent, complication_agent, procedure_agent


def _replay_orchestrator(seed, ticks, profile_name, config_path=None,
                         extra_injects=None):
    random.seed(seed)
    config = ConfigLayer(registry_path=config_path, active_profile=profile_name)
    orch = Orchestrator(seed=seed, config=config, active_profile=profile_name)
    SimulationAgent().setup(orch)
    vitals_agent, complication_agent, procedure_agent = _build_agents(profile_name)
    vitals_agent.setup(orch)
    complication_agent.setup(orch)
    procedure_agent.setup(orch)
    orch.setup()
    for t in range(ticks):
        orch.tick()
        if extra_injects:
            for inject in extra_injects:
                if inject.get("tick") == t + 1:
                    if inject["type"] == "procedure":
                        intent = ActionIntent(
                            id=f"intent-replay-{uuid.uuid4().hex[:8]}",
                            type="procedure",
                            name=inject["payload"].get("procedure", "monitor"),
                            target=inject["payload"].get("target", ""),
                            priority=0.0,
                            confidence=0.0,
                            source="replay",
                            reasoning="",
                        )
                        orch.authority.execute(intent)
                    else:
                        orch.bus.publish(
                            inject["type"],
                            inject["payload"],
                        )
        return orch


def _compute_delta_at_horizon(seed, current_tick, horizon, profile_name,
                              decision_dict, config_path=None):
    baseline_orch = _replay_orchestrator(
        seed=seed,
        ticks=current_tick + horizon,
        profile_name=profile_name,
        config_path=config_path,
    )
    baseline_score, _ = _score_ledger(baseline_orch.ledger.all(), config=baseline_orch.config)

    action = decision_dict.get("action", {})
    action_type = action.get("type", "")
    action_name = action.get("name", "")
    action_target = action.get("target", "")

    injects = None
    if action_type == "procedure":
        injects = [{
            "tick": current_tick + 1,
            "type": "procedure",
            "payload": {
                "tick": current_tick + 1,
                "procedure": action_name,
                "target": action_target,
            },
        }]

    decision_orch = _replay_orchestrator(
        seed=seed,
        ticks=current_tick + horizon,
        profile_name=profile_name,
        config_path=config_path,
        extra_injects=injects,
    )
    decision_score, decision_findings = _score_ledger(
        decision_orch.ledger.all(), config=decision_orch.config,
    )

    # Phase 5.5: Outcome-Oriented Validator
    if hasattr(baseline_orch, 'world') and hasattr(decision_orch, 'world'):
        baseline_score = -int(baseline_orch.world.mortality_risk * 1000)
        decision_score = -int(decision_orch.world.mortality_risk * 1000)
        
        # Add organ health bonuses
        baseline_organ = baseline_orch.world.organ_state
        baseline_score += int((baseline_organ.cardiovascular.health + baseline_organ.respiratory.health + baseline_organ.renal.health) * 100)
        
        decision_organ = decision_orch.world.organ_state
        decision_score += int((decision_organ.cardiovascular.health + decision_organ.respiratory.health + decision_organ.renal.health) * 100)
        
        # Resource efficiency
        decision_score -= sum(r.currently_used * 5 for r in decision_orch.world.resource_manager.resources.values())
        baseline_score -= sum(r.currently_used * 5 for r in baseline_orch.world.resource_manager.resources.values())
        
        # Stability Quality (SOFA/NEWS2)
        decision_score -= (decision_orch.world.sofa_score + decision_orch.world.news2_score) * 20
        baseline_score -= (baseline_orch.world.sofa_score + baseline_orch.world.news2_score) * 20

    details = {
        "total_events": len(decision_orch.ledger.all()),
        "complications": sum(1 for e in decision_orch.ledger.all() if e.type == "complication"),
        "procedures": sum(1 for e in decision_orch.ledger.all() if e.type == "procedure"),
        "decision_score": decision_score,
        "baseline_score": baseline_score,
        "mortality_delta": getattr(baseline_orch, 'world', None) and baseline_orch.world.mortality_risk - getattr(decision_orch, 'world', None).mortality_risk if getattr(decision_orch, 'world', None) else 0.0
    }

    return decision_score - baseline_score, decision_score, baseline_score, details


def _classify_confidence(improving_count, total_count):
    if total_count == 0:
        return "low"
    ratio = improving_count / total_count
    if ratio >= 0.75:
        return "high"
    elif ratio >= 0.5:
        return "medium"
    else:
        return "low"


def _classify_verdict(weighted_delta, confidence, improving_count, total_count):
    if weighted_delta > 0 and confidence == "high":
        return "strong_improvement"
    elif weighted_delta > 0:
        return "weak_improvement"
    elif weighted_delta < 0:
        return "worse"
    else:
        return "neutral"


class DecisionValidator:
    def __init__(self, horizons=None, weights=None, seeds=None,
                 recovery_window: int = 5):
        self._horizons = horizons or DEFAULT_HORIZONS
        self._weights = weights or DEFAULT_WEIGHTS
        self._seeds = seeds or [42]
        self._recovery_window = recovery_window
        self._validation_log: list[ValidationResult] = []

    def filter_intents(self, intents, min_priority: float = 0.0) -> list:
        from scrubin.models.intents import ActionIntent
        approved = []
        for intent in intents:
            if not isinstance(intent, ActionIntent):
                continue
            if intent.type != "procedure":
                continue
            if intent.priority >= min_priority:
                approved.append(intent)
        return approved

    def simulate_decision(self, seed, current_tick, profile_name, decision_dict,
                          config_path=None) -> ValidationResult:
        return self.validate(seed, current_tick, profile_name, decision_dict,
                             config_path=config_path)

    def validate(self, seed, current_tick, profile_name, decision_dict,
                 config_path=None) -> ValidationResult:
        action = decision_dict.get("action", {})
        action_name = action.get("name", "wait")

        per_horizon_deltas = {}
        per_horizon_decision_scores = {}
        per_horizon_baseline_scores = {}
        last_details = {}

        for h in self._horizons:
            delta, d_score, b_score, details = _compute_delta_at_horizon(
                seed, current_tick, h, profile_name, decision_dict,
                config_path=config_path,
            )
            per_horizon_deltas[h] = delta
            per_horizon_decision_scores[h] = d_score
            per_horizon_baseline_scores[h] = b_score
            last_details = details

        weighted_delta = sum(
            per_horizon_deltas.get(h, 0) * self._weights.get(h, 0)
            for h in self._horizons
        )

        improving = sum(1 for d in per_horizon_deltas.values() if d > 0)
        total = len(per_horizon_deltas)
        confidence = _classify_confidence(improving, total)
        verdict = _classify_verdict(weighted_delta, confidence, improving, total)

        primary_h = self._horizons[-1] if self._horizons else 3

        result = ValidationResult(
            decision_score=per_horizon_decision_scores.get(primary_h, 0),
            baseline_score=per_horizon_baseline_scores.get(primary_h, 0),
            delta=per_horizon_deltas.get(primary_h, 0),
            verdict=verdict,
            decision_action=action_name,
            decision_details=last_details,
            baseline_details={},
            deltas=per_horizon_deltas,
            weighted_delta=round(weighted_delta, 2),
            confidence=confidence,
            seeds_used=[seed],
            per_seed_deltas={seed: per_horizon_deltas},
        )
        self._validation_log.append(result)
        return result

    def validate_multi_seed(self, current_tick, profile_name, decision_dict,
                            config_path=None, seeds=None) -> ValidationResult:
        seeds = seeds or self._seeds
        action = decision_dict.get("action", {})
        action_name = action.get("name", "wait")

        all_per_seed = {}
        aggregated_deltas = {h: 0.0 for h in self._horizons}

        for seed in seeds:
            per_horizon = {}
            for h in self._horizons:
                delta, _, _, _ = _compute_delta_at_horizon(
                    seed, current_tick, h, profile_name, decision_dict,
                    config_path=config_path,
                )
                per_horizon[h] = delta
                aggregated_deltas[h] += delta
            all_per_seed[seed] = per_horizon

        avg_deltas = {h: aggregated_deltas[h] / len(seeds) for h in self._horizons}

        weighted_delta = sum(
            avg_deltas.get(h, 0) * self._weights.get(h, 0)
            for h in self._horizons
        )

        total_horizon_checks = len(self._horizons) * len(seeds)
        improving = sum(
            1 for seed_deltas in all_per_seed.values()
            for d in seed_deltas.values()
            if d > 0
        )
        confidence = _classify_confidence(improving, total_horizon_checks)
        verdict = _classify_verdict(weighted_delta, confidence, improving, total_horizon_checks)

        primary_h = self._horizons[-1] if self._horizons else 3
        primary_deltas = [all_per_seed[s][primary_h] for s in seeds]
        avg_primary = sum(primary_deltas) / len(primary_deltas)

        result = ValidationResult(
            decision_score=0,
            baseline_score=0,
            delta=round(avg_primary),
            verdict=verdict,
            decision_action=action_name,
            decision_details={},
            baseline_details={},
            deltas={h: round(v, 2) for h, v in avg_deltas.items()},
            weighted_delta=round(weighted_delta, 2),
            confidence=confidence,
            seeds_used=list(seeds),
            per_seed_deltas=all_per_seed,
        )
        self._validation_log.append(result)
        return result

    def validate_alternatives(self, seed, current_tick, profile_name, decision_dict,
                              alternatives, config_path=None) -> list[dict]:
        results = []
        main = self.validate(
            seed, current_tick, profile_name, decision_dict,
            config_path=config_path,
        )
        results.append({
            "name": main.decision_action,
            "decision_score": main.decision_score,
            "baseline_score": main.baseline_score,
            "delta": main.delta,
            "verdict": main.verdict,
            "deltas": main.deltas,
            "weighted_delta": main.weighted_delta,
            "confidence": main.confidence,
        })
        for alt in alternatives:
            alt_name = alt.get("name", "wait")
            alt_dict = {"action": {
                "type": "procedure" if alt_name not in ("wait", "monitor") else alt_name,
                "name": alt_name,
                "target": alt.get("target", "none"),
                "expected_effect": "",
                "confidence": 0.0,
            }}
            r = self.validate(
                seed, current_tick, profile_name, alt_dict,
                config_path=config_path,
            )
            results.append({
                "name": alt_name,
                "decision_score": r.decision_score,
                "baseline_score": r.baseline_score,
                "delta": r.delta,
                "verdict": r.verdict,
                "deltas": r.deltas,
                "weighted_delta": r.weighted_delta,
                "confidence": r.confidence,
            })
        return results

    def to_dict(self, result: ValidationResult) -> dict:
        return {
            "decision_score": result.decision_score,
            "baseline_score": result.baseline_score,
            "delta": result.delta,
            "verdict": result.verdict,
            "decision_action": result.decision_action,
            "deltas": result.deltas,
            "weighted_delta": result.weighted_delta,
            "confidence": result.confidence,
            "seeds_used": result.seeds_used,
        }

    @property
    def validation_log(self) -> list[ValidationResult]:
        return list(self._validation_log)

    def _summarize(self, ledger, findings):
        complications = [e for e in ledger if e.type == "complication"]
        procedures = [e for e in ledger if e.type == "procedure"]
        vitals = [e for e in ledger if e.type == "vitals_update"]
        latest = vitals[-1].payload.get("vitals", {}) if vitals else {}
        return {
            "total_events": len(ledger),
            "complications": len(complications),
            "procedures": len(procedures),
            "vitals_updates": len(vitals),
            "latest_vitals": latest,
            "findings_count": len(findings),
            "errors": sum(1 for f in findings if f.severity == "error"),
            "warnings": sum(1 for f in findings if f.severity == "warn"),
        }
