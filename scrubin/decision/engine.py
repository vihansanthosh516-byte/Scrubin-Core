import uuid
from dataclasses import dataclass, field
from typing import Any

from scrubin.clinical.thresholds import ClinicalThresholds
from scrubin.complications.registry import ComplicationRegistry
from scrubin.models.intents import ActionIntent
from scrubin.models.types import (
    ComplicationSeverity,
    ComplicationState,
    DecisionOption,
    RiskLevel,
    VitalDelta,
    Vitals,
)

_SEVERITY_OPTIONS: dict[str, dict[str, list[dict]]] = {
    "respiratory": {
        "mild": [
            {"id": "oxygen_therapy", "label": "Oxygen Therapy", "risk": "low", "impact": {"spo2": 3}},
            {"id": "positioning", "label": "Reposition Patient", "risk": "low", "impact": {"spo2": 2, "heart_rate": -2}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "moderate": [
            {"id": "oxygen_therapy", "label": "Oxygen Therapy (High Flow)", "risk": "low", "impact": {"spo2": 5}},
            {"id": "ventilator_adjustment", "label": "Ventilator Adjustment", "risk": "medium", "impact": {"spo2": 3, "heart_rate": -2}},
            {"id": "airway_adjuncts", "label": "Airway Adjuncts", "risk": "medium", "impact": {"spo2": 4, "heart_rate": -3}},
            {"id": "positioning", "label": "Reposition Patient", "risk": "low", "impact": {"spo2": 2}},
        ],
        "severe": [
            {"id": "intubation", "label": "Intubation", "risk": "high", "impact": {"spo2": 5, "heart_rate": -3}},
            {"id": "emergency_airway", "label": "Emergency Airway", "risk": "high", "impact": {"spo2": 8, "heart_rate": -5}},
            {"id": "ventilator_support", "label": "Ventilator Support", "risk": "high", "impact": {"spo2": 6, "heart_rate": -2}},
            {"id": "bag_mask", "label": "Bag-Mask Ventilation", "risk": "high", "impact": {"spo2": 4, "heart_rate": -4}},
        ],
    },
    "cardiovascular": {
        "mild": [
            {"id": "iv_fluids", "label": "IV Fluids", "risk": "low", "impact": {"bp_systolic": 5, "heart_rate": -3}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "moderate": [
            {"id": "central_line", "label": "Central Line Placement", "risk": "medium", "impact": {"bp_systolic": 5, "bp_diastolic": 3}},
            {"id": "blood_transfusion", "label": "Blood Transfusion", "risk": "medium", "impact": {"bp_systolic": 10, "spo2": 5, "heart_rate": -5}},
            {"id": "iv_fluids", "label": "IV Fluids (Aggressive)", "risk": "low", "impact": {"bp_systolic": 8, "heart_rate": -2}},
        ],
        "severe": [
            {"id": "blood_transfusion", "label": "Emergency Blood Transfusion", "risk": "high", "impact": {"bp_systolic": 15, "spo2": 8, "heart_rate": -8}},
            {"id": "central_line", "label": "Emergency Central Line", "risk": "high", "impact": {"bp_systolic": 8, "bp_diastolic": 5}},
            {"id": "vasopressors", "label": "Vasopressors", "risk": "high", "impact": {"bp_systolic": 20, "heart_rate": 10}},
            {"id": "surgical_intervention", "label": "Emergency Surgery", "risk": "high", "impact": {"bp_systolic": 10, "heart_rate": -5, "temperature": -0.4}},
        ],
    },
    "infectious": {
        "mild": [
            {"id": "antibiotics", "label": "Broad-Spectrum Antibiotics", "risk": "low", "impact": {"temperature": -0.3, "heart_rate": -3}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "moderate": [
            {"id": "antibiotics", "label": "IV Antibiotics", "risk": "low", "impact": {"temperature": -0.5, "heart_rate": -5, "spo2": 2}},
            {"id": "surgical_intervention", "label": "Source Control (Surgical)", "risk": "medium", "impact": {"temperature": -0.4, "heart_rate": -4}},
            {"id": "blood_transfusion", "label": "Supportive Transfusion", "risk": "medium", "impact": {"bp_systolic": 5, "spo2": 3}},
        ],
        "severe": [
            {"id": "surgical_intervention", "label": "Emergency Debridement", "risk": "high", "impact": {"temperature": -0.8, "heart_rate": -8}},
            {"id": "antibiotics", "label": "Maximum Antibiotic Therapy", "risk": "medium", "impact": {"temperature": -0.6, "heart_rate": -5, "spo2": 3}},
            {"id": "central_line", "label": "Central Line for Pressure Monitoring", "risk": "high", "impact": {"bp_systolic": 5, "bp_diastolic": 3}},
            {"id": "vasopressors", "label": "Septic Shock Protocol", "risk": "high", "impact": {"bp_systolic": 15, "heart_rate": 8}},
        ],
    },
    "hematologic": {
        "mild": [
            {"id": "iron_supplement", "label": "Iron Supplementation", "risk": "low", "impact": {"spo2": 1, "heart_rate": -2}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "moderate": [
            {"id": "blood_transfusion", "label": "Blood Transfusion", "risk": "medium", "impact": {"spo2": 5, "bp_systolic": 8, "heart_rate": -5}},
            {"id": "iron_supplement", "label": "IV Iron Therapy", "risk": "low", "impact": {"spo2": 2, "heart_rate": -3}},
        ],
        "severe": [
            {"id": "blood_transfusion", "label": "Emergency Blood Transfusion", "risk": "high", "impact": {"spo2": 8, "bp_systolic": 12, "heart_rate": -8}},
            {"id": "central_line", "label": "Central Line for Rapid Infusion", "risk": "high", "impact": {"bp_systolic": 5, "bp_diastolic": 3}},
            {"id": "ventilator_adjustment", "label": "Ventilator Support", "risk": "high", "impact": {"spo2": 4}},
        ],
    },
    "general": {
        "mild": [
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "moderate": [
            {"id": "intervention", "label": "Standard Intervention", "risk": "medium", "impact": {"spo2": 2, "heart_rate": -3, "bp_systolic": 5}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
        "severe": [
            {"id": "emergency_intervention", "label": "Emergency Intervention", "risk": "high", "impact": {"spo2": 5, "heart_rate": -5, "bp_systolic": 10}},
            {"id": "surgical_intervention", "label": "Surgical Intervention", "risk": "high", "impact": {"temperature": -0.4, "heart_rate": -4}},
            {"id": "monitor", "label": "Monitor", "risk": "low", "impact": {}},
        ],
    },
}

_DEFAULT_THRESHOLDS = ClinicalThresholds.defaults()


def _determine_severity(complication_id: str, vitals: dict, thresholds: ClinicalThresholds = None) -> ComplicationSeverity:
    t = thresholds or _DEFAULT_THRESHOLDS
    defn = ComplicationRegistry.get(complication_id)
    if defn is None:
        return "moderate"
    return t.determine_severity(defn.category, vitals)


def _generate_options_for_severity(
    complication_id: str,
    severity: ComplicationSeverity,
    vitals: dict,
) -> list[DecisionOption]:
    defn = ComplicationRegistry.get(complication_id)
    category = defn.category if defn else "general"
    category_options = _SEVERITY_OPTIONS.get(category, _SEVERITY_OPTIONS["general"])
    severity_options = category_options.get(severity, category_options.get("moderate", []))

    options = []
    for opt in severity_options:
        impact = opt.get("impact", {})
        options.append(DecisionOption(
            id=opt["id"],
            label=opt["label"],
            archetype=category,
            expected_impact=VitalDelta(
                spo2=impact.get("spo2", 0.0),
                heart_rate=impact.get("heart_rate", 0.0),
                bp_systolic=impact.get("bp_systolic", 0.0),
                bp_diastolic=impact.get("bp_diastolic", 0.0),
                temperature=impact.get("temperature", 0.0),
            ),
            risk_level=opt.get("risk", "medium"),
            target_complication=complication_id,
        ))
    return options


@dataclass
class Action:
    type: str
    target: str
    expected_effect: str
    confidence: float
    name: str = ""
    severity: ComplicationSeverity = "moderate"
    risk_level: RiskLevel = "medium"


@dataclass
class Decision:
    action: Action
    score: int
    reasoning: list
    alternatives: list


def _build_causality_graph(ledger):
    complications = [e for e in ledger if e.type == "complication"]
    procedures = [e for e in ledger if e.type == "procedure"]
    vitals_updates = [e for e in ledger if e.type == "vitals_update"]

    nodes = {}
    edges = []

    for c in complications:
        key = f"complication:{c.payload.get('complication')}@{c.tick}"
        nodes[key] = {"type": "complication", "tick": c.tick, "name": c.payload.get("complication"), "severity": c.payload.get("severity", "moderate")}

    for p in procedures:
        key = f"procedure:{p.payload.get('procedure')}@{p.tick}"
        nodes[key] = {"type": "procedure", "tick": p.tick, "name": p.payload.get("procedure"), "target": p.payload.get("target")}
        comp_key = f"complication:{p.payload.get('target')}@{p.tick}"
        if comp_key in nodes:
            edges.append((comp_key, key))

    for v in vitals_updates:
        key = f"vitals:{v.tick}"
        nodes[key] = {"type": "vitals_update", "tick": v.tick, "vitals": v.payload.get("vitals", {})}
        for n, data in list(nodes.items()):
            if data["type"] == "procedure" and data["tick"] < v.tick <= data["tick"] + 2:
                edges.append((n, key))

    return {"nodes": nodes, "edges": edges}


def _extract_state(ledger, tick, recovery_window=5):
    active_complications = []
    latest_vitals = {}
    recent_procedures = []

    for e in reversed(ledger):
        if e.type == "complication" and e.tick <= tick:
            name = e.payload.get("complication")
            in_window = tick <= e.tick + recovery_window
            has_procedure = any(
                p.payload.get("target") == name and p.tick >= e.tick
                for p in ledger
                if p.type == "procedure"
            )
            if in_window or not has_procedure:
                active_complications.append(name)

        if e.type == "vitals_update" and e.tick <= tick and not latest_vitals:
            latest_vitals = e.payload.get("vitals", {})

        if e.type == "procedure" and e.tick <= tick:
            recent_procedures.append(e.payload.get("procedure"))

    active_complications = sorted(set(active_complications))
    recent_procedures = sorted(set(recent_procedures))

    return {
        "tick": tick,
        "active_complications": active_complications,
        "latest_vitals": latest_vitals,
        "recent_procedures": recent_procedures,
    }


class DecisionEngine:
    def __init__(self, recovery_window: int = 5, policy_weights=None, thresholds: ClinicalThresholds = None, planner_config=None):
        self._recovery_window = recovery_window
        self._policy_weights = policy_weights
        self._thresholds = thresholds or _DEFAULT_THRESHOLDS
        self._decision_log: list[Decision] = []
        
        from scrubin.decision.config import PlannerConfig
        self.planner_config = planner_config or PlannerConfig()
        
        from scrubin.decision.utility import UtilityFunction
        from scrubin.decision.mcts import MonteCarloTreeSearch
        self.utility_function = UtilityFunction()
        self.mcts = MonteCarloTreeSearch(self.utility_function, self.planner_config)

    def evaluate_actions(self, state: dict, graph: dict, world=None) -> list[Action]:
        tick = state.get("tick", 0)
        active = state.get("active_complications", [])
        vitals = state.get("latest_vitals", {})

        candidates = []

        for comp in active:
            severity = _determine_severity(comp, vitals, thresholds=self._thresholds)
            options = _generate_options_for_severity(comp, severity, vitals)
            for opt in options:
                candidates.append(Action(
                    type="procedure",
                    target=comp,
                    expected_effect=f"addresses {comp} ({severity})",
                    confidence=0.9 if opt.risk_level == "low" else (0.7 if opt.risk_level == "medium" else 0.5),
                    name=opt.id,
                    severity=severity,
                    risk_level=opt.risk_level,
                ))

        candidates.append(Action(
            type="monitor",
            target="vitals",
            expected_effect="monitor vitals trends",
            confidence=0.7,
            name="monitor",
        ))

        candidates.append(Action(
            type="wait",
            target="none",
            expected_effect="no action",
            confidence=1.0,
            name="wait",
        ))

        return candidates

    def score_action(self, action: Action, state: dict, graph: dict, world=None) -> int:
        w = self._policy_weights
        if w is None:
            from scrubin.decision.learner import PolicyWeights
            w = PolicyWeights()

        score = 0
        active = state.get("active_complications", [])
        vitals = state.get("latest_vitals", {})
        recent = state.get("recent_procedures", [])
        tick = state.get("tick", 0)
        t = self._thresholds

        if action.type == "procedure" and action.target in active:
            score += w.resolves_complication
            if action.severity == "severe":
                score += int(w.resolves_complication * 0.5)
            elif action.severity == "mild":
                score -= int(w.resolves_complication * 0.2)

        if action.type == "procedure":
            defn = ComplicationRegistry.get(action.target)
            if defn:
                profile = defn.severity_profiles.for_severity(action.severity)
                impact_dict = profile.to_dict()
                for v_key, delta in impact_dict.items():
                    if delta == 0:
                        continue
                    val = vitals.get(v_key)
                    if val is None:
                        continue
                    if v_key == "spo2" and val < t.severity.spo2_severe and delta > 0:
                        score += w.improves_vitals
                    elif v_key == "spo2" and val < t.severity.spo2_moderate and delta > 0:
                        score += int(w.improves_vitals * 0.5)
                    elif v_key == "bp_systolic" and val < t.severity.bp_systolic_moderate and delta > 0:
                        score += w.improves_vitals
                    elif v_key == "heart_rate" and ((val > t.severity.heart_rate_tachycardia and delta < 0)
                                                     or (val < t.severity.heart_rate_bradycardia and delta > 0)):
                        score += w.improves_vitals
                    elif v_key == "temperature" and val > t.severity.temperature_moderate and delta < 0:
                        score += w.improves_vitals

        if action.type == "procedure" and not active and action.target not in active:
            score += w.unnecessary_penalty

        if action.name in recent:
            score += w.duplicate_penalty

        if action.type == "procedure" and action.target in active:
            comp_events = [
                n for n in graph.get("nodes", {}).values()
                if n.get("type") == "complication" and n.get("name") == action.target
            ]
            if comp_events:
                earliest = min(n["tick"] for n in comp_events)
                if tick - earliest < self._recovery_window:
                    score += w.recovery_window_bonus

        if action.risk_level == "high" and action.severity != "severe":
            score -= 5

        # Phase 5.5: Resource Constraint Penalties
        if world and action.type == "procedure":
            rm = world.resource_manager
            cost = 0
            scarcity_penalty = 0
            if action.name in ("intubation", "ventilator_support"):
                cost = 1
                if rm.resources["ventilators"].available == 1:
                    scarcity_penalty = 15 # using the last ventilator
                elif rm.resources["ventilators"].available == 0:
                    scarcity_penalty = 100 # impossible
            elif action.name == "blood_transfusion":
                cost = 2
                if rm.resources["blood_units"].available <= 2:
                    scarcity_penalty = 10
            
            score -= scarcity_penalty
            
            # Phase 5.5: SOFA influence
            if world.sofa_score >= 12 and action.risk_level == "low":
                score -= 10 # Penalize low risk actions when mortality is extremely high

        return int(round(score))

    def select_best_action(self, actions: list) -> Action:
        if not actions:
            return Action(type="wait", target="none", expected_effect="no candidates", confidence=1.0, name="wait")
        return max(actions, key=lambda a: (a.score if hasattr(a, "score") else 0, -ord(a.name[0]) if a.name else 0))

    def explain(self, action: Action, state: dict, graph: dict) -> list[str]:
        reasons = []
        active = state.get("active_complications", [])
        vitals = state.get("latest_vitals", {})
        recent = state.get("recent_procedures", [])
        tick = state.get("tick", 0)
        t = self._thresholds

        if action.type == "procedure" and action.target in active:
            reasons.append(f"resolves {action.target} (severity: {action.severity})")

        if action.type == "procedure":
            defn = ComplicationRegistry.get(action.target)
            if defn:
                profile = defn.severity_profiles.for_severity(action.severity)
                impact_dict = profile.to_dict()
                for v_key, delta in impact_dict.items():
                    if delta == 0:
                        continue
                    val = vitals.get(v_key)
                    if val is None:
                        continue
                    if v_key == "spo2" and val < t.severity.spo2_severe and delta > 0:
                        reasons.append("improves oxygenation (critical)")
                    elif v_key == "spo2" and val < t.severity.spo2_moderate and delta > 0:
                        reasons.append("improves oxygenation")
                    elif v_key == "bp_systolic" and val < t.severity.bp_systolic_moderate and delta > 0:
                        reasons.append("improves blood pressure")
                    elif v_key == "heart_rate" and ((val > t.severity.heart_rate_tachycardia and delta < 0)
                                                     or (val < t.severity.heart_rate_bradycardia and delta > 0)):
                        reasons.append("stabilizes heart rate")
                    elif v_key == "temperature" and val > t.severity.temperature_moderate and delta < 0:
                        reasons.append("reduces fever")

        if action.type == "procedure" and not active:
            reasons.append("unnecessary -- no active complication")

        if action.name in recent:
            reasons.append("duplicates recent procedure")

        if action.type == "procedure" and action.target in active:
            comp_events = [
                n for n in graph.get("nodes", {}).values()
                if n.get("type") == "complication" and n.get("name") == action.target
            ]
            if comp_events:
                earliest = min(n["tick"] for n in comp_events)
                if tick - earliest < self._recovery_window:
                    reasons.append("within recovery window")

        if action.type == "monitor":
            reasons.append("monitor vitals trends for changes")

        if action.type == "wait":
            reasons.append("no immediate action needed")

        return reasons if reasons else ["no specific reasoning"]

    def decide(self, world, ledger, tick: int) -> Decision:
        # Phase 6: MCTS Strategy Coordinator
        from scrubin.decision.interrupts import EmergencyInterrupts
        from scrubin.decision.planning import PlanningState
        
        if self.planner_config.enabled and world:
            # 1. Emergency interrupts
            interrupt = EmergencyInterrupts.check_interrupt(world)
            if interrupt:
                action_obj = Action(type="procedure", target="system", expected_effect="Emergency intervention", confidence=1.0, name=interrupt, risk_level="high")
                decision = Decision(action=action_obj, score=999, reasoning=["EMERGENCY BYPASS TRIGGERED: Critical physiological failure."], alternatives=[])
                self._decision_log.append(decision)
                return decision
                
            # 2. Strategic Planner path
            state = PlanningState(world=world)
            result = self.mcts.search(state, seed=tick)
            if result:
                action_type = "procedure" if result.selected_action not in ("wait", "monitor") else result.selected_action
                action_obj = Action(
                    type=action_type, target="system", expected_effect="Strategic planner choice", 
                    confidence=result.confidence, name=result.selected_action, risk_level="medium"
                )
                decision = Decision(
                    action=action_obj,
                    score=int(result.expected_utility),
                    reasoning=result.reasoning_trace,
                    alternatives=[] # Can be populated from MCTS branches later
                )
                
                # Add the result to decision for event publishing
                object.__setattr__(decision, "planning_result", result)
                self._decision_log.append(decision)
                return decision
                
            if not self.planner_config.fallback_to_greedy:
                action_obj = Action(type="wait", target="none", expected_effect="No viable plans", confidence=1.0, name="wait")
                return Decision(action=action_obj, score=0, reasoning=["MCTS failed to find path"], alternatives=[])

        # 3. Fallback to greedy (legacy) path
        state = _extract_state(ledger, tick, recovery_window=self._recovery_window)
        graph = _build_causality_graph(ledger)
        candidates = self.evaluate_actions(state, graph, world)

        scored = []
        for action in candidates:
            s = self.score_action(action, state, graph, world)
            scored_action = Action(
                type=action.type,
                target=action.target,
                expected_effect=action.expected_effect,
                confidence=action.confidence,
                name=action.name,
                severity=action.severity,
                risk_level=action.risk_level,
            )
            object.__setattr__(scored_action, "score", s)
            scored.append(scored_action)

        best = self.select_best_action(scored)
        reasoning = self.explain(best, state, graph)

        alternatives = []
        for a in sorted(scored, key=lambda x: x.score if hasattr(x, "score") else 0, reverse=True):
            if a is not best:
                alternatives.append({
                    "name": a.name,
                    "score": a.score if hasattr(a, "score") else 0,
                })

        decision = Decision(
            action=best,
            score=best.score if hasattr(best, "score") else 0,
            reasoning=reasoning,
            alternatives=alternatives,
        )
        self._decision_log.append(decision)
        return decision

    @property
    def decision_log(self) -> list[Decision]:
        return list(self._decision_log)

    def produce_intents(self, ledger, tick: int) -> list[ActionIntent]:
        state = _extract_state(ledger, tick, recovery_window=self._recovery_window)
        graph = _build_causality_graph(ledger)
        candidates = self.evaluate_actions(state, graph)

        intents = []
        for action in candidates:
            s = self.score_action(action, state, graph)
            reasoning = self.explain(action, state, graph)
            intent_id = f"intent-{uuid.uuid4().hex[:8]}"
            intents.append(ActionIntent(
                id=intent_id,
                type=action.type,
                name=action.name,
                target=action.target,
                priority=float(s),
                confidence=action.confidence,
                source="engine",
                reasoning="; ".join(reasoning),
                metadata={
                    "severity": action.severity,
                    "risk_level": action.risk_level,
                    "expected_effect": action.expected_effect,
                },
            ))
        return intents

    def generate_options(self, ledger, tick: int) -> list[DecisionOption]:
        state = _extract_state(ledger, tick, recovery_window=self._recovery_window)
        active = state.get("active_complications", [])
        vitals = state.get("latest_vitals", {})
        options: list[DecisionOption] = []

        for comp in active:
            severity = _determine_severity(comp, vitals, thresholds=self._thresholds)
            comp_options = _generate_options_for_severity(comp, severity, vitals)
            options.extend(comp_options)

        options.append(DecisionOption(
            id="monitor",
            label="Monitor",
            archetype="general",
            expected_impact=VitalDelta(),
            risk_level="low",
            target_complication="",
        ))
        options.append(DecisionOption(
            id="wait",
            label="Wait",
            archetype="general",
            expected_impact=VitalDelta(),
            risk_level="low",
            target_complication="",
        ))

        self._last_generated_options = options
        return options

    def option_to_dict(self, option: DecisionOption) -> dict:
        return option.to_dict()

    def resolve_option(self, option_id: str, target: str = "") -> Action | None:
        options = getattr(self, "_last_generated_options", [])
        for opt in options:
            if opt.id == option_id:
                action_type = "procedure" if opt.risk_level != "low" or opt.id not in ("monitor", "wait") else opt.id
                if opt.id in ("monitor", "wait"):
                    action_type = opt.id
                return Action(
                    type=action_type,
                    target=target or opt.target_complication,
                    expected_effect=f"addresses {opt.target_complication}" if opt.target_complication else opt.label,
                    confidence=0.9 if opt.risk_level == "low" else (0.7 if opt.risk_level == "medium" else 0.5),
                    name=opt.id,
                    severity="moderate",
                    risk_level=opt.risk_level,
                )

        if option_id in ("monitor", "wait"):
            return Action(type=option_id, target="none", expected_effect="no action", confidence=1.0, name=option_id)

        return None

    def resolve_option_to_intent(self, option_id: str, target: str = "", tick: int = 0) -> ActionIntent | None:
        action = self.resolve_option(option_id, target)
        if action is None:
            return None
        return ActionIntent(
            id=f"intent-user-{uuid.uuid4().hex[:8]}",
            type=action.type,
            name=action.name,
            target=action.target,
            priority=0.0,
            confidence=action.confidence,
            source="user_decision",
            reasoning=action.expected_effect,
            metadata={
                "severity": action.severity,
                "risk_level": action.risk_level,
                "expected_effect": action.expected_effect,
            },
        )

    def to_dict(self, decision: Decision) -> dict:
        return {
            "action": {
                "type": decision.action.type,
                "target": decision.action.target,
                "name": decision.action.name,
                "expected_effect": decision.action.expected_effect,
                "confidence": decision.action.confidence,
                "severity": decision.action.severity,
                "risk_level": decision.action.risk_level,
            },
            "score": decision.score,
            "reasoning": decision.reasoning,
            "alternatives": decision.alternatives,
        }
