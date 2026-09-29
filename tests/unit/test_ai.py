import json
from types import SimpleNamespace

import httpx
import pytest
from scml.ai.runtime import explain
from scml.services.config import Settings


class Runtime:
    def __init__(self, output=None, error=None):
        self.output = output
        self.error = error

    def complete(self, model, evidence):
        if self.error:
            raise self.error
        return {"content": json.dumps(self.output), "model": model}


def settings(enabled=True):
    return SimpleNamespace(llm_enabled=enabled, llm_runtime="ollama")


def test_missing_evidence_abstains():
    result = explain(settings(), {}, "mine", Runtime(error=AssertionError("must not call")))
    assert result["status"] == "abstained"


@pytest.mark.parametrize(
    "runtime",
    [
        Runtime(error=httpx.ConnectError("offline")),
        Runtime({"summary": "bad", "evidence_ids": ["invented"], "recommended_action": "observe"}),
        Runtime({"summary": "missing schema"}),
    ],
)
def test_llm_failure_cannot_corrupt_state(service, trained, runtime):
    before = service.store.rows("runs")
    result = explain(settings(), {trained["id"]: {"metric": 1}}, "my-model", runtime)
    assert result["status"] == "abstained" and service.store.rows("runs") == before
    assert service.active("forecast") is None


def test_valid_narrative_cites_known_evidence():
    result = explain(
        settings(),
        {"run-a": {"gate": "passed"}},
        "my-model",
        Runtime(
            {
                "summary": "Review the candidate evidence.",
                "evidence_ids": ["run-a"],
                "recommended_action": "review_candidate",
            }
        ),
    )
    assert result["status"] == "explained" and result["telemetry"]["tool_calls"] == []


def test_disabled_ai_calls_nothing():
    result = explain(
        settings(False), {"a": {}}, "any", Runtime(error=AssertionError("must not call"))
    )
    assert result["status"] == "abstained"


def test_local_endpoint_only(tmp_path, monkeypatch):
    monkeypatch.setenv("SCML_LLM_ENABLED", "true")
    monkeypatch.setenv("SCML_LLM_URL", "https://cloud.example.com/v1")
    with pytest.raises(ValueError, match="local runtime"):
        Settings(tmp_path)


def test_no_model_is_preselected(tmp_path, monkeypatch):
    monkeypatch.delenv("SCML_LLM_MODEL", raising=False)
    assert Settings(tmp_path).llm_model == ""


@pytest.mark.parametrize("runtime", ["ollama", "openai-compatible"])
def test_http_runtime_uses_schema_and_local_endpoint(monkeypatch, runtime):
    from scml.ai.runtime import HTTPRuntime
    from scml.domain.schemas import Narrative

    original = httpx.Client
    observed = []
    content = json.dumps(
        {
            "summary": "Review the supplied evidence.",
            "evidence_ids": ["run-a"],
            "recommended_action": "observe",
        }
    )

    def handler(request):
        body = json.loads(request.content)
        observed.append((str(request.url), body))
        result = (
            {"message": {"content": content}, "model": "mine"}
            if runtime == "ollama"
            else {"choices": [{"message": {"content": content}}], "model": "mine"}
        )
        return httpx.Response(200, json=result)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    config = SimpleNamespace(llm_runtime=runtime, llm_url="http://127.0.0.1:11434")
    result = HTTPRuntime(config).complete("mine", {"run-a": {"gate": "passed"}})
    assert Narrative.model_validate_json(result["content"]).evidence_ids == ["run-a"]
    assert observed[0][1]["model"] == "mine"
    if runtime == "ollama":
        assert observed[0][1]["format"]["type"] == "object"
    else:
        assert observed[0][1]["response_format"]["type"] == "json_schema"


def test_local_http_runtime_does_not_follow_redirect(monkeypatch):
    from scml.ai.runtime import HTTPRuntime

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(302, headers={"Location": "https://external.invalid"})
            ),
            **kwargs,
        ),
    )
    config = SimpleNamespace(llm_runtime="ollama", llm_url="http://127.0.0.1:11434")
    with pytest.raises(httpx.HTTPStatusError):
        HTTPRuntime(config).complete("mine", {"a": {}})
