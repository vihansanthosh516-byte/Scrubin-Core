class BayesianUpdater:
    """
    Handles Bayesian probability updates for clinical diagnoses over time.
    """
    
    @staticmethod
    def update_posterior(prior: float, likelihood: float, false_positive_rate: float = 0.1) -> float:
        """
        Updates the probability of a diagnosis given new evidence.
        
        Args:
            prior: The current estimated probability of the diagnosis before evidence.
            likelihood: P(Evidence | Diagnosis) - The probability of observing this evidence if the diagnosis is true.
            false_positive_rate: P(Evidence | Not Diagnosis) - The probability of observing this evidence if the diagnosis is false.
        
        Returns:
            The posterior probability P(Diagnosis | Evidence).
        """
        if prior >= 1.0:
            return 1.0
        if prior <= 0.0:
            return 0.0
            
        evidence_prob = (likelihood * prior) + (false_positive_rate * (1 - prior))
        
        if evidence_prob == 0:
            return 0.0
            
        posterior = (likelihood * prior) / evidence_prob
        return posterior

    @staticmethod
    def penalize_contradiction(prior: float, contradiction_strength: float = 0.5) -> float:
        """
        Reduces probability when evidence contradicts the hypothesis.
        """
        return prior * (1.0 - contradiction_strength)
