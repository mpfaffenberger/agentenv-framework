"""A rubrics verifier built in code, as the A2A validator builds its own, judges with the configured ``judge`` model,
as one read from a task does."""

import pytest

from agent_env.config import reset_config
from agent_env.task_step.task_steps.verifiers.rubrics_verifier import RubricsVerifierTaskStep

CRITERIA = [{"id": "c1", "description": "Response says hello"}]


@pytest.fixture
def judge_role(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('[model]\ndefault = "agent-model"\n\n[model.roles]\njudge = "judge-model"\n')
    monkeypatch.setenv("AGENT_ENV_CONFIG", str(config))
    reset_config()
    yield
    reset_config()


def _built(**kwargs) -> RubricsVerifierTaskStep:
    return RubricsVerifierTaskStep(id="verify", version=None, criteria=CRITERIA, prompt_id="p1", **kwargs)


def test_a_verifier_built_in_code_judges_with_the_configured_judge_model(judge_role):
    assert _built().default_model == "judge-model"


def test_a_verifier_read_from_a_task_judges_with_the_configured_judge_model(judge_role):
    data = _built().to_dict()
    del data["default_model"]

    assert RubricsVerifierTaskStep.from_dict(data).default_model == "judge-model"


def test_a_model_the_step_names_wins_over_the_judge_role(judge_role):
    assert _built(default_model="named-model").default_model == "named-model"


def test_without_a_judge_role_the_judge_is_claude_sonnet():
    assert _built().default_model == "claude-sonnet-4-6"
