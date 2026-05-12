import random
from scrubin.rl.action_space import ClinicalAction
from scrubin.rl.rollout import monitor_policy, wait_policy, random_policy
from scrubin.learning.curriculum import (
    CurriculumTrainer, CurriculumLevel, CurriculumProgress, CurriculumResult,
    CANONICAL_CURRICULUM,
)
from scrubin.learning.selfplay import (
    SelfPlayRunner, SelfPlayConfig, SelfPlayRound, SelfPlayResult,
    IterativeSelfPlayTrainer, IterativeTrainingResult,
)
from scrubin.learning.scenario_generator import (
    ScenarioGenerator, ScenarioConfig, ScenarioBatch, GeneratedScenario,
    CANONICAL_SCENARIO_CONFIGS,
)


def test_curriculum_level_to_dict():
    level = CurriculumLevel(level_id="test", difficulty=0.5, max_ticks=50, description="test level", graduation_threshold=0.6)
    d = level.to_dict()
    assert d["level_id"] == "test"
    assert d["difficulty"] == 0.5


def test_curriculum_progress_to_dict():
    p = CurriculumProgress(level_id="test", attempts=3, best_score=0.8, mean_score=0.6, graduated=True)
    d = p.to_dict()
    assert d["attempts"] == 3
    assert d["graduated"] is True


def test_curriculum_result_to_dict():
    r = CurriculumResult(total_levels=5, levels_completed=3, final_score=0.7, progress=[])
    d = r.to_dict()
    assert d["total_levels"] == 5
    assert d["levels_completed"] == 3


def test_canonical_curriculum():
    assert len(CANONICAL_CURRICULUM) == 5
    difficulties = [l.difficulty for l in CANONICAL_CURRICULUM]
    for i in range(len(difficulties) - 1):
        assert difficulties[i] < difficulties[i + 1], "Curriculum should be ordered by difficulty"


def test_curriculum_trainer_evaluate_level():
    trainer = CurriculumTrainer(max_attempts_per_level=1, base_seed=42)
    level = CurriculumLevel(level_id="quick", difficulty=0.1, max_ticks=10, graduation_threshold=0.1, num_episodes=2)
    score = trainer.evaluate_level(wait_policy, level, base_seed=42)
    assert 0.0 <= score <= 1.0


def test_curriculum_trainer_run_level():
    trainer = CurriculumTrainer(max_attempts_per_level=1, base_seed=42)
    level = CurriculumLevel(level_id="quick", difficulty=0.1, max_ticks=10, graduation_threshold=0.01, num_episodes=2)
    progress = trainer.run_level(wait_policy, level, base_seed=42)
    assert progress.attempts == 1
    assert progress.best_score >= 0.0


def test_curriculum_trainer_run_curriculum():
    curriculum = [
        CurriculumLevel(level_id="l1", difficulty=0.1, max_ticks=10, graduation_threshold=0.01, num_episodes=2, seed_range=(0, 100)),
    ]
    trainer = CurriculumTrainer(curriculum=curriculum, max_attempts_per_level=1, base_seed=42)
    result = trainer.run_curriculum(wait_policy, policy_id="test")
    assert result.total_levels == 1
    assert result.policy_id == "test"


def test_curriculum_trainer_progress():
    trainer = CurriculumTrainer(max_attempts_per_level=1, base_seed=42)
    level = CurriculumLevel(level_id="test_level", difficulty=0.1, max_ticks=10, graduation_threshold=0.01, num_episodes=2)
    trainer.run_level(monitor_policy, level, base_seed=42)
    assert "test_level" in trainer.progress


def test_curriculum_trainer_reset():
    trainer = CurriculumTrainer(max_attempts_per_level=1, base_seed=42)
    level = CurriculumLevel(level_id="test_level", difficulty=0.1, max_ticks=10, graduation_threshold=0.01, num_episodes=2)
    trainer.run_level(monitor_policy, level, base_seed=42)
    trainer.reset()
    assert len(trainer.progress) == 0


def test_self_play_config_defaults():
    c = SelfPlayConfig()
    assert c.num_rounds == 10
    assert c.max_ticks == 50


def test_self_play_round_to_dict():
    r = SelfPlayRound(round_num=0, policy_a_reward=5.0, policy_b_reward=3.0, policy_a_survival=True, policy_b_survival=False, winner="a", seed=42)
    d = r.to_dict()
    assert d["round_num"] == 0
    assert d["winner"] == "a"


def test_self_play_result_to_dict():
    r = SelfPlayResult(num_rounds=10, wins_a=6, wins_b=3, draws=1, policy_a_id="a", policy_b_id="b", final_policy_a_win_rate=0.6)
    d = r.to_dict()
    assert d["wins_a"] == 6
    assert d["final_policy_a_win_rate"] == 0.6


def test_self_play_runner_basic():
    runner = SelfPlayRunner(config=SelfPlayConfig(num_rounds=3, max_ticks=10, base_seed=42))
    result = runner.play(monitor_policy, wait_policy, policy_a_id="monitor", policy_b_id="wait")
    assert result.num_rounds == 3
    assert result.wins_a + result.wins_b + result.draws == 3
    assert 0.0 <= result.final_policy_a_win_rate <= 1.0


