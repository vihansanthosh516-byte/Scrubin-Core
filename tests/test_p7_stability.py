from scrubin.control_plane.p7.stability.lyapunov import LyapunovAnalyzer


def test_stable_case():
    analyzer = LyapunovAnalyzer()
    t1 = [{"x": 1}, {"x": 1.1}, {"x": 1.05}]
    t2 = [{"x": 1}, {"x": 1.05}, {"x": 1.02}]
    exp = analyzer.estimate_exponent(t1, t2)
    result = analyzer.classify(exp)
    assert result.regime in ["STABLE", "NEUTRAL"]


def test_chaotic_case():
    analyzer = LyapunovAnalyzer()
    t1 = [{"x": 1}, {"x": 2}, {"x": 4}]
    t2 = [{"x": 1}, {"x": 3}, {"x": 6}]
    exp = analyzer.estimate_exponent(t1, t2)
    result = analyzer.classify(exp)
    assert isinstance(exp, float)
    assert result.regime in ["CHAOTIC", "NEUTRAL"]
