from typing import List, Dict, Any
from scrubin.learning.benchmarks import BenchmarkRunner
from scrubin.learning.metrics import CompositeMetrics
from scrubin.scenarios.dsl import ScenarioRegistry, register_canonical_scenarios


class ClinicalBenchmarkSuite:
    """
    Formal research benchmark suite for clinical planners and RL policies.
    """
    def __init__(self):
        register_canonical_scenarios()
        self.runner = BenchmarkRunner()

    def run_standard_benchmarks(self, agent: Any) -> Dict[str, CompositeMetrics]:
        results = {}
        scenarios = ["septic_shock", "ards", "hemorrhagic_trauma", "cascade_failure"]
        
        for name in scenarios:
            config = ScenarioRegistry.get(name)
            if config:
                print(f"[BenchmarkSuite] Running benchmark: {name}")
                metrics = self.runner.run_scenario(agent, config)
                results[name] = metrics
        
        return results

    def generate_leaderboard(self, all_results: Dict[str, Dict[str, CompositeMetrics]]) -> str:
        """
        Generates a formatted leaderboard string for research reporting.
        """
        lines = ["# ScrubIn Clinical Research Leaderboard", ""]
        lines.append("| Agent | Scenario | Survival | Composite Score |")
        lines.append("|-------|----------|----------|-----------------|")
        
        for agent_name, scenario_results in all_results.items():
            for sc_name, metrics in scenario_results.items():
                lines.append(f"| {agent_name} | {sc_name} | {metrics.clinical.survival_rate:.2f} | {metrics.composite_score:.4f} |")
        
        return "\n".join(lines)
