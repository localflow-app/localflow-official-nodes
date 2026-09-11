"""Copy text/HTML files to the host clipboard without third-party packages."""

import html as html_module
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "p", "div", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")


def html_to_plain_text(value):
    parser = _TextExtractor()
    parser.feed(value)
    text = html_module.unescape("".join(parser.parts))
    return re.sub(r"\n[ \t]*\n+", "\n", text).strip()


def build_cf_html(html, plain_text):
    """Build the standard Windows CF_HTML byte payload and its fallback."""
    fragment = html
    source = "<html><body><!--StartFragment-->" + fragment + "<!--EndFragment--></body></html>"
    template = (
        "Version:0.9\r\nStartHTML:{start_html:010d}\r\nEndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_fragment:010d}\r\nEndFragment:{end_fragment:010d}\r\n"
    )
    empty = template.format(start_html=0, end_html=0, start_fragment=0, end_fragment=0).encode("utf-8")
    start_html = len(empty)
    start_fragment = start_html + len("<html><body><!--StartFragment-->".encode("utf-8"))
    body = source.encode("utf-8")
    end_fragment = start_fragment + len(fragment.encode("utf-8"))
    header = template.format(start_html=start_html, end_html=start_html + len(body), start_fragment=start_fragment, end_fragment=end_fragment).encode("utf-8")
    return header + body, plain_text


def _workflow_file(value):
    root = Path(os.environ.get("MOZIKIT_WORKFLOW_DIR", "")).resolve()
    if not root.exists():
        raise RuntimeError("MOZIKIT_WORKFLOW_DIR is not set; workflow execution context is missing")
    raw = str(value).replace("\\", os.sep).replace("/", os.sep)
    candidate = Path(raw).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes workflow directory: {value}") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"workflow file does not exist: {value}")
    return resolved


def _write_windows(html, plain_text):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    cf_unicode = 13
    cf_html = user32.RegisterClipboardFormatW("HTML Format")
    if not user32.OpenClipboard(None):
        raise RuntimeError("could not open the Windows clipboard (no interactive desktop session?)")
    handles = []
    try:
        if not user32.EmptyClipboard():
            raise RuntimeError("could not empty the Windows clipboard")
        def put(fmt, payload):
            size = len(payload)
            handle = kernel32.GlobalAlloc(0x0002, size)
            if not handle:
                raise RuntimeError("could not allocate clipboard memory")
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                kernel32.GlobalFree(handle)
                raise RuntimeError("could not lock clipboard memory")
            ctypes.memmove(pointer, payload, size)
            kernel32.GlobalUnlock(handle)
            if not user32.SetClipboardData(fmt, handle):
                kernel32.GlobalFree(handle)
                raise RuntimeError("could not set clipboard data")
            handles.append(handle)
        put(cf_unicode, (plain_text + "\0").encode("utf-16le"))
        put(cf_html, build_cf_html(html, plain_text)[0] + b"\0")
    finally:
        user32.CloseClipboard()


def _write_plain(plain_text):
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(plain_text)
        root.update()
        root.destroy()
    except Exception as exc:
        raise RuntimeError("clipboard_copy requires an interactive desktop session") from exc


def write_clipboard(html, plain_text):
    if sys.platform == "win32" and html is not None:
        _write_windows(html, plain_text)
    else:
        _write_plain(plain_text)


def execute(self, input_data: dict) -> dict:
    source_var = str(self.config.get("source_path_var") or "path")
    source = input_data.get(source_var) or self.config.get("source_path")
    if not source:
        raise ValueError(f"clipboard source path is missing (variable: {source_var})")
    source_file = _workflow_file(source)
    suffix = source_file.suffix.lower()
    raw = source_file.read_text(encoding="utf-8")
    html = raw if suffix in {".html", ".htm"} else None
    plain = html_to_plain_text(raw) if html is not None else raw
    write_clipboard(html, plain)
    output_var = str(self.config.get("output_var") or "path").strip() or "path"
    return {**input_data, output_var: source_file.relative_to(Path(os.environ["MOZIKIT_WORKFLOW_DIR"]).resolve()).as_posix()}
