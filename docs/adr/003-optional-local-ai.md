# ADR 003: opt-in local narrative adapter

Status: accepted.

No numerical calculation or workflow state needs an LLM. Ship with AI disabled and no selected model. Provide an evidence-summary adapter for Ollama and local OpenAI-compatible runtimes. The operator chooses their installed model; no cloud provider or model license is implicitly required.

Schema/citation validation and abstention make failures visible. The adapter has no lifecycle mutation capability, shell execution or SQL tool. A narrative is an optional explanation, not an approval recommendation or deterministic metric source.

Costs: model-dependent structured-output compatibility and latency. A schema-valid summary can still be semantically wrong. Live model benchmarking requires the operator's chosen runtime/weights and must record their license and configuration.
