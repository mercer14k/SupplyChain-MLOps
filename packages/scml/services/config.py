import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse


class Settings:
    def __init__(self, root=None):
        self.root = Path(root or os.getenv("SCML_STATE_DIR", ".runtime"))
        self.root.mkdir(parents=True, exist_ok=True)
        token_file = self.root / "credentials.json"
        if not token_file.exists():
            credentials = {
                "operator": secrets.token_urlsafe(32),
                "reviewer": secrets.token_urlsafe(32),
            }
            try:
                fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    json.dump(credentials, f)
            except FileExistsError:
                pass
        saved = json.loads(token_file.read_text())
        self.tokens = {
            role: os.getenv("SCML_" + role.upper() + "_TOKEN") or saved[role]
            for role in ("operator", "reviewer")
        }
        if self.tokens["operator"] == self.tokens["reviewer"] or any(
            len(v) < 24 for v in self.tokens.values()
        ):
            raise ValueError(
                "Distinct operator/reviewer tokens of at least 24 characters are required"
            )
        self.llm_enabled = os.getenv("SCML_LLM_ENABLED", "false").lower() == "true"
        self.llm_runtime = os.getenv("SCML_LLM_RUNTIME", "ollama")
        self.llm_url = os.getenv("SCML_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
        self.llm_model = os.getenv("SCML_LLM_MODEL", "")
        if self.llm_enabled:
            url = urlparse(self.llm_url)
            allowed = {
                "localhost",
                "127.0.0.1",
                "::1",
                "host.docker.internal",
                "ollama",
                "llama",
                "vllm",
            }
            if (
                url.scheme not in ("http", "https")
                or url.hostname not in allowed
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in ("", "/v1")
            ):
                raise ValueError(
                    "LLM endpoint must be a local runtime URL without credentials or query strings"
                )
            if self.llm_runtime not in ("ollama", "openai-compatible"):
                raise ValueError("Use ollama or openai-compatible local runtime")
