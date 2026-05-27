from scrubin.control_plane.p7.phase_space.phase_space_analyzer import PhaseSpaceAnalyzer


def test_convergent_system():
    analyzer = PhaseSpaceAnalyzer()

    traj = [{"x": 1}, {"x": 1.01}, {"x": 1.02}, {"x": 1.01}]
    embedded = analyzer.embed(traj)
    attractors = analyzer.detect_attractors(embedded)
    classification = analyzer.classify(attractors)
    assert classification in ["CONVERGENT", "OSCILLATORY"]


def test_chaotic_system():
    analyzer = PhaseSpaceAnalyzer()

    traj = [
        {"x": 1},
        {"x": 5},
        {"x": -3},
        {"x": 10},
        {"x": 0},
    ]
    embedded = analyzer.embed(traj)
    attractors = analyzer.detect_attractors(embedded, threshold=0.1)
    classification = analyzer.classify(attractors)
    assert isinstance(attractors, list)
    assert classification in ["CHAOTIC", "OSCILLATORY"]
