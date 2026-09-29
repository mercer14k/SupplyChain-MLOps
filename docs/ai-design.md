# AI design: deterministic core, optional narratives

## Default execution

`SCML_LLM_ENABLED=false`. No runtime must be installed, no model is preselected, and no model download happens. NumPy models generate all forecasts, anomaly scores, metrics and drift values. Transactional service code determines all workflow state.

## Local runtime abstraction

`LocalRuntime.complete(model, evidence)` separates transport from business logic. `HTTPRuntime` supports Ollama `/api/chat` and a local OpenAI-compatible `/v1/chat/completions` protocol used by llama.cpp/vLLM. Every request supplies a JSON schema, a bounded output budget, deterministic sampling settings where supported, no tools, a 30-second timeout and a 128-KiB response limit. Redirects and environment proxies are disabled.

Example Compose configuration (model name stays user-selected):

```dotenv
SCML_LLM_ENABLED=true
SCML_LLM_RUNTIME=ollama
SCML_LLM_URL=http://host.docker.internal:11434
SCML_LLM_MODEL=
```

For a local compatible server:

```dotenv
SCML_LLM_ENABLED=true
SCML_LLM_RUNTIME=openai-compatible
SCML_LLM_URL=http://host.docker.internal:8080/v1
SCML_LLM_MODEL=
```

Restart with `docker compose up -d --force-recreate api`. For native development, export the same environment variables before starting the API and use `http://127.0.0.1:<port>`. Native Python does not implicitly read `.env`; Compose does.

Only loopback names or named local runtime services are allowed. Do not point the local server at a cloud proxy. Use an installed open-weight model whose license permits your use. There is no bundled model, no recommendation masquerading as a requirement and no automatic pull command. A model with poor structured-output support will abstain.

## Evidence and boundaries

The LLM receives a bounded run summary containing task, metrics, quality policy and dataset fingerprint. Imported content is untrusted data, never instructions. The schema requires a summary, evidence IDs and one of four read-only recommended actions. Unknown citations, malformed JSON, missing evidence, disabled AI and runtime failures return `abstained`. A valid schema is not a semantic factuality guarantee; users must compare the labeled narrative with its supporting evidence.

There are no generated shell commands, arbitrary SQL, state-changing AI tools, autonomous approval, or hidden chain-of-thought capture. Numbers rendered in the operations UI come from deterministic code, not narrative text.

Observable telemetry includes requested/resolved model, runtime, prompt template version, evidence IDs, empty tool-call list, latency, retries (zero), validation failures and usage if exposed by the runtime. Input data and role keys are excluded from logs.

## Evaluation

Unit tests inject fake runtime responses to verify citation validation, missing-evidence abstention, unavailable runtimes and unchanged deterministic state. HTTP transport tests exercise the payload contract without requiring a model. No real local model was installed or benchmarked during this delivery; this remains an optional release check.

References: [Ollama structured output](https://ollama.com/blog/structured-outputs), [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/).

For an explicitly enabled runtime, compare your installed models without changing business logic:

```bash
python scripts/benchmark_local_models.py --run-id <run-id> --models <local-model-one> <local-model-two>
```

The output records observed abstentions, validation failures, citations, usage and latency. It is not a scored factuality benchmark; no made-up local-model result is committed.
