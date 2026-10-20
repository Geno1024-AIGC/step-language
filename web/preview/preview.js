(() => {
  "use strict";

  const DEFAULT_SAMPLE = "repair-computer.step";
  const MAX_FILE_BYTES = 1024 * 1024;
  const $ = (id) => document.getElementById(id);

  const el = {
    source: $("source"),
    fileName: $("file-name"),
    status: $("compile-status"),
    stats: $("preview-stats"),
    diagnostics: $("diagnostics"),
    dropZone: $("drop-zone"),
    fileInput: $("file-input"),
    reset: $("reset-sample"),
    download: $("download"),
    openTab: $("open-tab"),
    preview: $("preview"),
    frameWrap: $("frame-wrap"),
    placeholder: $("placeholder"),
    error: $("preview-error"),
    errorText: $("preview-error-text"),
  };
  const sampleButtons = Array.from(document.querySelectorAll("[data-sample]"));
  const viewButtons = Array.from(document.querySelectorAll("[data-view]"));

  const state = {
    assets: null,
    samples: new Map(),
    name: DEFAULT_SAMPLE,
    currentSample: DEFAULT_SAMPLE,
    html: "",
    doc: null,
    timer: 0,
  };

  function setStatus(text, kind) {
    el.status.textContent = text;
    el.status.dataset.state = kind;
  }

  function setStats(text) {
    el.stats.textContent = text;
  }

  function setSampleActive(file) {
    for (const button of sampleButtons) {
      button.setAttribute("aria-pressed", String(button.dataset.sample === file));
    }
  }

  function clearDiagnostics() {
    el.diagnostics.hidden = true;
    el.diagnostics.className = "diagnostics";
    el.diagnostics.replaceChildren();
  }

  function showWarningList(warnings) {
    if (!warnings.length) {
      clearDiagnostics();
      return;
    }

    const heading = document.createElement("p");
    heading.textContent = `语法通过，但有 ${warnings.length} 个警告`;
    const list = document.createElement("ul");
    for (const warning of warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      list.append(item);
    }

    el.diagnostics.className = "diagnostics warn";
    el.diagnostics.replaceChildren(heading, list);
    el.diagnostics.hidden = false;
  }

  function showErrorDiagnostic(message) {
    const heading = document.createElement("p");
    heading.textContent = "无法生成预览";
    const detail = document.createElement("pre");
    detail.textContent = message;

    el.diagnostics.className = "diagnostics error";
    el.diagnostics.replaceChildren(heading, detail);
    el.diagnostics.hidden = false;
  }

  function showFatal(message) {
    el.placeholder.hidden = true;
    el.errorText.textContent = message;
    el.error.hidden = false;
    setStatus("加载失败", "error");
    setStats("预览不可用");
  }

  async function fetchText(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`${path} 返回 HTTP ${response.status}`);
    }
    return response.text();
  }

  function fileStem(name) {
    return String(name).replace(/\.step$/i, "") || "guide";
  }

  function injectBase(html) {
    const base = new URL("./", window.location.href).href;
    return html.replace("<head>", `<head>\n<base href="${StepCompiler.escape(base)}">`);
  }

  function formatError(error) {
    if (error && typeof error.format === "function") return error.format();
    if (error && error.message) return error.message;
    return String(error);
  }

  function compileNow() {
    window.clearTimeout(state.timer);
    if (!state.assets) return;

    const text = el.source.value;
    const name = state.name || "untitled.step";

    try {
      const doc = StepCompiler.parseStep(text, {
        source: name,
        defaultId: fileStem(name),
      });
      const html = injectBase(
        StepCompiler.renderDocument(doc, {
          css: state.assets.css,
          js: state.assets.js,
          generatedBy: "在线预览",
        }),
      );

      state.doc = doc;
      state.html = html;
      el.preview.srcdoc = html;
      el.placeholder.hidden = true;
      el.error.hidden = true;
      el.download.disabled = false;
      el.openTab.disabled = false;
      setStatus("已生成", "ok");
      setStats(`${doc.steps.length} 个步骤 · ${doc.warnings.length} 个警告`);
      showWarningList(doc.warnings);
    } catch (error) {
      const message = formatError(error);
      state.html = "";
      state.doc = null;
      el.download.disabled = true;
      el.openTab.disabled = true;
      el.errorText.textContent = message;
      el.error.hidden = false;
      setStatus("有错误", "error");
      setStats("等待修正");
      showErrorDiagnostic(message);
    }
  }

  function scheduleCompile() {
    if (!state.assets) return;
    setStatus("编辑中", "busy");
    window.clearTimeout(state.timer);
    state.timer = window.setTimeout(compileNow, 380);
  }

  function setSource(text, name, sampleFile) {
    el.source.value = text;
    state.name = name;
    el.fileName.textContent = name;
    if (sampleFile !== undefined) {
      state.currentSample = sampleFile || "";
      setSampleActive(state.currentSample);
    }
    compileNow();
  }

  async function loadSample(file) {
    setSampleActive(file);
    setStatus("正在载入", "busy");
    try {
      let text = state.samples.get(file);
      if (text == null) {
        text = await fetchText(`samples/${file}`);
        state.samples.set(file, text);
      }
      setSource(text, file, file);
    } catch (error) {
      state.currentSample = "";
      setSampleActive("");
      setStatus("载入失败", "error");
      showFatal(`无法载入示例：${formatError(error)}`);
    }
  }

  async function loadFile(file) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      showFatal(`文件超过 ${Math.round(MAX_FILE_BYTES / 1024)} KB，无法在浏览器中预览。`);
      return;
    }

    try {
      const text = await file.text();
      state.currentSample = "";
      setSampleActive("");
      setSource(text, file.name || "untitled.step", "");
    } catch (error) {
      showFatal(`无法读取文件：${formatError(error)}`);
    }
  }

  function downloadHtml() {
    if (!state.html) return;
    const blob = new Blob([state.html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileStem(state.name)}.html`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function openInNewTab() {
    if (!state.html) return;
    const blob = new Blob([state.html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener");
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  function setView(view) {
    el.frameWrap.dataset.view = view;
    for (const button of viewButtons) {
      const active = button.dataset.view === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
  }

  function bindEvents() {
    for (const button of sampleButtons) {
      button.addEventListener("click", () => loadSample(button.dataset.sample));
    }

    for (const button of viewButtons) {
      button.addEventListener("click", () => setView(button.dataset.view));
    }

    el.reset.addEventListener("click", () => loadSample(DEFAULT_SAMPLE));
    el.download.addEventListener("click", downloadHtml);
    el.openTab.addEventListener("click", openInNewTab);
    el.fileInput.addEventListener("change", () => {
      const file = el.fileInput.files && el.fileInput.files[0];
      el.fileInput.value = "";
      loadFile(file);
    });

    el.source.addEventListener("input", scheduleCompile);
    el.source.addEventListener("keydown", (event) => {
      if (event.key !== "Tab" || event.shiftKey || event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      el.source.setRangeText("  ", el.source.selectionStart, el.source.selectionEnd, "end");
      el.source.dispatchEvent(new Event("input", { bubbles: true }));
    });

    let dragDepth = 0;
    el.dropZone.addEventListener("dragenter", (event) => {
      event.preventDefault();
      dragDepth += 1;
      el.dropZone.classList.add("dragging");
    });
    el.dropZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    });
    el.dropZone.addEventListener("dragleave", () => {
      dragDepth = Math.max(0, dragDepth - 1);
      if (!dragDepth) el.dropZone.classList.remove("dragging");
    });
    el.dropZone.addEventListener("drop", (event) => {
      event.preventDefault();
      dragDepth = 0;
      el.dropZone.classList.remove("dragging");
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      loadFile(file);
    });

    window.addEventListener("dragover", (event) => {
      if (!el.dropZone.contains(event.target)) event.preventDefault();
    });
    window.addEventListener("drop", (event) => {
      if (!el.dropZone.contains(event.target)) event.preventDefault();
    });
  }

  async function boot() {
    bindEvents();
    setSampleActive(DEFAULT_SAMPLE);

    try {
      if (!window.StepCompiler) {
        throw new Error("编译器脚本没有载入");
      }
      const [css, js] = await Promise.all([
        fetchText("assets/app.css"),
        fetchText("assets/app.js"),
      ]);
      state.assets = { css, js };
      await loadSample(DEFAULT_SAMPLE);
    } catch (error) {
      showFatal(`无法加载预览资源：${formatError(error)}`);
    }
  }

  boot();
})();
