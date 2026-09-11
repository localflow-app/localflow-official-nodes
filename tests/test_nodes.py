import importlib.util
from pathlib import Path

from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment


ROOT = Path(__file__).resolve().parents[1]


def load_node(node_type):
    path = ROOT / node_type / "node.py"
    spec = importlib.util.spec_from_file_location(f"test_{node_type}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rich_text_writes_standard_relative_html(tmp_path, monkeypatch):
    module = load_node("rich_text")
    monkeypatch.setenv("MOZIKIT_WORKFLOW_DIR", str(tmp_path))
    environment = SandboxedEnvironment(loader=BaseLoader(), variable_start_string="{%", variable_end_string="%}", block_start_string="<@", comment_start_string="{##")

    class Node:
        config = {
            "content": environment.from_string("<p>Hello <b>{% name %}</b></p>").render(name="Mozikit"),
            "output_path": "artifacts/message.html",
            "output_var": "path",
        }

    result = module.execute(Node(), {})
    assert result["path"] == "artifacts/message.html"
    assert "Mozikit" in (tmp_path / result["path"]).read_text(encoding="utf-8")


def test_html_clipboard_payload_has_plain_fallback():
    module = load_node("clipboard_copy")
    html = "<p>Hello <b>Mozikit</b></p>"
    plain = module.html_to_plain_text(html)
    payload, fallback = module.build_cf_html(html, plain)
    assert plain == "Hello Mozikit"
    assert b"StartFragment:" in payload
    assert b"<b>Mozikit</b>" in payload
    assert fallback == "Hello Mozikit"
