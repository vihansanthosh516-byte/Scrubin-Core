"""Unified objective function for all optimization decisions.

The simulator consists of many separate components (projection, Monte‑Carlo
risk, scoring, lineup optimisation, captain strategy, etc.).  Historically each
component produced its own “score” which led to contradictory decisions.

`lineup_objective` is the **single source of truth** – every optimizer,
strategy or decision‑making module should call this function instead of using any
custom heuristic.

The function is deliberately deterministic: it receives plain dictionaries
(`player`, `projection`) and a mode string and returns a float.  The same input
always produces the same output, guaranteeing replay safety.
"""

from __future__ import annotations

from typing import Dict, Any


def lineup_objective(player: Dict[str, Any], projection: Dict[str, Any], mode: str = "balanced") -> float:
    """Canonical utility used by every optimisation component.

    Parameters
    ----------
    player:
        Dictionary describing the candidate (e.g. a medical instrument, a
        procedural step, a team member, etc.).  Expected keys (defaults are
        provided when missing):
        * ``ownership_pct`` – proportion of current ownership/resource share.
        * ``price`` – cost or resource consumption associated with the player.
    projection:
        Dictionary containing the stochastic projection for the player.  Expected
        keys (defaults used if missing):
        * ``mean_ev`` – expected value (e.g. clinical benefit, EV, utility).
        * ``sigma`` – standard deviation (risk indicator).
        * ``start_probability`` – probability the player will be available at
          the start of the tick/phase.
    mode:
        "safe", "aggressive" or any other string interpreted as "balanced".
        Determines how risk (sigma) is penalised or rewarded.

    Returns
    -------
    float
        Deterministic utility score – higher is better.
    """
    # -----------------------------------------------------------------
    # 1️⃣ Extract values with safe defaults (deterministic for missing keys).
    # -----------------------------------------------------------------
    ev = float(projection.get("mean_ev", 0.0))
    sigma = float(projection.get("sigma", 0.0))
    start_p = float(projection.get("start_probability", 1.0))
    ownership = float(player.get("ownership_pct", 0.0))
    price = float(player.get("price", 0.0))

    # -----------------------------------------------------------------
    # 2️⃣ Base utility – expected value multiplied by the chance it will be
    #    present at the start of the phase.
    # -----------------------------------------------------------------
    score = ev * start_p

    # -----------------------------------------------------------------
    # 3️⃣ Risk adjustment – mode‑dependent weighting of the standard
    #    deviation.  The coefficients are deterministic and keep the overall
    #    function linear for replay safety.
    # -----------------------------------------------------------------
    if mode == "safe":
        score -= 0.6 * sigma
    elif mode == "aggressive":
        score += 0.3 * sigma
    else:  # "balanced" or any unknown mode
        score -= 0.3 * sigma

    # -----------------------------------------------------------------
    # 4️⃣ Ownership differential – encourages diversification and penalises
    #    overly concentrated resources.
    # -----------------------------------------------------------------
    if ownership < 5.0:
        score += 2.0
    elif ownership > 30.0:
        score -= 0.5

    # -----------------------------------------------------------------
    # 5️⃣ Budget efficiency pressure – higher price yields a modest positive
    #    boost, reflecting the fact that expensive resources are often
    #    high‑impact (the coefficient is deterministic).
    # -----------------------------------------------------------------
    score += 0.05 * price

    return score
