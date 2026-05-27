import pytest
from scrubin.control_plane.control.adversarial_controller import AdversarialController


def test_control_signal_basic():
    controller = AdversarialController()
    signal = controller.compute_control(
        metrics={"stability": 0.9, "drift": 0.1, "variance": 0.2},
        regime="CONVERGENT",
    )
    # Ensure signal fields exist and are within reasonable bounds.
    assert isinstance(signal.adversary_scale, float)
    assert 0.0 <= signal.adversary_scale <= 2.0
    assert isinstance(signal.stability_bias, float)


def test_control_chaotic_response():
    controller = AdversarialController()
    signal = controller.compute_control(
        metrics={"stability": 0.2, "drift": 0.8, "variance": 1.5},
        regime="CHAOTIC",
    )
    assert signal.damping_factor > 0.0
    assert signal.stability_bias > 0.0
    # adversary_scale should be reduced for chaotic regime
    assert signal.adversary_scale < 1.0
