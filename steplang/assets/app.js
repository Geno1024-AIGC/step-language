(() => {
  "use strict";

  const dataEl = document.getElementById("step-data");
  if (!dataEl) return;

  const doc = JSON.parse(dataEl.textContent);
  const steps = Array.isArray(doc.steps) ? doc.steps : [];
  if (!steps.length) return;

  const byId = new Map(steps.map((step) => [step.id, step]));
  const indexOf = new Map(steps.map((step, index) => [step.id, index]));
  const validChecks = new Set();
  for (const step of steps) {
    for (const block of step.blocks || []) {
      if (block.t === "checks") {
        for (const item of block.items || []) validChecks.add(item.id);
      }
    }
  }

  const zh = String(doc.lang || "").toLowerCase().startsWith("zh");
  const L = zh
    ? {
        stepWord: "步骤",
        stepOf: (i, n) => `步骤 ${i} / ${n}`,
        announce: (i, n, title) => `步骤 ${i}，共 ${n} 步：${title}`,
        done: "已完成",
        back: "上一步",
        next: "完成并继续",
        finish: "完成流程",
        skip: "跳过，继续",
        mark: "标记本步完成",
        marked: "本步已完成",
        restart: "重新开始",
        review: "查看当前步骤",
        print: "打印全部",
        resetTitle: "重置进度？",
        resetBody: "已勾选的项目和完成状态将被清除，且无法恢复。",
        theme: "主题",
        themeNames: { auto: "自动", light: "浅色", dark: "深色" },
        copy: "复制",
        copied: "已复制",
        copyFailed: "复制失败",
        code: "代码",
        tip: "提示",
        warn: "警告",
        finished: "流程结束",
        finishedSub: "本次流程已结束，进度已自动保存在本机。",
        statDone: "已完成步骤",
        statTotal: "步骤总数",
        statTime: "用时",
        stepsWord: "个步骤",
        min: "分",
        sec: "秒",
      }
    : {
        stepWord: "Step",
        stepOf: (i, n) => `Step ${i} / ${n}`,
        announce: (i, n, title) => `Step ${i} of ${n}: ${title}`,
        done: "Done",
        back: "Back",
        next: "Complete and continue",
        finish: "Finish",
        skip: "Skip and continue",
        mark: "Mark this step done",
        marked: "Step completed",
        restart: "Start over",
        review: "View current step",
        print: "Print all",
        resetTitle: "Reset progress?",
        resetBody: "Checked items and completion state will be permanently cleared.",
        theme: "Theme",
        themeNames: { auto: "Auto", light: "Light", dark: "Dark" },
        copy: "Copy",
        copied: "Copied",
        copyFailed: "Copy failed",
        code: "Code",
        tip: "Tip",
        warn: "Warning",
        finished: "Workflow complete",
        finishedSub: "You have reached the end. Progress is saved on this device.",
        statDone: "Steps done",
        statTotal: "Total steps",
        statTime: "Time spent",
        stepsWord: "steps",
        min: "min",
        sec: "sec",
      };

  const $ = (id) => document.getElementById(id);
  const start = byId.has(doc.start) ? doc.start : steps[0].id;
  const total = steps.length;
  const storageKey = `steplang:${doc.id}:${doc.version}`;
  const themeKey = "steplang:theme";
  const hasOwn = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

  const el = {
    content: $("content"),
    stepnav: $("stepnav"),
    list: $("step-list"),
    topCount: $("top-count"),
    topBar: $("top-bar"),
    sideCount: $("side-count"),
    sideLabel: $("side-label"),
    sideBar: $("side-bar"),
    live: $("live"),
    themeLabel: $("theme-label"),
    dialog: $("reset-dialog"),
    printView: $("print-view"),
    menuBtn: document.querySelector('[data-act="open-menu"]'),
    themeBtn: document.querySelector('[data-act="theme"]'),
  };

  let state = null;
  let theme = "auto";
  try {
    const savedTheme = localStorage.getItem(themeKey);
    if (savedTheme === "light" || savedTheme === "dark" || savedTheme === "auto") {
      theme = savedTheme;
    }
  } catch (error) {
    theme = "auto";
  }

  const esc = (value) =>
    String(value).replace(/[&<>"']/g, (char) => {
      switch (char) {
        case "&":
          return "&amp;";
        case "<":
          return "&lt;";
        case ">":
          return "&gt;";
        case '"':
          return "&quot;";
        default:
          return "&#39;";
      }
    });

  function initialState() {
    return {
      v: 1,
      doc: doc.id,
      version: doc.version,
      current: start,
      history: [],
      done: {},
      checks: {},
      startedAt: Date.now(),
      finishedAt: null,
    };
  }

  function cleanOldStates() {
    try {
      const prefix = `steplang:${doc.id}:`;
      for (let i = localStorage.length - 1; i >= 0; i -= 1) {
        const key = localStorage.key(i);
        if (key && key !== storageKey && key.startsWith(prefix)) {
          localStorage.removeItem(key);
        }
      }
    } catch (error) {
      return;
    }
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return null;
      const saved = JSON.parse(raw);
      if (!saved || saved.v !== 1 || saved.doc !== doc.id || saved.version !== doc.version) {
        return null;
      }

      const clean = {
        v: 1,
        doc: doc.id,
        version: doc.version,
        current: byId.has(saved.current) ? saved.current : start,
        history: Array.isArray(saved.history)
          ? saved.history.filter((id) => byId.has(id)).slice(-300)
          : [],
        done: {},
        checks: {},
        startedAt: Number.isFinite(saved.startedAt) ? saved.startedAt : Date.now(),
        finishedAt: Number.isFinite(saved.finishedAt) ? saved.finishedAt : null,
      };

      if (saved.done && typeof saved.done === "object") {
        for (const id of Object.keys(saved.done)) {
          if (byId.has(id) && saved.done[id]) clean.done[id] = true;
        }
      }
      if (saved.checks && typeof saved.checks === "object") {
        for (const id of Object.keys(saved.checks)) {
          if (validChecks.has(id) && typeof saved.checks[id] === "boolean") {
            clean.checks[id] = saved.checks[id];
          }
        }
      }
      return clean;
    } catch (error) {
      return null;
    }
  }

  function saveState() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch (error) {
      return;
    }
  }

  function currentStep() {
    return byId.get(state.current) || byId.get(start);
  }

  function doneCount() {
    let count = 0;
    for (const id of Object.keys(state.done)) {
      if (state.done[id] && byId.has(id)) count += 1;
    }
    return count;
  }

  function isDone(id) {
    return Boolean(state.done[id]);
  }

  function pushHistory(id) {
    if (!id || !byId.has(id)) return;
    state.history.push(id);
    if (state.history.length > 300) {
      state.history.splice(0, state.history.length - 300);
    }
  }

  function updateHash() {
    const target = state.finishedAt ? "done" : state.current;
    if (window.location.hash.slice(1) === target) return;
    try {
      history.replaceState(null, "", `#${encodeURIComponent(target)}`);
    } catch (error) {
      window.location.hash = target;
    }
  }

  function applyHash() {
    let hash = "";
    try {
      hash = decodeURIComponent(window.location.hash.slice(1));
    } catch (error) {
      hash = "";
    }
    if (!hash) return;
    if (hash === "done") {
      if (!state.finishedAt) state.finishedAt = Date.now();
      return;
    }
    if (byId.has(hash)) {
      state.current = hash;
      state.finishedAt = null;
    }
  }

  function applyTheme() {
    const root = document.documentElement;
    if (theme === "auto") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    const label = L.themeNames[theme];
    if (el.themeLabel) el.themeLabel.textContent = label;
    if (el.themeBtn) {
      el.themeBtn.setAttribute("aria-label", `${L.theme}: ${label}`);
      el.themeBtn.title = `${L.theme}: ${label}`;
    }
  }

  function cycleTheme() {
    theme = theme === "auto" ? "light" : theme === "light" ? "dark" : "auto";
    try {
      localStorage.setItem(themeKey, theme);
    } catch (error) {
      void error;
    }
    applyTheme();
  }

  function formatDuration(ms) {
    const seconds = Math.max(0, Math.round(ms / 1000));
    if (seconds < 60) return `${seconds} ${L.sec}`;
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    return rest ? `${minutes} ${L.min} ${rest} ${L.sec}` : `${minutes} ${L.min}`;
  }

  function callout(kind, tag, html) {
    return `<aside class="callout ${kind}"><span class="callout-tag">${esc(tag)}</span><div class="callout-body">${html}</div></aside>`;
  }

  function renderBlock(block) {
    switch (block.t) {
      case "p":
        return `<p>${block.html || ""}</p>`;
      case "ul":
        return `<ul class="bullets">${(block.items || []).map((item) => `<li>${item}</li>`).join("")}</ul>`;
      case "checks": {
        const items = (block.items || [])
          .map((item) => {
            const checked = hasOwn(state.checks, item.id)
              ? Boolean(state.checks[item.id])
              : Boolean(item.checked);
            return `<label class="check"><input type="checkbox" data-check="${esc(item.id)}"${
              checked ? " checked" : ""
            }><span>${item.html || ""}</span></label>`;
          })
          .join("");
        return `<div class="checklist">${items}</div>`;
      }
      case "tip":
        return callout("tip", L.tip, block.html || "");
      case "warn":
        return callout("warn", L.warn, block.html || "");
      case "code": {
        const lang = block.lang ? esc(block.lang) : esc(L.code);
        return `<div class="code"><div class="code-bar"><span class="code-lang">${lang}</span><button type="button" class="copy" data-act="copy">${L.copy}</button></div><pre tabindex="0"><code>${esc(
          block.text || ""
        )}</code></pre></div>`;
      }
      case "img": {
        const caption = block.caption ? `<figcaption>${block.caption}</figcaption>` : "";
        return `<figure class="figure"><img src="${esc(block.src)}" alt="${esc(
          block.alt || ""
        )}" loading="lazy" decoding="async">${caption}</figure>`;
      }
      case "choice": {
        const qid = `q-${block.id || "choice"}`;
        const options = (block.options || [])
          .map(
            (option) =>
              `<button type="button" class="choice" data-target="${esc(option.target)}"><span>${option.label}</span><span class="choice-arrow" aria-hidden="true">→</span></button>`
          )
          .join("");
        return `<div class="choice-block"><p class="choice-prompt" id="${esc(
          qid
        )}">${block.prompt || ""}</p><div class="choices" role="group" aria-labelledby="${esc(
          qid
        )}">${options}</div></div>`;
      }
      default:
        return "";
    }
  }

  function renderNav(step) {
    const hasChoices = (step.blocks || []).some((block) => block.t === "choice");
    const canBack = state.history.length > 0 || step.id !== start;
    const back = canBack
      ? `<button type="button" class="btn btn-ghost" data-act="back">← ${L.back}</button>`
      : '<span class="nav-spacer" aria-hidden="true"></span>';
    const done = isDone(step.id);
    const mark = `<button type="button" class="btn btn-done${
      done ? " is-done" : ""
    }" data-act="toggle-done" aria-pressed="${done ? "true" : "false"}">${
      done ? L.marked : L.mark
    }</button>`;

    let primary = "";
    if (step.next && step.next !== "done") {
      primary = `<button type="button" class="btn btn-primary" data-act="advance">${
        hasChoices ? L.skip : L.next
      }</button>`;
    } else if (step.next === "done" || !hasChoices) {
      primary = `<button type="button" class="btn btn-primary" data-act="advance">${L.finish}</button>`;
    } else {
      primary = `<button type="button" class="btn" data-act="advance">${L.finish}</button>`;
    }

    return `${back}<div class="nav-actions">${mark}${primary}</div>`;
  }

  function renderTop() {
    const count = doneCount();
    const percent = total ? Math.round((count / total) * 100) : 0;
    if (el.topCount) el.topCount.textContent = `${count}/${total}`;
    if (el.sideCount) el.sideCount.textContent = `${count} / ${total}`;
    if (el.sideLabel) el.sideLabel.textContent = L.done;
    if (el.topBar) el.topBar.style.width = `${percent}%`;
    if (el.sideBar) el.sideBar.style.width = `${percent}%`;
    document.querySelectorAll(".bar[role='progressbar']").forEach((bar) => {
      bar.setAttribute("aria-valuenow", String(percent));
    });
  }

  function renderSidebar() {
    const finished = Boolean(state.finishedAt);
    el.list.innerHTML = steps
      .map((step, index) => {
        const done = isDone(step.id);
        const current = !finished && step.id === state.current;
        const label = `${L.stepWord} ${index + 1}: ${step.title}${done ? ` (${L.done})` : ""}`;
        return `<button type="button" class="step-link${done ? " is-done" : ""}" data-jump="${esc(
          step.id
        )}"${current ? ' aria-current="step"' : ""} aria-label="${esc(
          label
        )}"><span class="step-num" aria-hidden="true">${
          index + 1
        }</span><span class="step-label">${esc(step.title)}</span><span class="step-check" aria-hidden="true">✓</span></button>`;
      })
      .join("");

    const current = el.list.querySelector('[aria-current="step"]');
    if (current && window.matchMedia("(min-width: 901px)").matches) {
      requestAnimationFrame(() => current.scrollIntoView({ block: "nearest" }));
    }
  }

  function renderStep(step, options) {
    const index = indexOf.get(step.id) || 0;
    const done = isDone(step.id);
    const blocks = (step.blocks || []).map(renderBlock).join("");
    const timeChip = step.time
      ? `<span class="chip">${esc(step.time)}</span>`
      : "";
    el.content.innerHTML = `<article class="step" aria-labelledby="step-title"><div class="step-kicker"><span class="chip">${L.stepOf(
      index + 1,
      total
    )}</span>${timeChip}<span class="chip chip-done" data-done-chip${
      done ? "" : " hidden"
    }>${L.done}</span></div><h1 id="step-title" tabindex="-1">${esc(
      step.title
    )}</h1>${blocks}</article>`;
    el.stepnav.innerHTML = renderNav(step);
    document.title = `${step.title} · ${doc.title}`;
    if (el.live) el.live.textContent = L.announce(index + 1, total, step.title);
    if (options.focus !== false) {
      const heading = $("step-title");
      if (heading) heading.focus({ preventScroll: true });
    }
    if (options.scroll !== false) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  function renderDone(options) {
    const count = doneCount();
    const elapsed = formatDuration((state.finishedAt || Date.now()) - state.startedAt);
    el.content.innerHTML = `<article class="done-card"><div class="done-icon" aria-hidden="true">✓</div><h1 id="done-title" tabindex="-1">${
      L.finished
    }</h1><p class="done-sub">${L.finishedSub}</p><div class="stats"><div class="stat"><b>${count}</b><span>${
      L.statDone
    }</span></div><div class="stat"><b>${total}</b><span>${
      L.statTotal
    }</span></div><div class="stat"><b>${esc(elapsed)}</b><span>${
      L.statTime
    }</span></div></div><div class="done-actions"><button type="button" class="btn btn-primary" data-act="restart">${
      L.restart
    }</button><button type="button" class="btn" data-act="review">${
      L.review
    }</button><button type="button" class="btn" data-act="print">${
      L.print
    }</button></div></article>`;
    el.stepnav.innerHTML = "";
    document.title = `${L.finished} · ${doc.title}`;
    if (el.live) el.live.textContent = L.finished;
    if (options.focus !== false) {
      const heading = $("done-title");
      if (heading) heading.focus({ preventScroll: true });
    }
    if (options.scroll !== false) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  function render(options = {}) {
    if (!byId.has(state.current)) state.current = start;
    renderTop();
    renderSidebar();
    applyTheme();
    if (state.finishedAt) {
      renderDone(options);
    } else {
      renderStep(currentStep(), options);
    }
    updateHash();
  }

  function closeMenu(restoreFocus) {
    if (!document.body.classList.contains("menu-open")) return;
    document.body.classList.remove("menu-open");
    if (el.menuBtn) el.menuBtn.setAttribute("aria-expanded", "false");
    if (restoreFocus && el.menuBtn && document.activeElement && document.activeElement.closest("#sidebar")) {
      el.menuBtn.focus();
    }
  }

  function openMenu() {
    document.body.classList.add("menu-open");
    if (el.menuBtn) el.menuBtn.setAttribute("aria-expanded", "true");
    const closeButton = document.querySelector('#sidebar [data-act="close-menu"]');
    if (closeButton) closeButton.focus();
    const current = el.list.querySelector('[aria-current="step"]');
    if (current) requestAnimationFrame(() => current.scrollIntoView({ block: "nearest" }));
  }

  function navigateTo(stepId) {
    if (!byId.has(stepId)) return;
    if (stepId !== state.current) pushHistory(state.current);
    state.current = stepId;
    state.finishedAt = null;
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function choose(target) {
    if (state.finishedAt) return;
    state.done[state.current] = true;
    if (target === "done") {
      finish();
      return;
    }
    if (!byId.has(target)) return;
    if (target !== state.current) pushHistory(state.current);
    state.current = target;
    state.finishedAt = null;
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function advance() {
    if (state.finishedAt) return;
    const step = currentStep();
    state.done[step.id] = true;
    if (!step.next || step.next === "done" || !byId.has(step.next)) {
      finish();
      return;
    }
    if (step.next !== state.current) pushHistory(state.current);
    state.current = step.next;
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function back() {
    if (state.history.length) {
      state.current = state.history.pop();
    } else if (state.current !== start) {
      state.current = start;
    } else {
      return;
    }
    state.finishedAt = null;
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function finish() {
    state.done[state.current] = true;
    if (!state.finishedAt) state.finishedAt = Date.now();
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function resetNow() {
    state = initialState();
    saveState();
    closeMenu(false);
    render({ focus: true, scroll: true });
  }

  function review() {
    state.finishedAt = null;
    saveState();
    render({ focus: true, scroll: true });
  }

  function toggleDone() {
    const id = state.current;
    if (state.done[id]) {
      delete state.done[id];
    } else {
      state.done[id] = true;
    }
    saveState();
    renderTop();
    renderSidebar();
    const chip = el.content.querySelector("[data-done-chip]");
    if (chip) chip.hidden = !isDone(id);
    el.stepnav.innerHTML = renderNav(currentStep());
    const button = el.stepnav.querySelector('[data-act="toggle-done"]');
    if (button) button.focus({ preventScroll: true });
  }

  function openReset() {
    if (!el.dialog) {
      if (window.confirm(`${L.resetTitle}\n${L.resetBody}`)) resetNow();
      return;
    }
    if (el.dialog.open) return;
    el.dialog.returnValue = "";
    if (typeof el.dialog.showModal === "function") {
      el.dialog.showModal();
    } else if (window.confirm(`${L.resetTitle}\n${L.resetBody}`)) {
      resetNow();
    }
  }

  function fallbackCopy(text, success, failure) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (error) {
      ok = false;
    }
    area.remove();
    if (ok) success();
    else failure();
  }

  function copyCode(button) {
    const container = button.closest(".code");
    const pre = container ? container.querySelector("pre") : null;
    if (!pre) return;
    const text = pre.textContent || "";
    const success = () => {
      button.textContent = L.copied;
      window.setTimeout(() => {
        button.textContent = L.copy;
      }, 1400);
    };
    const failure = () => {
      button.textContent = L.copyFailed;
      window.setTimeout(() => {
        button.textContent = L.copy;
      }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(success)
        .catch(() => fallbackCopy(text, success, failure));
    } else {
      fallbackCopy(text, success, failure);
    }
  }

  function printBlock(block) {
    switch (block.t) {
      case "p":
        return `<p>${block.html || ""}</p>`;
      case "ul":
        return `<ul>${(block.items || []).map((item) => `<li>${item}</li>`).join("")}</ul>`;
      case "checks":
        return (block.items || [])
          .map((item) => {
            const checked = hasOwn(state.checks, item.id)
              ? Boolean(state.checks[item.id])
              : Boolean(item.checked);
            return `<div class="print-check">${checked ? "☑" : "☐"} ${item.html || ""}</div>`;
          })
          .join("");
      case "tip":
        return `<div class="print-tip"><strong>${esc(L.tip)}:</strong> ${block.html || ""}</div>`;
      case "warn":
        return `<div class="print-warn"><strong>${esc(L.warn)}:</strong> ${block.html || ""}</div>`;
      case "code":
        return `<pre>${esc(block.text || "")}</pre>`;
      case "img": {
        const caption = block.caption ? `<figcaption>${block.caption}</figcaption>` : "";
        return `<figure><img src="${esc(block.src)}" alt="${esc(
          block.alt || ""
        )}" loading="eager" decoding="async">${caption}</figure>`;
      }
      case "choice": {
        const options = (block.options || [])
          .map((option) => {
            const target =
              option.target === "done"
                ? L.finish
                : byId.has(option.target)
                ? byId.get(option.target).title
                : option.target;
            return `<li>${option.label} <span class="print-arrow">→</span> ${esc(target)}</li>`;
          })
          .join("");
        return `<p><strong>${block.prompt || ""}</strong></p><ul class="print-choices">${options}</ul>`;
      }
      default:
        return "";
    }
  }

  function buildPrintView() {
    if (!el.printView || el.printView.dataset.ready === "1") return;
    const parts = [
      `<header class="print-head"><h1>${esc(doc.title)}</h1>`,
    ];
    if (doc.description) parts.push(`<p class="print-desc">${esc(doc.description)}</p>`);
    parts.push(
      `<p class="print-meta">v${esc(doc.version)} · ${total} ${esc(L.stepsWord)}</p></header>`
    );
    steps.forEach((step, index) => {
      parts.push(
        `<section class="print-step"><h2><span class="num">${esc(L.stepWord)} ${
          index + 1
        }</span> ${esc(step.title)}</h2>`
      );
      for (const block of step.blocks || []) parts.push(printBlock(block));
      parts.push("</section>");
    });
    el.printView.innerHTML = parts.join("");
    el.printView.dataset.ready = "1";
  }

  function clearPrintView() {
    if (!el.printView) return;
    el.printView.innerHTML = "";
    delete el.printView.dataset.ready;
  }

  function waitForImages(root, timeout) {
    const images = Array.from(root.querySelectorAll("img"));
    if (!images.length) return Promise.resolve();
    const loaded = Promise.all(
      images.map(
        (image) =>
          new Promise((resolve) => {
            if (image.complete) {
              resolve();
              return;
            }
            image.addEventListener("load", resolve, { once: true });
            image.addEventListener("error", resolve, { once: true });
          })
      )
    );
    return Promise.race([
      loaded,
      new Promise((resolve) => window.setTimeout(resolve, timeout)),
    ]);
  }

  async function printAll() {
    buildPrintView();
    if (el.printView) await waitForImages(el.printView, 2500);
    try {
      window.print();
    } catch (error) {
      return;
    }
  }

  function handleAction(action, target) {
    switch (action) {
      case "open-menu":
        openMenu();
        break;
      case "close-menu":
        closeMenu(true);
        break;
      case "theme":
        cycleTheme();
        break;
      case "back":
        back();
        break;
      case "advance":
        advance();
        break;
      case "toggle-done":
        toggleDone();
        break;
      case "restart":
        resetNow();
        break;
      case "review":
        review();
        break;
      case "print":
        printAll();
        break;
      case "reset":
        openReset();
        break;
      case "copy":
        copyCode(target);
        break;
      default:
        break;
    }
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-act], [data-jump], [data-target]");
    if (!target) return;
    if (target.dataset.jump) {
      event.preventDefault();
      navigateTo(target.dataset.jump);
      return;
    }
    if (target.dataset.target) {
      event.preventDefault();
      choose(target.dataset.target);
      return;
    }
    if (target.dataset.act) {
      event.preventDefault();
      handleAction(target.dataset.act, target);
    }
  });

  document.addEventListener("change", (event) => {
    const input = event.target.closest("[data-check]");
    if (!input) return;
    state.checks[input.dataset.check] = input.checked;
    saveState();
  });

  document.addEventListener("keydown", (event) => {
    if (el.dialog && el.dialog.open) return;
    if (event.key === "Escape") {
      closeMenu(true);
      return;
    }
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
    const tag = event.target && event.target.tagName ? event.target.tagName.toLowerCase() : "";
    if (
      tag === "input" ||
      tag === "textarea" ||
      tag === "select" ||
      tag === "button" ||
      (event.target && event.target.isContentEditable)
    ) {
      return;
    }
    if (event.key === "ArrowLeft") {
      if (state.history.length || state.current !== start || state.finishedAt) {
        event.preventDefault();
        back();
      }
      return;
    }
    if (event.key === "ArrowRight" && !state.finishedAt) {
      const step = currentStep();
      const hasChoices = (step.blocks || []).some((block) => block.t === "choice");
      if (!hasChoices || step.next) {
        event.preventDefault();
        advance();
      }
    }
  });

  if (el.dialog) {
    el.dialog.addEventListener("close", () => {
      if (el.dialog.returnValue === "confirm") resetNow();
      el.dialog.returnValue = "";
    });
  }

  window.addEventListener("beforeprint", buildPrintView);
  window.addEventListener("afterprint", clearPrintView);

  cleanOldStates();
  state = loadState() || initialState();
  applyHash();
  saveState();
  applyTheme();
  render({ focus: false, scroll: false });
})();
