from scrubin.search.similarity_engine import SimilarityEngine


def test_euclidean_and_manhattan():
    v1 = {"x": 1, "y": 2}
    v2 = {"x": 4, "y": 6}
    eu = SimilarityEngine.euclidean(v1, v2)
    man = SimilarityEngine.manhattan(v1, v2)
    assert eu == ((3**2 + 4**2) ** 0.5)
    assert man == 3 + 4


def test_exact_and_hamming():
    a = {"cat": "red", "num": 5}
    b = {"cat": "blue", "num": 5}
    assert SimilarityEngine.exact_match(a, a) == 0.0
    assert SimilarityEngine.exact_match(a, b) == 1.0
    assert SimilarityEngine.hamming(a, b) == 1
    assert SimilarityEngine.hamming(a, a) == 0
