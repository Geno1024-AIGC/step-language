from __future__ import annotations

import argparse
import gzip
import html
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from . import __version__
from .model import Document, StepSyntaxError
from .parser import parse_file
from .render import render

GUIDE_ZH = """\
step-language 快速参考

元数据（放在第一个步骤之前）：
  @title 标题              必填
  @description 一句话说明
  @id doc-id               可选；默认取文件名
  @version 1.0             可选；版本变化会重置本地保存的进度
  @lang zh-CN              可选；zh 开头用中文界面，否则英文
  @accent #2563eb          可选；主题色
  @start step-id           可选；默认第一步

步骤：
  == step-id | 步骤标题

步骤内容：
  普通文字会成为一个段落，连续行会合并。
  - 无序列表项
  - [ ] 可勾选项目（进度会保存在浏览器本机）
  - [x] 默认勾选的项目
  > 提示文字
  ! 警告文字
  @time 约 5 分钟
  @img images/photo.jpg | 图片说明
  -> next-step-id          指定下一步；不写则按文档顺序
  ? 需要用户判断的问题
  * 选项一 -> target-step-id
  * 已解决 -> done          done 表示结束流程

行内格式：
  **粗体**  `代码`  [链接文字](https://example.com)

代码块：
  ```bash
  echo hello
  ```

注释：以 # 或 // 开头的整行。

命令：
  python3 -m steplang build examples/repair-computer.step
  python3 -m steplang check examples/repair-computer.step --strict
  python3 -m steplang serve examples
  python3 -m steplang guide
"""


def _warn(doc: Document) -> None:
    for warning in doc.warnings:
        print(f"warning: {warning}", file=sys.stderr)


def _summary(doc: Document) -> str:
    return (
        f"{doc.title} ({len(doc.steps)} steps, id={doc.id}, "
        f"v{doc.version}, lang={doc.lang})"
    )


