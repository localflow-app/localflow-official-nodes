"""Create a portable HTML artifact from inline content or an HTML source file."""

import os
from pathlib import Path


def _path(value, *, write=False, exists=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty string")
    root = Path(os.environ.get("MOZIKIT_WORKFLOW_DIR", "")).resolve()
    if not root.exists():
        raise RuntimeError("MOZIKIT_WORKFLOW_DIR is not set; workflow execution context is missing")
    raw = value.replace("\\", os.sep).replace("/", os.sep)
    candidate = Path(raw).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes workflow directory: {value}") from exc
    if exists and not resolved.is_file():
        raise FileNotFoundError(f"workflow file does not exist: {value}")
    if write:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def execute(self, input_data: dict) -> dict:
    source_path = str(self.config.get("source_path") or "").strip()
    if source_path:
        content = _path(source_path, exists=True).read_text(encoding="utf-8")
    else:
        content = str(self.config.get("content") or "")

    output_path = str(self.config.get("output_path") or "artifacts/rich_text.html")
    output_file = _path(output_path, write=True)
    output_file.write_text(content, encoding="utf-8")
    relative_path = output_file.relative_to(Path(os.environ["MOZIKIT_WORKFLOW_DIR"]).resolve()).as_posix()
    output_var = str(self.config.get("output_var") or "path").strip() or "path"
    return {**input_data, output_var: relative_path}
