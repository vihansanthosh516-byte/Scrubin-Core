class DummyKernel:
    """A minimal deterministic kernel used for P8 unit tests.

    The kernel updates a ``value`` field deterministically based on the
    provided ``seed`` and an internal tick counter. Each ``step`` returns a
    new state dictionary.
    """

    def __init__(self, seed: int = 0):
        self.seed = seed
        self.tick_counter = 0

    def step(self, state: dict):
        """Perform a deterministic state transition.

        Parameters
        ----------
        state: dict
            Current simulation state.

        Returns
        -------
        dict
            Updated state containing ``tick`` and a cumulative ``value``.
        """
        # Ensure we work on a copy to avoid side‑effects on the caller's dict
        new_state = dict(state) if state else {}
        new_state["tick"] = self.tick_counter
        # Deterministic increment: seed + current tick_counter
        new_state["value"] = new_state.get("value", 0) + self.seed + self.tick_counter
        self.tick_counter += 1
        return new_state