def test_self_play_runner_same_policy():
    runner = SelfPlayRunner(config=SelfPlayConfig(num_rounds=3, max_ticks=10, base_seed=42))
    result = runner.play(monitor_policy, monitor_policy, policy_a_id="m1", policy_b_id="m2")
    assert result.num_rounds == 3
    assert result.draws == 3


def test_self_play_runner_previous():
    runner = SelfPlayRunner(config=SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=42))
    result = runner.play_against_previous(monitor_policy, wait_policy, current_id="current", previous_id="prev")
    assert result.policy_a_id == "current"
    assert result.policy_b_id == "prev"


def test_iterative_training_result_to_dict():
    r = IterativeTrainingResult(num_iterations=3, self_play_results=[], policy_history=["v1", "v2", "v3"], improvement_curve=[0.5, 0.6, 0.7])
    d = r.to_dict()
    assert d["num_iterations"] == 3
    assert d["final_win_rate"] == 0.7


def test_iterative_self_play_trainer():
    trainer = IterativeSelfPlayTrainer(config=SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=42))
    result = trainer.train(
        initial_policy=monitor_policy,
        num_iterations=3,
        base_policy_id="test_sp",
        initial_seed=42,
    )
    assert result.num_iterations == 3
    assert len(result.policy_history) == 3
    assert len(result.improvement_curve) == 3


def test_iterative_self_play_registry():
    trainer = IterativeSelfPlayTrainer(config=SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=42))
    trainer.train(initial_policy=monitor_policy, num_iterations=2, base_policy_id="reg_test")
    reg = trainer.registry
    assert "reg_test" in reg.list_policies()
    versions = reg.list_versions("reg_test")
    assert len(versions) >= 2


def test_iterative_self_play_with_updater():
    def dummy_updater(current, previous, traj_curr, traj_prev):
        return current
    trainer = IterativeSelfPlayTrainer(
        config=SelfPlayConfig(num_rounds=2, max_ticks=10, base_seed=42),
        updater=dummy_updater,
    )
    result = trainer.train(initial_policy=monitor_policy, num_iterations=3, base_policy_id="up_test")
    assert result.num_iterations == 3


def test_scenario_config_to_dict():
    c = ScenarioConfig(scenario_id="test", description="test scenario", difficulty=0.5, max_ticks=50, seed_offset=1000)
    d = c.to_dict()
    assert d["scenario_id"] == "test"
    assert d["difficulty"] == 0.5


def test_scenario_batch_to_dict():
    configs = [ScenarioConfig(scenario_id="s1", description="s1", difficulty=0.3)]
    b = ScenarioBatch(batch_id="b1", configs=configs, total_scenarios=1)
    d = b.to_dict()
    assert d["batch_id"] == "b1"
    assert d["total_scenarios"] == 1


def test_generated_scenario_to_dict():
    gs = GeneratedScenario(scenario_id="gs1", seed=42, difficulty=0.5, metadata={"max_ticks": 50})
    d = gs.to_dict()
    assert d["scenario_id"] == "gs1"
    assert d["seed"] == 42


def test_canonical_scenario_configs():
    assert len(CANONICAL_SCENARIO_CONFIGS) == 7
    for c in CANONICAL_SCENARIO_CONFIGS:
        assert 0.0 <= c.difficulty <= 1.0
        assert c.max_ticks > 0


def test_scenario_generator_generate():
    gen = ScenarioGenerator(base_seed=0)
    config = ScenarioConfig(scenario_id="test", description="test", difficulty=0.5, max_ticks=50, seed_offset=0)
    scenarios = gen.generate(config, count=5)
    assert len(scenarios) == 5
    assert scenarios[0].scenario_id == "test_0"
    assert scenarios[4].scenario_id == "test_4"


def test_scenario_generator_batch():
    gen = ScenarioGenerator(base_seed=0)
    batch = gen.generate_batch(count_per_config=3)
    assert batch.total_scenarios == len(CANONICAL_SCENARIO_CONFIGS) * 3


def test_scenario_generator_curriculum():
    gen = ScenarioGenerator(base_seed=0)
    configs = gen.generate_curriculum_batch(num_levels=4, scenarios_per_level=2)
    assert len(configs) == 4
    for i in range(len(configs) - 1):
        assert configs[i].difficulty < configs[i + 1].difficulty


def test_scenario_generator_adversarial():
    random.seed(42)
    gen = ScenarioGenerator(base_seed=0)
    configs = gen.generate_adversarial(base_difficulty=0.5, num_scenarios=5)
    assert len(configs) == 5
    for c in configs:
        assert 0.0 <= c.difficulty <= 1.0


def test_scenario_generator_configs_property():
    gen = ScenarioGenerator(base_seed=0)
    configs = gen.configs
    assert len(configs) == len(CANONICAL_SCENARIO_CONFIGS)


def test_scenario_generator_num_configs():
    gen = ScenarioGenerator(base_seed=0)
    assert gen.num_configs == len(CANONICAL_SCENARIO_CONFIGS)


TESTS = [
    (k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
]
