"""`agent-env a2a-agent put --published`: an agent registered over the image a release published for a shipped agent."""

import importlib

import pytest
from click.testing import CliRunner

from agent_env.a2a_agent import A2AAgent
from agent_env.artifact.store import get_artifact_store
from agent_env.cli import cli
from agent_env.env.published_images import PublishedImage
from agent_env.store.base import NotFoundError

put_module = importlib.import_module("agent_env.cli.a2a_agent.put")
DIGEST = "sha256:" + "a" * 64


@pytest.fixture
def shipped(tmp_path, monkeypatch, local_stores):
    """A shipped claude-code agent folder, and a release that published its image under ``DIGEST``."""
    folder = tmp_path / "agents" / "claude-code"
    folder.mkdir(parents=True)
    (folder / "Dockerfile").write_text("FROM scratch\nCOPY a2a_server.py /\n")
    (folder / "a2a_server.py").write_text("print('ok')\n")
    image = PublishedImage("agentenv-claude-code", folder / "Dockerfile")
    monkeypatch.setattr(put_module, "AGENT_IMAGES", (image,))
    monkeypatch.setattr(put_module, "published_digest", lambda published: DIGEST)
    return image


def _put(*args):
    return CliRunner().invoke(cli, ["a2a-agent", "put", "--id", "claude-code-cli", *args, "--skip-validation"])


def test_published_registers_the_released_image_by_tag_and_digest_with_the_folder_as_its_context(shipped):
    result = _put("--published", "claude-code")

    assert result.exit_code == 0, result.output
    agent = A2AAgent.get("claude-code-cli")
    image = get_artifact_store().get(agent.docker_image_artifact.id, agent.docker_image_artifact.version)
    assert image.image_name == shipped.ref() and image.image_name.startswith("ghcr.io/scaleapi/agentenv-claude-code:src-")
    assert image.image_digest == DIGEST
    assert image.build_context_object_url
    assert image.source_digest == "sha256:" + shipped.tag().removeprefix("src-")
    assert not image.context_only
    assert f"{shipped.ref()}@{DIGEST}" in result.output


def test_published_refuses_when_no_image_is_published_for_the_installed_sources(shipped, monkeypatch):
    monkeypatch.setattr(put_module, "published_digest", lambda published: None)

    result = _put("--published", "claude-code")

    assert result.exit_code == 1
    assert "no image is published" in result.output and shipped.ref() in result.output
    assert get_artifact_store().next_version("claude-code-cli__agent_image") == 1
    with pytest.raises(NotFoundError):
        A2AAgent.get("claude-code-cli")


def test_published_names_the_agents_it_can_register(shipped):
    result = _put("--published", "pi")

    assert result.exit_code == 1
    assert "publishes no image for 'pi'" in result.output and "claude-code" in result.output


@pytest.mark.parametrize("other", [["--image-ref", "ghcr.io/acme/agent:1"], ["--dockerfile", "{dockerfile}"]])
def test_published_is_one_of_the_image_sources(shipped, other):
    args = [arg.format(dockerfile=shipped.dockerfile) for arg in other]

    result = _put("--published", "claude-code", *args)

    assert result.exit_code == 1
    assert "exactly one of --dockerfile, --image-ref and --published" in result.output
