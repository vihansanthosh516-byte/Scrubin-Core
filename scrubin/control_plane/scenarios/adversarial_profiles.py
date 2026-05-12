from typing import List, Any
from scrubin.control_plane.fuzz.mutators import ShuffleMutator, DelayMutator, DuplicateMutator, NoiseMutator

class AdversarialProfiles:
    """
    Predefined chaos attack patterns for stress-testing ScrubIn robustness.
    """
    @staticmethod
    def burst_chaos():
        return [ShuffleMutator(), DuplicateMutator(), DuplicateMutator()]

    @staticmethod
    def cascading_failure():
        return [DelayMutator(), DelayMutator(), ShuffleMutator()]

    @staticmethod
    def clinical_instability():
        return [NoiseMutator(), ShuffleMutator(), NoiseMutator()]

    @staticmethod
    def maximum_entropy():
        return [ShuffleMutator(), DelayMutator(), DuplicateMutator(), NoiseMutator()]
