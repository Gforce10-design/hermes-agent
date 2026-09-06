"""``session/set_model`` with an explicit ``provider:model`` must keep that provider.

``_resolve_model_selection`` used to run provider auto-detection whenever the parsed
provider equalled the session's current provider -- which is exactly the case for
``openai-codex:gpt-6-astra`` on an openai-codex session. Auto-detection then found the
model in the OpenRouter catalog and re-routed the switch to openrouter, and with no
openrouter key the switch failed with "No LLM provider configured". ACP clients send the
prefixed id straight from ``availableModels``, so the explicit prefix has to win.
"""

import pytest

import hermes_cli.models as models_mod
from acp_adapter.server import HermesACPAgent


@pytest.fixture
def detect_to_openrouter(monkeypatch):
    calls = []

    def fake_detect(model, current_provider):
        calls.append((model, current_provider))
        return ("openrouter", f"openai/{model}")

    monkeypatch.setattr(models_mod, "detect_provider_for_model", fake_detect)
    return calls


def test_explicit_prefix_matching_current_provider_is_not_redetected(detect_to_openrouter):
    provider, model = HermesACPAgent._resolve_model_selection("openai-codex:gpt-6-astra", "openai-codex")
    assert (provider, model) == ("openai-codex", "gpt-6-astra")
    assert detect_to_openrouter == []


def test_explicit_prefix_to_other_provider_is_honored(detect_to_openrouter):
    provider, model = HermesACPAgent._resolve_model_selection("anthropic:claude-opus-5", "openai-codex")
    assert (provider, model) == ("anthropic", "claude-opus-5")
    assert detect_to_openrouter == []


def test_bare_model_still_auto_detects(detect_to_openrouter):
    provider, model = HermesACPAgent._resolve_model_selection("gpt-6-astra", "openai-codex")
    assert (provider, model) == ("openrouter", "openai/gpt-6-astra")
    assert detect_to_openrouter == [("gpt-6-astra", "openai-codex")]
