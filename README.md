# step-language

Turn a plain-text procedure into a small, interactive guide that works on a phone and offline.

[Live site](https://geno1024-aigc.github.io/step-language/) ·
[Interactive example](https://geno1024-aigc.github.io/step-language/examples/repair-computer/) ·
[中文说明](README.zh-CN.md)

`step-language` is a tiny DSL and static-site compiler for step-by-step procedures. Write a
`.step` file with checklists, questions, branches, tips, images, and code blocks. The compiler
produces one portable HTML file with no framework, no external fonts, and no runtime
dependencies. Images stay external and lazy-loaded, so the page is cheap to host and quick to
open on a slow connection.

The compiler uses only the Python standard library. The generated page uses vanilla CSS and
JavaScript.

> This project, including the compiler, runtime, documentation, and examples, is 100% AI-generated.

## Features

- **Branching flows** — ask a question with `?`, route answers with `* choice -> step`, and end
  with `done`.
- **Persistent progress** — checklist state is kept in `localStorage`, scoped by document ID and
  version. Bump `@version` to start fresh.
- **Responsive by default** — a step sidebar on desktop, a mobile drawer, and left/right keyboard
  navigation.
- **Low bandwidth** — the 8-step example is about 54 KB of HTML, or 14.4 KB gzipped. Images use
  lazy loading, so unrelated images do not delay the first view.
- **Comfortable reading** — automatic, light, and dark themes; print-all view; copy buttons for
  code; deep links to individual steps; reset progress.
- **Safe by default** — text is HTML-escaped, embedded JSON cannot break out of its script tag,
  and unsafe URL schemes such as `javascript:` are rejected.
- **No build toolchain** — Python 3.10+ and a browser are all you need.

## Quick start

```bash
git clone https://github.com/Geno1024-AIGC/step-language.git
cd step-language

python3 -m steplang check examples/repair-computer.step --strict
python3 -m steplang build examples/repair-computer.step -o dist/repair.html
python3 -m steplang serve examples
```

Open <http://127.0.0.1:8000/> for the live-compiling example index. The generated
`dist/repair.html` is a standalone page and can be hosted anywhere.

Install the `steplang` and `stepc` commands if you prefer:

```bash
python3 -m pip install -e .
steplang guide
```

## A small `.step` file

```step
@title Fix a PC that will not start
@description A short power and display checklist
@id fix-pc
@version 1.0.0
@lang en
@start safety
@accent #2563eb

== safety | Safety first
- [ ] Unplug the power cable
- [ ] Remove USB devices and peripherals
> Touch a grounded metal case before opening the machine.
! Stop and seek a technician if you smell burning or see damaged capacitors.

@time About 2 minutes
-> power

== power | Check the power path
? Does the power button produce a light, sound, or fan movement?
* Yes -> display
* No -> cable
* Not sure -> observe

== cable | Check the cable and adapter
- Try another known-good outlet
- Try another power cable or adapter
? Does it start now?
* Yes -> display
* Still no -> service

== display | Check the display
- Confirm the monitor input and cable
- Listen for fans or disk activity
? Is there still no picture?
* Yes -> service
* No, it boots -> done

== service | Ask for repair
Record the model, symptoms, and steps already tried.
```

Run `python3 -m steplang guide` for the full quick reference, or open the
[interactive example](https://geno1024-aigc.github.io/step-language/examples/repair-computer/).

## Examples

- [Repair a PC that will not start](https://geno1024-aigc.github.io/step-language/examples/repair-computer/)
- [Reinstall Windows](https://geno1024-aigc.github.io/step-language/examples/reinstall-windows/)

Both pages are generated from the `.step` files in `examples/`.

## Syntax overview

| Construct | Syntax |
| --- | --- |
| Metadata | `@title`, `@description`, `@id`, `@version`, `@lang`, `@accent`, `@start` |
| Step | `== step-id \| Step title` |
| List / checklist | `- item`, `- [ ] item`, `- [x] item` |
| Callout | `> note`, `! warning` |
| Time / image | `@time 5 minutes`, `@img images/photo.jpg \| Alt text` |
| Question / branch | `? question`, `* label -> step-id`, `* label -> done` |
| Navigation | `-> step-id`; omit it to continue in document order |
| Code | fenced code block |
| Inline | `**bold**`, `` `code` ``, `[text](https://example.com)` |

`check --strict` fails on warnings such as unreachable steps, empty steps, or self-loops.
Duplicate step IDs, unknown jump targets, and unsafe URLs are always errors.

## CLI

| Command | Purpose |
| --- | --- |
| `python3 -m steplang build FILE [-o OUT]` | Compile one `.step` file into a standalone HTML page. |
| `python3 -m steplang check FILE [--strict]` | Parse and validate without writing output. |
| `python3 -m steplang serve [DIR] [--port N]` | Serve a directory and compile `.step` files on request with gzip. |
| `python3 -m steplang guide` | Print a compact DSL reference. |

## GitHub Pages

The `Deploy Pages` workflow in `.github/workflows/pages.yml` runs the test suite, builds both
examples, copies the landing page from `web/`, and deploys `_site/` with GitHub Actions.

- Landing page: <https://geno1024-aigc.github.io/step-language/>
- PC repair example: <https://geno1024-aigc.github.io/step-language/examples/repair-computer/>
- Windows reinstall example: <https://geno1024-aigc.github.io/step-language/examples/reinstall-windows/>

For a fork, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions** once,
then push to `master`.

## Development

```bash
python3 -m unittest discover -s tests -t .
node --check steplang/assets/app.js   # optional, if Node.js is available
```

## Layout

```text
steplang/              compiler package
steplang/assets/       generated-page CSS and JavaScript
examples/              sample workflow and image
web/                   GitHub Pages landing page source
tests/                 unittest suite
.github/workflows/     Pages deployment workflow
```
