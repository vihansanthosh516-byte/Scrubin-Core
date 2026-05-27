from scrubin.control_plane.p7.evolution.evolutionary_adversary import AdversaryGenome, EvolutionaryAdversary


def test_evolution_changes_population():
    base = AdversaryGenome(0.2, 0.2, 0.2, 0.2)
    evo = EvolutionaryAdversary(base)
    fitness = [1.0]  # simple fitness for the single individual
    evo.evolve(fitness, "abc")
    assert len(evo.population) == 2


def test_mutation_deterministic():
    g = AdversaryGenome(0.5, 0.5, 0.5, 0.5)
    m1 = g.mutate("seed")
    m2 = g.mutate("seed")
    # Mutations from the same seed must be identical
    assert m1.crash_bias == m2.crash_bias
    assert isinstance(m1.crash_bias, float)
    assert isinstance(m2.delay_bias, float)