def cmd_build(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.is_file():
        print(f"steplang: input file not found: {source}", file=sys.stderr)
        return 1

    try:
        doc = parse_file(source)
    except StepSyntaxError as exc:
        print(f"steplang: {exc}", file=sys.stderr)
        return 1
    _warn(doc)

    output = Path(args.output) if args.output else source.with_suffix(".html")
    if output.exists() and output.is_dir():
        output = output / (source.stem + ".html")
    if output.resolve() == source.resolve():
        print("steplang: refusing to overwrite the .step source", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)

    data = render(doc)
    encoded = data.encode("utf-8")
    output.write_text(data, encoding="utf-8")
    packed = len(gzip.compress(encoded, 9))
    print(
        f"wrote {output} ({len(encoded) / 1024:.1f} KiB, "
        f"gzip {packed / 1024:.1f} KiB, {len(doc.steps)} steps)"
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.is_file():
        print(f"steplang: input file not found: {source}", file=sys.stderr)
        return 1
    try:
        doc = parse_file(source)
    except StepSyntaxError as exc:
        print(f"steplang: {exc}", file=sys.stderr)
        return 1
    _warn(doc)
    print(f"ok: {_summary(doc)}")
    if args.strict and doc.warnings:
        return 1
    return 0


def _index_page(root: Path) -> str:
    files = sorted(root.rglob("*.step"))
    rows: list[str] = []
    for path in files:
        rel = path.relative_to(root)
        href = "/" + quote(rel.as_posix())
        try:
            doc = parse_file(path)
            detail = html.escape(f"{len(doc.steps)} steps · v{doc.version}")
            title = doc.title
        except StepSyntaxError as exc:
            detail = html.escape(str(exc))
            title = rel.as_posix()
        except OSError as exc:
            detail = html.escape(str(exc))
            title = rel.as_posix()
        rows.append(
            "<li>"
            f'<a href="{html.escape(href, quote=True)}">{html.escape(title)}</a>'
            f'<span class="path">{html.escape(rel.as_posix())}</span>'
            f"<span class=\"detail\">{detail}</span>"
            "</li>"
        )

    if not rows:
        rows.append('<li class="empty">当前目录下没有 .step 文件。</li>')

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>step-language</title>
<style>
:root{{color-scheme:light dark;--bg:#f4f6f9;--panel:#fff;--text:#17202b;--muted:#5f6b7a;--border:#dfe5ec;--accent:#2563eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0d1117;--panel:#151b23;--text:#e6edf3;--muted:#9aa7b8;--border:#283545;--accent:#7db2ff}}}}
*{{box-sizing:border-box}}body{{margin:0;padding:40px 20px;background:var(--bg);color:var(--text);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif}}
main{{max-width:780px;margin:0 auto}}h1{{margin:0 0 4px;font-size:28px}}p{{color:var(--muted);margin:0 0 24px}}
ul{{list-style:none;margin:0;padding:0;border:1px solid var(--border);border-radius:14px;overflow:hidden;background:var(--panel)}}
li{{display:grid;grid-template-columns:1fr auto;gap:2px 14px;padding:14px 18px;border-top:1px solid var(--border)}}li:first-child{{border-top:0}}
a{{color:var(--accent);font-weight:600;text-decoration:none}}a:hover{{text-decoration:underline}}
.path{{color:var(--muted);font:12px ui-monospace,monospace;align-self:center}}
.detail{{grid-column:1/-1;color:var(--muted);font-size:13px;overflow-wrap:anywhere}}
.empty{{display:block;color:var(--muted)}}
</style>
</head>
<body><main><h1>step-language</h1><p>{len(files)} 个步骤文档 · 点击打开</p><ul>{''.join(rows)}</ul></main></body>
</html>
"""


def _error_page(message: str, status: int) -> bytes:
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{status} · step-language</title>
<style>
body{{margin:0;padding:40px 20px;background:#f4f6f9;color:#17202b;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:760px;margin:0 auto}}h1{{font-size:24px}}pre{{padding:14px;overflow:auto;white-space:pre-wrap;background:#fff;border:1px solid #dfe5ec;border-radius:10px;color:#a32323}}
a{{color:#2563eb}}
@media(prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}pre{{background:#151b23;border-color:#283545;color:#ff9a9a}}a{{color:#7db2ff}}}}
</style></head>
<body><main><h1>{status} · 无法编译步骤文档</h1><pre>{html.escape(message)}</pre>
<p><a href="/">返回文档列表</a></p></main></body></html>""".encode("utf-8")


class StepServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], root: Path):
        self.root = root.resolve()
        super().__init__(address, StepHandler)


class StepHandler(BaseHTTPRequestHandler):
    server: StepServer

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(
            f"[{self.log_date_time_string()}] {self.client_address[0]} {fmt % args}\n"
        )

    def do_GET(self) -> None:
        self._handle(head=False)

    def do_HEAD(self) -> None:
        self._handle(head=True)

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        head: bool,
        cache: str = "no-store",
    ) -> None:
        compressible = (
            content_type.startswith("text/")
            or "javascript" in content_type
            or "json" in content_type
            or "svg" in content_type
        )
        encoded = ""
        if (
            compressible
            and len(body) >= 1024
            and "gzip" in self.headers.get("Accept-Encoding", "").lower()
        ):
            body = gzip.compress(body, 6)
            encoded = "gzip"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if compressible:
            self.send_header("Vary", "Accept-Encoding")
        if encoded:
            self.send_header("Content-Encoding", encoded)
        self.end_headers()
        if not head:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _resolve(self, path: str) -> Path | None:
        candidate = (self.server.root / path).resolve()
        try:
            candidate.relative_to(self.server.root)
        except ValueError:
            return None
        return candidate

    def _handle(self, *, head: bool) -> None:
        url = urlsplit(self.path)
        raw_path = unquote(url.path)
        if raw_path in ("", "/"):
            body = _index_page(self.server.root).encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8", head=head)
            return

        relative = raw_path.lstrip("/")
        target = self._resolve(relative)
        if target is None:
            self._send(403, b"Forbidden", "text/plain; charset=utf-8", head=head)
            return

        step_path: Path | None = None
        if target.is_file() and target.suffix == ".step":
            step_path = target
        elif not target.exists() and target.suffix == "":
            if (target.parent / (target.name + ".step")).is_file():
                step_path = target.parent / (target.name + ".step")

        if step_path is not None:
            try:
                doc = parse_file(step_path)
                for warning in doc.warnings:
                    print(f"warning: {warning}", file=sys.stderr)
                body = render(doc).encode("utf-8")
            except StepSyntaxError as exc:
                self._send(400, _error_page(str(exc), 400), "text/html; charset=utf-8", head=head)
                return
            except OSError as exc:
                self._send(500, _error_page(str(exc), 500), "text/html; charset=utf-8", head=head)
                return
            self._send(200, body, "text/html; charset=utf-8", head=head)
            return

        if target.is_file():
            try:
                body = target.read_bytes()
            except OSError as exc:
                self._send(500, _error_page(str(exc), 500), "text/plain; charset=utf-8", head=head)
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send(200, body, content_type, head=head, cache="public, max-age=300")
            return

        self._send(404, _error_page("404 Not Found", 404), "text/html; charset=utf-8", head=head)


def cmd_serve(args: argparse.Namespace) -> int:
    root = Path(args.directory)
    if not root.is_dir():
        print(f"steplang: directory not found: {root}", file=sys.stderr)
        return 1
    try:
        server = StepServer((args.host, args.port), root)
    except OSError as exc:
        print(f"steplang: cannot listen on {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 1
    host, port = server.server_address[:2]
    shown_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    print(f"serving {root.resolve()} at http://{shown_host}:{port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


def cmd_guide(_: argparse.Namespace) -> int:
    print(GUIDE_ZH.rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="steplang",
        description="Compile .step workflows into tiny, interactive, responsive HTML guides.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="compile a .step file into a standalone HTML file")
    build.add_argument("input", help="path to the .step source file")
    build.add_argument("-o", "--output", help="output HTML path (default: next to input)")
    build.set_defaults(func=cmd_build)

    check = sub.add_parser("check", help="parse and validate a .step file without building")
    check.add_argument("input", help="path to the .step source file")
    check.add_argument("--strict", action="store_true", help="exit non-zero when warnings exist")
    check.set_defaults(func=cmd_check)

    serve = sub.add_parser("serve", help="serve a directory of .step files with live compilation")
    serve.add_argument("directory", nargs="?", default=".", help="directory to serve (default: .)")
    serve.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    serve.set_defaults(func=cmd_serve)

    guide = sub.add_parser("guide", help="print a short DSL reference")
    guide.set_defaults(func=cmd_guide)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
