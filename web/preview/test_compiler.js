#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const StepCompiler = require("./compiler.js");

const root = path.resolve(__dirname, "../..");
const files = [
  "examples/repair-computer.step",
  "examples/reinstall-windows.step",
];
const python = process.env.PYTHON || "python3";
const pythonScript = [
  "import json, sys",
  "from pathlib import Path",
  "from steplang.parser import parse",
  "p = Path(sys.argv[1])",
  "d = parse(p.read_text(encoding='utf-8'), source=str(p), default_id=p.stem)",
  "print(json.dumps({'doc': d.to_dict(), 'warnings': d.warnings}, ensure_ascii=False))",
].join("\n");

function pythonResult(file) {
  const output = execFileSync(python, ["-c", pythonScript, file], {
    cwd: root,
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function stepToDict(step) {
  return {
    id: step.id,
    title: step.title,
    next: step.next,
    time: step.time,
    blocks: step.blocks,
  };
}

function docToDict(doc) {
  return {
    id: doc.id,
    title: doc.title,
    description: doc.description,
    version: doc.version,
    lang: doc.lang,
    accent: doc.accent,
    start: doc.start,
    steps: doc.steps.map(stepToDict),
  };
}

for (const file of files) {
  const text = fs.readFileSync(path.join(root, file), "utf8");
  const doc = StepCompiler.parseStep(text, {
    source: file,
    defaultId: path.basename(file, path.extname(file)),
  });
  const expected = pythonResult(file);

  assert.deepEqual(docToDict(doc), expected.doc, `${file}: document data differs`);
  assert.deepEqual(doc.warnings, expected.warnings, `${file}: warnings differ`);

  const html = StepCompiler.renderDocument(doc, { css: "", js: "" });
  assert.match(html, /<title>/, `${file}: rendered HTML has no title`);
  assert.match(html, /id="step-data"/, `${file}: rendered HTML has no document data`);
  console.log(`ok ${file} (${doc.steps.length} steps)`);
}

assert.throws(
  () =>
    StepCompiler.parseStep(
      ["@title Broken", "", "== start | Start", "-> missing"].join("\n"),
      { source: "broken.step" },
    ),
  /unknown target step 'missing'/,
);
console.log("compiler.js matches the Python parser");
