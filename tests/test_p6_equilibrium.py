import pytest
from scrubin.control_plane.analysis.equilibrium import EquilibriumAnalyzer
from scrubin.control_plane.analysis.attractor import AttractorClassifier


def test_equilibrium_metrics_basic():
    analyzer = EquilibriumAnalyzer()
    states = [
        {"energy": 1.0},
        {"energy": 1.1},
        {"energy": 1.05},
    ]
    metrics = analyzer.compute_metrics(states)
    assert "stability" in metrics
    assert 0.0 <= metrics["stability"] <= 1.0


def test_attractor_classification():
    classifier = AttractorClassifier()
    result = classifier.classify({
        "stability": 0.9,
        "drift": 0.1,
        "variance": 0.1,
    })
    assert result in {"CONVERGENT", "OSCILLATORY", "CHAOTIC", "UNSTABLE"}
