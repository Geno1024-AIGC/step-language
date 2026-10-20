from __future__ import annotations

import hashlib
import re
import textwrap
from pathlib import Path

from .inline import render_inline, validate_url
from .model import Block, Document, Step, StepSyntaxError

_META = re.compile(r"^@([A-Za-z][A-Za-z0-9_-]*)[ \t]*(.*)$")
_STEP = re.compile(r"^==[ \t]+([A-Za-z0-9][A-Za-z0-9_-]*)[ \t]*\|[ \t]*(.+?)[ \t]*$")
_STEP_ANY = re.compile(r"^==\b.*$")
_OPTION = re.compile(r"^\*[ \t]+(.+?)[ \t]+->[ \t]+([A-Za-z0-9][A-Za-z0-9_-]*)[ \t]*$")
_NEXT = re.compile(r"^->[ \t]+([A-Za-z0-9][A-Za-z0-9_-]*)[ \t]*$")
_TIME = re.compile(r"^@time[ \t]+(.+?)[ \t]*$")
_IMG = re.compile(r"^@img[ \t]+(.+?)[ \t]*$")
_CHECK = re.compile(r"^-[ \t]+\[([ xX])\][ \t]*(.*)$")
_BULLET = re.compile(r"^-[ \t]+(.*)$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_LANG = re.compile(r"^[A-Za-z0-9-]+$")
_ACCENT = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_COMMENT = re.compile(r"^(?:#|//)")
_FENCE_LANG = re.compile(r"^[A-Za-z0-9_+-]*$")
_KNOWN_META = {"title", "description", "id", "version", "lang", "accent", "start"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")
    return slug or "document"


def parse(
    text: str,
    *,
    source: str = "<input>",
    default_id: str = "",
) -> Document:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    meta: dict[str, tuple[str, int]] = {}
    steps: list[Step] = []
    seen_ids: set[str] = set()
    targets: list[tuple[str, int, str]] = []
    warnings: list[str] = []
    current: Step | None = None
    check_seq = 0
    first_step_line = 0
    doc_title = ""

    def fail(message: str, line: int | None = None, raw: str = "") -> StepSyntaxError:
        return StepSyntaxError(message, line=line, source=source, text=raw.strip())

    def add_warning(message: str, line: int | None = None) -> None:
        if line is None:
            warnings.append(message)
        else:
            warnings.append(f"{source}:{line}: {message}")

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line_no = i + 1
        s = raw.strip()

        if not s or _COMMENT.match(s):
            i += 1
            continue

        if s.startswith("=="):
            if current is not None and not current.blocks and current.next is None:
                add_warning(f"step '{current.id}' has no content", current.line)
            match = _STEP.match(s)
            if not match:
                raise fail(
                    "invalid step header; use '== step-id | Title'",
                    line_no,
                    raw,
                )
            step_id, title = match.group(1), match.group(2).strip()
            if step_id == "done":
                raise fail("'done' is a reserved step id", line_no, raw)
            if step_id in seen_ids:
                raise fail(f"duplicate step id '{step_id}'", line_no, raw)
            if not title:
                raise fail("step title cannot be empty", line_no, raw)
            if current is None:
                first_step_line = line_no
                doc_title = meta.get("title", ("", line_no))[0].strip()
            seen_ids.add(step_id)
            current = Step(
                id=step_id,
                title=title,
                line=line_no,
            )
            steps.append(current)
            check_seq = 0
            i += 1
            continue

        if current is None:
            match = _META.match(s)
            if not match:
                if _STEP_ANY.match(s):
                    raise fail("invalid step header; use '== step-id | Title'", line_no, raw)
                raise fail("expected metadata (@title ...) or a step header ('== id | Title')", line_no, raw)
            key, value = match.group(1).lower(), match.group(2).strip()
            if key not in _KNOWN_META:
                add_warning(f"unknown metadata '@{key}' ignored", line_no)
                i += 1
                continue
            if key in meta:
                raise fail(f"duplicate metadata '@{key}'", line_no, raw)
            meta[key] = (value, line_no)
            i += 1
            continue

        if _STEP_ANY.match(s):
            raise fail("invalid step header; use '== step-id | Title'", line_no, raw)

        if s.startswith("```"):
            lang = s[3:].strip()
            if lang and not _FENCE_LANG.match(lang):
                lang = ""
            j = i + 1
            code_lines: list[str] = []
            while j < n and lines[j].strip() != "```":
                code_lines.append(lines[j])
                j += 1
            if j >= n:
                raise fail("unterminated code fence", line_no, raw)
            code = textwrap.dedent("\n".join(code_lines)).strip("\n")
            current.blocks.append(Block("code", {"lang": lang, "text": code}))
            i = j + 1
            continue

        if s.startswith("? "):
            prompt = s[2:].strip()
            if not prompt:
                raise fail("choice prompt cannot be empty", line_no, raw)
            if current.has_choices:
                raise fail("a step can contain only one choice block", line_no, raw)
            options: list[dict[str, str]] = []
            j = i + 1
            while j < n:
                opt = lines[j].strip()
                if not opt or _COMMENT.match(opt):
                    j += 1
                    continue
                match = _OPTION.match(opt)
                if match:
                    label, target = match.group(1).strip(), match.group(2)
                    if not label:
                        raise fail("choice label cannot be empty", j + 1, lines[j])
                    options.append(
                        {
                            "label": render_inline(label, source=source, line=j + 1),
                            "target": target,
                        }
                    )
                    targets.append((target, j + 1, lines[j]))
                    j += 1
                    continue
                if opt.startswith("* "):
                    raise fail(
                        "invalid choice; use '* label -> target-step-id'",
                        j + 1,
                        lines[j],
                    )
                break
            if not options:
                raise fail(
                    "choice prompt needs at least one option ('* label -> target-step-id')",
                    line_no,
                    raw,
                )
            current.blocks.append(
                Block(
                    "choice",
                    {
                        "id": f"{current.id}-q",
                        "prompt": render_inline(prompt, source=source, line=line_no),
                        "options": options,
                    },
                )
            )
            i = j
            continue

        if s.startswith("* "):
            raise fail("choice option without a preceding '? prompt'", line_no, raw)

        if s.startswith("->"):
            match = _NEXT.match(s)
            if not match:
                raise fail("invalid continuation; use '-> step-id'", line_no, raw)
            if current.next is not None:
                raise fail("duplicate '->' continuation in this step", line_no, raw)
            target = match.group(1)
            current.next = target
            targets.append((target, line_no, raw))
            i += 1
            continue

        if s.startswith("@img "):
            match = _IMG.match(s)
            if not match:
                raise fail("invalid image; use '@img path | alt text'", line_no, raw)
            src, sep, alt = match.group(1).partition("|")
            src = src.strip()
            alt = alt.strip() if sep else ""
            if not src:
                raise fail("image path cannot be empty", line_no, raw)
            validate_url(src, kind="image", source=source, line=line_no, text=raw)
            current.blocks.append(
                Block(
                    "img",
                    {
                        "src": src,
                        "alt": alt,
                        "caption": render_inline(alt, source=source, line=line_no) if alt else "",
                    },
                )
            )
            i += 1
            continue

        if s.startswith("@time "):
            match = _TIME.match(s)
            if not match:
                raise fail("invalid time estimate; use '@time 5 min'", line_no, raw)
            if current.time is not None:
                raise fail("duplicate '@time' in this step", line_no, raw)
            current.time = match.group(1).strip()
            i += 1
            continue

        if s.startswith("@"):
            raise fail("unknown step directive (supported: @time, @img)", line_no, raw)

        if s.startswith("> "):
            html = render_inline(s[2:].strip(), source=source, line=line_no)
            if current.blocks and current.blocks[-1].kind == "tip":
                current.blocks[-1].data["html"] += " " + html
            else:
                current.blocks.append(Block("tip", {"html": html}))
            i += 1
            continue

        if s.startswith("! "):
            html = render_inline(s[2:].strip(), source=source, line=line_no)
            if current.blocks and current.blocks[-1].kind == "warn":
                current.blocks[-1].data["html"] += " " + html
            else:
                current.blocks.append(Block("warn", {"html": html}))
            i += 1
            continue

        check = _CHECK.match(s)
        if check:
            checked = check.group(1).lower() == "x"
            content = check.group(2).strip()
            if not content:
                raise fail("checklist item needs text", line_no, raw)
            item = {
                "id": f"{current.id}-c{check_seq}",
                "checked": checked,
                "html": render_inline(content, source=source, line=line_no),
            }
            check_seq += 1
            if current.blocks and current.blocks[-1].kind == "checks":
                current.blocks[-1].data["items"].append(item)
            else:
                current.blocks.append(Block("checks", {"items": [item]}))
            i += 1
            continue

        bullet = _BULLET.match(s)
        if bullet:
            content = bullet.group(1).strip()
            if not content:
                raise fail("bullet item needs text", line_no, raw)
            html = render_inline(content, source=source, line=line_no)
            if current.blocks and current.blocks[-1].kind == "ul":
                current.blocks[-1].data["items"].append(html)
            else:
                current.blocks.append(Block("ul", {"items": [html]}))
            i += 1
            continue

        parts = [s]
        j = i + 1
        while j < n:
            nxt = lines[j].strip()
            if not nxt:
                break
            if _is_special(nxt):
                break
            parts.append(nxt)
            j += 1
        paragraph = " ".join(parts)
        current.blocks.append(
            Block("p", {"html": render_inline(paragraph, source=source, line=line_no)})
        )
        i = j

    if not steps:
        raise fail("document has no steps", None)
    if not steps[-1].blocks and steps[-1].next is None:
        add_warning(f"step '{steps[-1].id}' has no content", steps[-1].line)
    if not doc_title:
        if "title" in meta:
            title_line = meta["title"][1]
            raise fail("document title cannot be empty", title_line, lines[title_line - 1])
        raise fail("missing '@title' before the first step", first_step_line, lines[first_step_line - 1])

    doc_id = meta.get("id", ("", 0))[0].strip()
    if doc_id:
        if not _ID.match(doc_id):
            line = meta["id"][1]
            raise fail("document id may only contain letters, digits, '_' and '-'", line, lines[line - 1])
    else:
        doc_id = _slug(default_id) if default_id else ""
        if not doc_id:
            doc_id = "doc-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

    version = meta.get("version", ("1", 0))[0].strip() or "1"
    lang = meta.get("lang", ("zh-CN", 0))[0].strip() or "zh-CN"
    if not _LANG.match(lang):
        line = meta["lang"][1]
        raise fail("invalid language tag", line, lines[line - 1])

    accent = meta.get("accent", ("#2563eb", 0))[0].strip() or "#2563eb"
    if not _ACCENT.match(accent):
        line = meta["accent"][1]
        raise fail("accent must be a hex color such as #2563eb", line, lines[line - 1])

    description = meta.get("description", ("", 0))[0].strip()

    step_ids = {step.id for step in steps}
    for target, line_no, raw in targets:
        if target != "done" and target not in step_ids:
            raise fail(f"unknown target step '{target}'", line_no, raw)

    start = meta.get("start", ("", 0))[0].strip() or steps[0].id
    if start not in step_ids:
        line = meta.get("start", ("", 0))[1]
        raise fail(f"unknown start step '{start}'", line, lines[line - 1] if line else "")

    for index, step in enumerate(steps):
        if step.next is None:
            if step.has_choices:
                step.next = None
            elif index + 1 < len(steps):
                step.next = steps[index + 1].id
            else:
                step.next = "done"
        if step.next == step.id:
            add_warning(f"step '{step.id}' continues to itself", step.line)
        for block in step.blocks:
            if block.kind == "choice":
                for option in block.data["options"]:
                    if option["target"] == step.id:
                        add_warning(f"step '{step.id}' has a choice that loops back to itself", step.line)
                        break

    reachable: set[str] = set()
    stack = [start]
    while stack:
        step_id = stack.pop()
        if step_id in reachable or step_id not in step_ids:
            continue
        reachable.add(step_id)
        step = next(item for item in steps if item.id == step_id)
        if step.next and step.next != "done":
            stack.append(step.next)
        for block in step.blocks:
            if block.kind == "choice":
                for option in block.data["options"]:
                    if option["target"] != "done":
                        stack.append(option["target"])
    for step in steps:
        if step.id not in reachable:
            add_warning(f"step '{step.id}' is not reachable from '{start}'", step.line)

    doc = Document(
        title=doc_title,
        id=doc_id,
        description=description,
        version=version,
        lang=lang,
        accent=accent,
        start=start,
        steps=steps,
        warnings=warnings,
    )
    return doc


def _is_special(line: str) -> bool:
    return (
        line.startswith("==")
        or line.startswith("->")
        or line.startswith("```")
        or line.startswith("@")
        or line.startswith("? ")
        or line.startswith("* ")
        or line.startswith("> ")
        or line.startswith("! ")
        or line.startswith("- ")
        or bool(_COMMENT.match(line))
    )


def parse_file(path: str | Path) -> Document:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse(text, source=str(path), default_id=path.stem)
