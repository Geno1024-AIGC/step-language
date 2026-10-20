(() => {
  const root = document.documentElement;
  const toggle = document.getElementById("theme-toggle");
  const label = toggle?.querySelector(".theme-label");
  const key = "step-language-docs-theme";
  const themes = ["system", "light", "dark"];
  const labels = { system: "跟随系统", light: "浅色", dark: "深色" };
  let theme = "system";

  try {
    const saved = localStorage.getItem(key);
    if (themes.includes(saved)) theme = saved;
  } catch {
    // Storage can be unavailable in private browsing modes.
  }

  function applyTheme() {
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.dataset.theme = theme;
    }
    if (label) label.textContent = labels[theme];
    toggle?.setAttribute("aria-label", `切换主题（当前：${labels[theme]}）`);
  }

  applyTheme();

  toggle?.addEventListener("click", () => {
    theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    try {
      localStorage.setItem(key, theme);
    } catch {
      // Ignore storage failures; the theme still changes for this visit.
    }
    applyTheme();
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    const target = document.querySelector(button.getAttribute("data-copy"));
    if (!target) return;
    const original = button.textContent;

    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(target.innerText.trim());
        button.textContent = "已复制";
      } catch {
        button.textContent = "复制失败";
      }
      window.setTimeout(() => {
        button.textContent = original;
      }, 1400);
    });
  });

  const year = document.querySelector("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());
})();
