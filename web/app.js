const CACHE_KEY = "micropython-web-ide-cache-v2";

const state = {
  selectedFile: "",
  files: [],
  lastLogId: 0,
  connected: false,
  dirty: false,
  untitled: false,
  activeTerminal: "repl",
  openTabs: [],
  staleFiles: {},
  terminalCollapsed: false,
  editorFullscreen: false,
  cache: {
    files: [],
    contents: {},
    selectedFile: "",
  },
};

const el = {
  portSelect: document.querySelector("#portSelect"),
  baudInput: document.querySelector("#baudInput"),
  connectBtn: document.querySelector("#connectBtn"),
  disconnectBtn: document.querySelector("#disconnectBtn"),
  themeSelect: document.querySelector("#themeSelect"),
  customThemeBtn: document.querySelector("#customThemeBtn"),
  themePanel: document.querySelector("#themePanel"),
  themeControls: document.querySelector("#themeControls"),
  closeThemePanelBtn: document.querySelector("#closeThemePanelBtn"),
  saveThemeBtn: document.querySelector("#saveThemeBtn"),
  resetThemeBtn: document.querySelector("#resetThemeBtn"),
  statusBadge: document.querySelector("#statusBadge"),
  refreshFilesBtn: document.querySelector("#refreshFilesBtn"),
  fileList: document.querySelector("#fileList"),
  fileCount: document.querySelector("#fileCount"),
  newFileBtn: document.querySelector("#newFileBtn"),
  firmwareInput: document.querySelector("#firmwareInput"),
  firmwareFileLabel: document.querySelector("#firmwareFileLabel"),
  firmwareAddressInput: document.querySelector("#firmwareAddressInput"),
  firmwareEraseInput: document.querySelector("#firmwareEraseInput"),
  flashFirmwareBtn: document.querySelector("#flashFirmwareBtn"),
  eraseFlashBtn: document.querySelector("#eraseFlashBtn"),
  fileNameInput: document.querySelector("#fileNameInput"),
  openTabs: document.querySelector("#openTabs"),
  saveBtn: document.querySelector("#saveBtn"),
  runBtn: document.querySelector("#runBtn"),
  deleteBtn: document.querySelector("#deleteBtn"),
  stopBtn: document.querySelector("#stopBtn"),
  fullscreenEditorBtn: document.querySelector("#fullscreenEditorBtn"),
  editor: document.querySelector("#editor"),
  highlightedCode: document.querySelector("#highlightedCode"),
  minimapCode: document.querySelector("#minimapCode"),
  replOutput: document.querySelector("#replOutput"),
  terminalForm: document.querySelector("#terminalForm"),
  terminalCommand: document.querySelector("#terminalCommand"),
  clearTerminalBtn: document.querySelector("#clearTerminalBtn"),
  toggleTerminalBtn: document.querySelector("#toggleTerminalBtn"),
  appShell: document.querySelector(".app-shell"),
};

const CUSTOM_THEME_KEY = "micropython-web-ide-custom-theme-v1";
const CUSTOM_THEME_FIELDS = [
  ["--bg", "Page background"],
  ["--chrome", "Top bars"],
  ["--sidebar", "File sidebar"],
  ["--surface", "Panels"],
  ["--surface-2", "Controls"],
  ["--ink", "Main text"],
  ["--muted", "Muted text"],
  ["--border", "Borders"],
  ["--accent", "Accent"],
  ["--action", "Run / success"],
  ["--danger", "Danger"],
  ["--terminal", "Terminal bg"],
  ["--terminal-line", "Terminal border"],
  ["--terminal-text", "Terminal text"],
  ["--code-bg", "Editor bg"],
  ["--code-gutter", "Editor gutter"],
  ["--code-text", "Code text"],
  ["--code-keyword", "Keywords"],
  ["--code-string", "Strings"],
  ["--code-comment", "Comments"],
  ["--code-number", "Numbers"],
  ["--code-builtin", "Functions / builtins"],
  ["--code-function", "Function names"],
  ["--code-variable", "Variables"],
  ["--code-operator", "Operators"],
];

const DEFAULT_CUSTOM_THEME = {
  "--bg": "#10121d",
  "--chrome": "#171a2b",
  "--sidebar": "#121522",
  "--surface": "#171a2b",
  "--surface-2": "#222641",
  "--ink": "#eef0ff",
  "--muted": "#a8add2",
  "--border": "#34395e",
  "--accent": "#9d7dff",
  "--action": "#53e6b5",
  "--danger": "#ff7aa9",
  "--terminal": "#0b0d16",
  "--terminal-line": "#2b3154",
  "--terminal-text": "#e8ebff",
  "--code-bg": "#10121d",
  "--code-gutter": "#0b0d16",
  "--code-text": "#eef0ff",
  "--code-keyword": "#c792ea",
  "--code-string": "#f6c177",
  "--code-comment": "#7f86b8",
  "--code-number": "#ff9ac1",
  "--code-builtin": "#7fffd4",
  "--code-function": "#82d8ff",
  "--code-variable": "#f0f3ff",
  "--code-operator": "#ffcc66",
};

function readCache() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CACHE_KEY) || "{}");
    state.cache = {
      files: Array.isArray(parsed.files) ? parsed.files : [],
      contents: parsed.contents && typeof parsed.contents === "object" ? parsed.contents : {},
      selectedFile: parsed.selectedFile || "",
    };
  } catch {
    state.cache = { files: [], contents: {}, selectedFile: "" };
  }
}

function writeCache() {
  localStorage.setItem(CACHE_KEY, JSON.stringify(state.cache));
}

function applyTheme(theme) {
  const next = ["light", "dark", "purple"].includes(theme) ? theme : "dark";
  document.documentElement.dataset.theme = next;
  el.themeSelect.value = next;
  localStorage.setItem("micropython-web-ide-theme", next);
}

function readCustomTheme() {
  try {
    return { ...DEFAULT_CUSTOM_THEME, ...JSON.parse(localStorage.getItem(CUSTOM_THEME_KEY) || "{}") };
  } catch {
    return { ...DEFAULT_CUSTOM_THEME };
  }
}

function writeCustomTheme(values) {
  localStorage.setItem(CUSTOM_THEME_KEY, JSON.stringify(values));
}

function applyCustomTheme(values = readCustomTheme()) {
  for (const [name] of CUSTOM_THEME_FIELDS) {
    document.documentElement.style.setProperty(name, values[name] || DEFAULT_CUSTOM_THEME[name]);
  }
}

function clearCustomThemeVars() {
  for (const [name] of CUSTOM_THEME_FIELDS) {
    document.documentElement.style.removeProperty(name);
  }
}

function setTheme(theme) {
  const next = ["light", "dark", "purple", "custom"].includes(theme) ? theme : "dark";
  document.documentElement.dataset.theme = next;
  el.themeSelect.value = next;
  localStorage.setItem("micropython-web-ide-theme", next);
  if (next === "custom") {
    applyCustomTheme();
  } else {
    clearCustomThemeVars();
  }
}

function renderThemeControls() {
  const values = readCustomTheme();
  el.themeControls.innerHTML = "";
  for (const [name, label] of CUSTOM_THEME_FIELDS) {
    const row = document.createElement("label");
    row.className = "theme-control";
    row.innerHTML = `
      <span>${escapeHtml(label)}</span>
      <input type="color" value="${escapeHtml(values[name] || DEFAULT_CUSTOM_THEME[name])}" data-theme-var="${escapeHtml(name)}" />
    `;
    el.themeControls.append(row);
  }
}

function collectThemeControls() {
  const values = {};
  for (const input of el.themeControls.querySelectorAll("input[type='color']")) {
    values[input.dataset.themeVar] = input.value;
  }
  return values;
}

function openThemePanel() {
  renderThemeControls();
  el.themePanel.classList.add("open");
  el.themePanel.setAttribute("aria-hidden", "false");
}

function closeThemePanel() {
  el.themePanel.classList.remove("open");
  el.themePanel.setAttribute("aria-hidden", "true");
}

function setTerminalCollapsed(collapsed) {
  state.terminalCollapsed = collapsed;
  el.appShell.classList.toggle("terminal-collapsed", collapsed);
  el.toggleTerminalBtn.textContent = collapsed ? "^" : "x";
  el.toggleTerminalBtn.title = collapsed ? "Open terminal (Ctrl+J)" : "Close terminal (Ctrl+J)";
  el.toggleTerminalBtn.setAttribute("aria-label", collapsed ? "Open terminal" : "Close terminal");
}

function toggleTerminal() {
  setTerminalCollapsed(!state.terminalCollapsed);
}

function setEditorFullscreen(fullscreen) {
  state.editorFullscreen = fullscreen;
  el.appShell.classList.toggle("editor-fullscreen", fullscreen);
  el.fullscreenEditorBtn.textContent = fullscreen ? "Exit" : "Focus";
  window.setTimeout(() => {
    updateHighlight();
    syncEditorScroll();
    el.editor.focus();
  }, 0);
}

function toggleEditorFullscreen() {
  setEditorFullscreen(!state.editorFullscreen);
}

function cacheFiles(files) {
  state.cache.files = files;
  writeCache();
}

function cacheFileContent(name, content) {
  state.cache.contents[name] = content;
  state.cache.selectedFile = name;
  writeCache();
}

function markBoardStorageStale() {
  for (const name of state.openTabs) {
    if (name && name !== "untitled.py") {
      state.staleFiles[name] = true;
    }
  }
  state.files = [];
  state.cache.files = [];
  writeCache();
  renderFiles([], "board");
}

function ensureDraftForTyping() {
  if (state.selectedFile || !el.editor.value) return;
  state.selectedFile = "untitled.py";
  state.untitled = true;
  el.fileNameInput.value = "untitled.py";
  state.cache.contents["untitled.py"] = el.editor.value;
  addOpenTab("untitled.py");
}

function renderOpenTabs() {
  el.openTabs.innerHTML = "";
  if (!state.openTabs.length) {
    const empty = document.createElement("div");
    empty.className = "empty-tab";
    empty.textContent = "No file open";
    el.openTabs.append(empty);
    return;
  }

  for (const name of state.openTabs) {
    const tab = document.createElement("button");
    tab.className = `file-tab${name === state.selectedFile ? " active" : ""}`;
    tab.type = "button";
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-selected", String(name === state.selectedFile));
    tab.innerHTML = `<span>${escapeHtml(name)}</span><span class="tab-close" title="Close tab" aria-hidden="true">x</span>`;
    tab.addEventListener("click", (event) => {
      if (event.target.classList.contains("tab-close")) {
        closeTab(name);
        return;
      }
      switchTab(name);
    });
    el.openTabs.append(tab);
  }
}

function addOpenTab(name) {
  if (!name) return;
  if (!state.openTabs.includes(name)) {
    state.openTabs.push(name);
  }
  renderOpenTabs();
}

function switchTab(name) {
  if (!name || name === state.selectedFile) return;
  if (state.selectedFile) {
    state.cache.contents[state.selectedFile] = el.editor.value;
    writeCache();
  }
  state.selectedFile = name;
  state.untitled = name === "untitled.py";
  el.fileNameInput.value = name;
  setEditorValue(state.cache.contents[name] || "");
  state.dirty = false;
  renderFiles(state.files.length ? state.files : state.cache.files, state.files.length ? "board" : "cache");
  renderOpenTabs();
}

function closeTab(name) {
  const index = state.openTabs.indexOf(name);
  state.openTabs = state.openTabs.filter((tab) => tab !== name);
  if (name === state.selectedFile) {
    const next = state.openTabs[Math.max(0, index - 1)] || state.openTabs[0] || "";
    state.selectedFile = next;
    state.untitled = next === "untitled.py";
    el.fileNameInput.value = next;
    setEditorValue(next ? state.cache.contents[next] || "" : "");
    state.dirty = false;
  }
  renderFiles(state.files.length ? state.files : state.cache.files, state.files.length ? "board" : "cache");
  renderOpenTabs();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

async function apiForm(path, formData) {
  const response = await fetch(path, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.error || "Request failed");
  }
  return data;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function highlightPython(source) {
  const keywords = new Set([
    "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class",
    "continue", "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass",
    "raise", "return", "try", "while", "with", "yield",
  ]);
  const builtins = new Set([
    "abs", "all", "any", "bool", "bytearray", "bytes", "dict", "enumerate", "float",
    "int", "len", "list", "map", "max", "min", "open", "print", "range", "set",
    "str", "sum", "tuple", "type", "zip", "Pin", "sleep", "time",
  ]);
  const tokenPattern = /("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|#[^\n]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b|==|!=|<=|>=|:=|->|[-+*/%=&|^~<>!]+|[^\w#"'0-9]+)/g;
  const tokens = Array.from(source.matchAll(tokenPattern), (match) => match[0]);

  function nextMeaningfulToken(index) {
    for (let i = index + 1; i < tokens.length; i += 1) {
      if (tokens[i].trim()) return tokens[i];
    }
    return "";
  }

  let previousMeaningful = "";
  return tokens.map((token, index) => {
    const escaped = escapeHtml(token);
    if (token.startsWith("#")) return `<span class="tok-comment">${escaped}</span>`;
    if (token.startsWith("\"") || token.startsWith("'")) return `<span class="tok-string">${escaped}</span>`;
    if (/^\d/.test(token)) return `<span class="tok-number">${escaped}</span>`;
    if (/^[-+*/%=&|^~<>!:]+$/.test(token)) return `<span class="tok-operator">${escaped}</span>`;
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(token)) {
      const next = nextMeaningfulToken(index);
      let html = escaped;
      if (previousMeaningful === "def" || previousMeaningful === "class") {
        html = `<span class="tok-function">${escaped}</span>`;
      } else if (keywords.has(token)) {
        html = `<span class="tok-keyword">${escaped}</span>`;
      } else if (builtins.has(token) || next === "(") {
        html = `<span class="tok-builtin">${escaped}</span>`;
      } else {
        html = `<span class="tok-variable">${escaped}</span>`;
      }
      previousMeaningful = token;
      return html;
    }
    if (token.trim()) previousMeaningful = token;
    return escaped;
  }).join("");
}

function updateHighlight() {
  const source = el.editor.value || "";
  el.highlightedCode.innerHTML = `${highlightPython(source)}\n`;
  el.minimapCode.textContent = `${source}\n`;
  updateMinimapScroll();
}

function setEditorValue(value) {
  el.editor.value = value;
  updateHighlight();
}

function markEditorDirty() {
  state.dirty = true;
  if (state.selectedFile) {
    state.cache.contents[state.selectedFile] = el.editor.value;
  }
  updateHighlight();
}

function replaceEditorRange(start, end, text, caretOffset = text.length) {
  el.editor.setRangeText(text, start, end, "end");
  const caret = start + caretOffset;
  el.editor.selectionStart = caret;
  el.editor.selectionEnd = caret;
  markEditorDirty();
  window.requestAnimationFrame(scrollCaretIntoView);
}

function scrollCaretIntoView() {
  const text = el.editor.value.slice(0, el.editor.selectionStart);
  const lines = text.split("\n");
  const lineHeight = parseFloat(getComputedStyle(el.editor).lineHeight) || 22;
  const paddingTop = parseFloat(getComputedStyle(el.editor).paddingTop) || 0;
  const caretY = paddingTop + (lines.length - 1) * lineHeight;
  const visibleTop = el.editor.scrollTop;
  const visibleBottom = visibleTop + el.editor.clientHeight - lineHeight * 1.5;

  if (caretY > visibleBottom) {
    el.editor.scrollTop = caretY - el.editor.clientHeight + lineHeight * 2;
  } else if (caretY < visibleTop) {
    el.editor.scrollTop = Math.max(0, caretY - lineHeight);
  }
  syncEditorScroll();
}

function currentLineBeforeCaret() {
  const before = el.editor.value.slice(0, el.editor.selectionStart);
  return before.slice(before.lastIndexOf("\n") + 1);
}

function leadingWhitespace(value) {
  return (value.match(/^[ \t]*/) || [""])[0];
}

function nextLineIndent(line) {
  const indent = leadingWhitespace(line);
  const code = line.replace(/#.*/, "").trimEnd();
  return code.endsWith(":") ? `${indent}    ` : indent;
}

function handleEditorKeydown(event) {
  const start = el.editor.selectionStart;
  const end = el.editor.selectionEnd;
  const value = el.editor.value;
  const selected = value.slice(start, end);
  const pairs = { "(": ")", "[": "]", "{": "}", "'": "'", "\"": "\"" };
  const closing = new Set([")", "]", "}", "'", "\""]);

  if ((event.ctrlKey || event.metaKey) && event.key === "Backspace") {
    event.preventDefault();
    if (start !== end) {
      replaceEditorRange(start, end, "", 0);
      return;
    }
    if (start === 0) return;
    let deleteFrom = start;
    while (deleteFrom > 0 && /[ \t]/.test(value[deleteFrom - 1])) {
      deleteFrom -= 1;
    }
    if (deleteFrom === start) {
      const previous = value[deleteFrom - 1];
      const isWord = /[A-Za-z0-9_]/.test(previous);
      while (
        deleteFrom > 0 &&
        value[deleteFrom - 1] !== "\n" &&
        (isWord ? /[A-Za-z0-9_]/.test(value[deleteFrom - 1]) : !/[A-Za-z0-9_\s]/.test(value[deleteFrom - 1]))
      ) {
        deleteFrom -= 1;
      }
    }
    replaceEditorRange(deleteFrom, start, "", 0);
    return;
  }

  if (event.key === "Tab") {
    event.preventDefault();
    if (event.shiftKey) {
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      const removeCount = value.slice(lineStart, lineStart + 4) === "    " ? 4 : value[lineStart] === "\t" ? 1 : 0;
      if (removeCount) replaceEditorRange(lineStart, lineStart + removeCount, "", 0);
    } else {
      replaceEditorRange(start, end, "    ");
    }
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
    const line = currentLineBeforeCaret();
    replaceEditorRange(start, end, `\n${nextLineIndent(line)}`);
    return;
  }

  if (closing.has(event.key) && value[start] === event.key && start === end) {
    event.preventDefault();
    el.editor.selectionStart = start + 1;
    el.editor.selectionEnd = start + 1;
    return;
  }

  if (pairs[event.key]) {
    const next = pairs[event.key];
    event.preventDefault();
    if (selected) {
      replaceEditorRange(start, end, `${event.key}${selected}${next}`, selected.length + 1);
    } else {
      replaceEditorRange(start, end, `${event.key}${next}`, 1);
    }
    return;
  }

  if (event.key === "Backspace" && start === end && start > 0) {
    const previous = value[start - 1];
    const next = value[start];
    if (pairs[previous] === next) {
      event.preventDefault();
      replaceEditorRange(start - 1, start + 1, "", 0);
    }
  }
}

function syncEditorScroll() {
  el.highlightedCode.scrollTop = el.editor.scrollTop;
  el.highlightedCode.scrollLeft = el.editor.scrollLeft;
  updateMinimapScroll();
}

function updateMinimapScroll() {
  if (!el.minimapCode) return;
  const maxEditorScroll = Math.max(1, el.editor.scrollHeight - el.editor.clientHeight);
  const maxMiniScroll = Math.max(0, el.minimapCode.scrollHeight - el.minimapCode.clientHeight);
  el.minimapCode.scrollTop = (el.editor.scrollTop / maxEditorScroll) * maxMiniScroll;
}

function scrollEditorFromMinimap(event) {
  const rect = el.minimapCode.getBoundingClientRect();
  const ratio = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
  const maxEditorScroll = Math.max(0, el.editor.scrollHeight - el.editor.clientHeight);
  el.editor.scrollTop = ratio * maxEditorScroll;
  syncEditorScroll();
}

function outputTarget(stream) {
  return el.replOutput;
}

function appendTerminal(text, stream = "info", time = "") {
  if (!text) return;
  const target = outputTarget(stream);
  const lines = String(text).replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  const html = lines.map((line) => {
    const stamp = time ? `<span class="log-time">[${escapeHtml(time)}]</span> ` : "";
    return `${stamp}<span class="log-${stream}">${escapeHtml(line)}</span>`;
  }).join("\n");
  target.insertAdjacentHTML("beforeend", `${html}\n`);
  target.scrollTop = target.scrollHeight;
}

function setTerminalTab(tab) {
  state.activeTerminal = tab;
}

function setStatus(status) {
  state.connected = Boolean(status.connected);
  const label = status.connected ? `${status.port || "Connected"} @ ${status.baud}` : "Offline";
  el.statusBadge.textContent = label;
  el.statusBadge.classList.toggle("online", state.connected);
}

function renderFiles(files = state.files, source = "board") {
  state.files = files;
  el.fileList.innerHTML = "";
  const label = files.length ? `${files.length} file${files.length === 1 ? "" : "s"} ${source === "cache" ? "cached" : "on board"}` : "No files";
  el.fileCount.textContent = label;

  if (!files.length) {
    el.fileList.innerHTML = `<div class="file-row empty"><span>No board files loaded</span></div>`;
    return;
  }

  for (const file of files) {
    const button = document.createElement("button");
    button.className = `file-row${file === state.selectedFile ? " selected" : ""}`;
    button.type = "button";
    button.innerHTML = `<span>${escapeHtml(file)}</span>`;
    button.addEventListener("click", () => openFile(file));
    el.fileList.append(button);
  }
}

function loadCachedWorkspace() {
  readCache();
  if (state.cache.files.length) {
    renderFiles(state.cache.files, "cache");
  }

  const cachedName = state.cache.selectedFile;
  if (cachedName && Object.prototype.hasOwnProperty.call(state.cache.contents, cachedName)) {
    state.selectedFile = cachedName;
    el.fileNameInput.value = cachedName;
    addOpenTab(cachedName);
    setEditorValue(state.cache.contents[cachedName]);
    state.dirty = false;
    state.untitled = false;
    renderFiles(state.cache.files, "cache");
    appendTerminal(`Loaded ${cachedName} from cache`, "info");
  }
}

async function loadPorts() {
  try {
    const data = await api("/api/ports");
    const current = data.status.port || data.detected_port || data.ports[0]?.device;
    el.portSelect.innerHTML = "";
    if (!data.ports.length) {
      el.portSelect.append(new Option("No ports found", ""));
    } else {
      for (const port of data.ports) {
        const marker = port.detected ? " *" : "";
        const option = new Option(`${port.device} - ${port.description}${marker}`, port.device);
        el.portSelect.append(option);
      }
      el.portSelect.value = current || data.ports[0].device;
    }
    setStatus(data.status);
    return data;
  } catch (error) {
    appendTerminal(error.message, "error");
    return null;
  }
}

async function loadServerCache() {
  try {
    const data = await api("/api/cache");
    const cache = data.cache;
    if (Array.isArray(cache.files) && cache.files.length) {
      state.cache.files = cache.files;
      state.cache.contents = { ...state.cache.contents, ...(cache.contents || {}) };
      writeCache();
      renderFiles(state.cache.files, "cache");
      appendTerminal(cache.message || "Loaded server cache", "info");
      return true;
    }
  } catch {
  }
  return false;
}

function watchServerCache(attempt = 0) {
  if (attempt > 8) return;
  window.setTimeout(async () => {
    const loaded = await loadServerCache();
    if (!loaded) {
      watchServerCache(attempt + 1);
    }
  }, 1000 + attempt * 500);
}

async function connect({ silent = false } = {}) {
  try {
    const data = await api("/api/connect", {
      method: "POST",
      body: JSON.stringify({
        port: el.portSelect.value,
        baud: Number(el.baudInput.value || 115200),
      }),
    });
    setStatus(data.status);
    if (!silent) appendTerminal("Connected", "ok");
    await refreshFiles({ openCachedSelection: true });
    await startUnifiedMonitor();
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function disconnect() {
  try {
    const data = await api("/api/disconnect", { method: "POST", body: "{}" });
    setStatus(data.status);
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function refreshFiles({ openCachedSelection = false } = {}) {
  try {
    const data = await api("/api/files");
    renderFiles(data.files);
    cacheFiles(data.files);

    const preferred = state.selectedFile || state.cache.selectedFile || data.files[0] || "";
    if (openCachedSelection && preferred && state.cache.contents[preferred] && !state.dirty) {
      state.selectedFile = preferred;
      el.fileNameInput.value = preferred;
      addOpenTab(preferred);
      setEditorValue(state.cache.contents[preferred]);
      renderFiles(data.files);
    }
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function openFile(name = el.fileNameInput.value.trim() || state.selectedFile) {
  if (!name) {
    appendTerminal("Select or enter a file name first", "warn");
    return;
  }

  state.selectedFile = name;
  state.untitled = false;
  el.fileNameInput.value = name;
  addOpenTab(name);
  renderFiles(state.files.length ? state.files : state.cache.files, state.files.length ? "board" : "cache");

  if (Object.prototype.hasOwnProperty.call(state.cache.contents, name)) {
    setEditorValue(state.cache.contents[name]);
    state.dirty = false;
    appendTerminal(`Opened ${name} from cache`, "info");
  } else {
    setEditorValue("");
    appendTerminal(`Opening ${name} from board...`, "info");
  }

  try {
    const data = await api(`/api/file?name=${encodeURIComponent(name)}`);
    el.fileNameInput.value = data.file.name;
    setEditorValue(data.file.content);
    state.selectedFile = data.file.name;
    state.dirty = false;
    cacheFileContent(data.file.name, data.file.content);
    addOpenTab(data.file.name);
    renderFiles(state.files.length ? state.files : state.cache.files, state.files.length ? "board" : "cache");
    appendTerminal(`Opened ${data.file.name}`, "ok");
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

function askSaveName(current) {
  const fallback = current && current !== "untitled.py" ? current : "new_file.py";
  const name = window.prompt("File name to save on board:", fallback);
  return name ? name.trim() : "";
}

async function saveFile() {
  let name = el.fileNameInput.value.trim();
  if (state.untitled || !name || name === "untitled.py") {
    name = askSaveName(name);
    if (!name) {
      appendTerminal("Save cancelled", "warn");
      return;
    }
    el.fileNameInput.value = name;
  }

  try {
    const data = await api("/api/file", {
      method: "POST",
      body: JSON.stringify({ name, content: el.editor.value }),
    });
    state.selectedFile = data.file.name;
    state.untitled = false;
    state.dirty = false;
    cacheFileContent(data.file.name, el.editor.value);
    delete state.staleFiles[data.file.name];
    addOpenTab(data.file.name);
    appendTerminal(`Saved ${data.file.name} (${data.file.bytes} bytes)`, "ok");
    await refreshFiles({ openCachedSelection: true });
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function deleteFile() {
  const name = el.fileNameInput.value.trim() || state.selectedFile;
  if (!name || state.untitled) {
    appendTerminal("Select a saved board file before deleting", "warn");
    return;
  }
  if (!window.confirm(`Delete ${name} from the board?`)) {
    return;
  }
  try {
    await api("/api/delete", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    delete state.cache.contents[name];
    state.cache.files = state.cache.files.filter((file) => file !== name);
    writeCache();
    state.files = state.files.filter((file) => file !== name);
    state.selectedFile = "";
    state.untitled = false;
    state.dirty = false;
    el.fileNameInput.value = "";
    setEditorValue("");
    state.openTabs = state.openTabs.filter((file) => file !== name);
    renderOpenTabs();
    renderFiles(state.files.length ? state.files : state.cache.files, state.files.length ? "board" : "cache");
    appendTerminal(`Deleted ${name}`, "warn");
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function runFile() {
  const name = el.fileNameInput.value.trim() || state.selectedFile;
  if (!name) {
    if (el.editor.value.trim()) {
      state.selectedFile = "untitled.py";
      state.untitled = true;
      el.fileNameInput.value = "untitled.py";
      addOpenTab("untitled.py");
      state.dirty = true;
    } else {
      appendTerminal("Select or create a .py file before running", "warn");
      return;
    }
  }
  const initialName = el.fileNameInput.value.trim() || state.selectedFile;
  if (!initialName.toLowerCase().endsWith(".py")) {
    appendTerminal("Only .py files can be run", "warn");
    return;
  }
  try {
    if (state.dirty || state.staleFiles[initialName]) {
      appendTerminal(`Saving ${initialName} before run...`, "info");
      await saveFile();
    }
    const runName = el.fileNameInput.value.trim() || state.selectedFile;
    await api("/api/run", {
      method: "POST",
      body: JSON.stringify({ name: runName }),
    });
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function stopProgram() {
  try {
    await api("/api/stop", { method: "POST", body: "{}" });
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function flashFirmware() {
  const file = el.firmwareInput.files[0];
  if (!file) {
    appendTerminal("Choose a .bin firmware file first", "warn");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".bin")) {
    appendTerminal("Firmware file must be .bin", "warn");
    return;
  }
  const address = el.firmwareAddressInput.value.trim() || "0x1000";
  const erase = el.firmwareEraseInput.checked;
  const warning = erase
    ? `Erase flash and write ${file.name} at ${address}?`
    : `Write ${file.name} at ${address}?`;
  if (!window.confirm(warning)) {
    return;
  }

  try {
    setTerminalTab("repl");
    appendTerminal(`Flashing ${file.name} at ${address}...`, "cmd");
    el.flashFirmwareBtn.disabled = true;
    const formData = new FormData();
    formData.append("firmware", file);
    formData.append("address", address);
    formData.append("erase", String(erase));
    const data = await apiForm("/api/firmware/flash", formData);
    appendTerminal(`Firmware flashed: ${data.firmware.name}`, "ok");
    markBoardStorageStale();
    await loadPorts();
  } catch (error) {
    appendTerminal(error.message, "error");
  } finally {
    el.flashFirmwareBtn.disabled = false;
  }
}

async function eraseFlashOnly() {
  if (!window.confirm("Erase the whole board flash without writing firmware?")) {
    return;
  }
  try {
    appendTerminal("Erasing board flash...", "warn");
    el.eraseFlashBtn.disabled = true;
    await api("/api/firmware/erase", { method: "POST", body: "{}" });
    appendTerminal("Board flash erased", "ok");
    markBoardStorageStale();
    await loadPorts();
  } catch (error) {
    appendTerminal(error.message, "error");
  } finally {
    el.eraseFlashBtn.disabled = false;
  }
}

async function setMonitor(active) {
  try {
    setTerminalTab("monitor");
    const endpoint = active ? "/api/monitor/start" : "/api/monitor/stop";
    const data = await api(endpoint, { method: "POST", body: "{}" });
    setStatus(data.status);
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function startUnifiedMonitor() {
  try {
    const data = await api("/api/monitor/start", { method: "POST", body: "{}" });
    setStatus(data.status);
  } catch (error) {
    appendTerminal(error.message, "warn");
  }
}

async function sendTerminalCommand(event) {
  event.preventDefault();
  const command = el.terminalCommand.value.trim();
  if (!command) return;
  el.terminalCommand.value = "";
  try {
    await api("/api/terminal", {
      method: "POST",
      body: JSON.stringify({ command }),
    });
  } catch (error) {
    appendTerminal(error.message, "error");
  }
}

async function pollLogs() {
  try {
    const data = await api(`/api/logs?since=${state.lastLogId}`);
    state.lastLogId = data.last;
    for (const entry of data.entries) {
      appendTerminal(entry.text, entry.stream, entry.time);
    }
  } catch {
  } finally {
    window.setTimeout(pollLogs, 700);
  }
}

function newFile() {
  state.selectedFile = "untitled.py";
  state.untitled = true;
  state.dirty = false;
  el.fileNameInput.value = "untitled.py";
  state.cache.contents["untitled.py"] = "# New MicroPython file\n\n";
  addOpenTab("untitled.py");
  setEditorValue("# New MicroPython file\n\n");
  el.editor.focus();
  appendTerminal("Created untitled file. Save will ask for a board file name.", "info");
}

async function bootWorkspace() {
  const params = new URLSearchParams(window.location.search);
  const requestedTheme = params.get("theme");
  setTheme(requestedTheme || localStorage.getItem("micropython-web-ide-theme") || "dark");
  if (params.get("editor") === "fullscreen") {
    setEditorFullscreen(true);
  }
  if (params.get("terminal") === "collapsed") {
    setTerminalCollapsed(true);
  }
  loadCachedWorkspace();
  const loaded = await loadServerCache();
  if (!loaded) {
    watchServerCache();
  }
  const data = await loadPorts();
  if (data?.ports?.length) {
    await connect({ silent: true });
  }
}

function bindEvents() {
  el.connectBtn.addEventListener("click", () => connect());
  el.disconnectBtn.addEventListener("click", disconnect);
  el.refreshFilesBtn.addEventListener("click", () => refreshFiles());
  el.saveBtn.addEventListener("click", saveFile);
  el.runBtn.addEventListener("click", runFile);
  el.deleteBtn.addEventListener("click", deleteFile);
  el.stopBtn.addEventListener("click", stopProgram);
  el.themeSelect.addEventListener("change", () => setTheme(el.themeSelect.value));
  el.customThemeBtn.addEventListener("click", openThemePanel);
  el.closeThemePanelBtn.addEventListener("click", closeThemePanel);
  el.themeControls.addEventListener("input", (event) => {
    if (!event.target.matches("input[type='color']")) return;
    const values = collectThemeControls();
    setTheme("custom");
    applyCustomTheme(values);
  });
  el.saveThemeBtn.addEventListener("click", () => {
    const values = collectThemeControls();
    writeCustomTheme(values);
    setTheme("custom");
    closeThemePanel();
  });
  el.resetThemeBtn.addEventListener("click", () => {
    writeCustomTheme(DEFAULT_CUSTOM_THEME);
    renderThemeControls();
    setTheme("custom");
  });
  el.fullscreenEditorBtn.addEventListener("click", toggleEditorFullscreen);
  el.newFileBtn.addEventListener("click", newFile);
  el.firmwareInput.addEventListener("change", () => {
    el.firmwareFileLabel.textContent = el.firmwareInput.files[0]?.name || "Select firmware .bin";
  });
  el.flashFirmwareBtn.addEventListener("click", flashFirmware);
  el.eraseFlashBtn.addEventListener("click", eraseFlashOnly);
  el.toggleTerminalBtn.addEventListener("click", toggleTerminal);
  el.clearTerminalBtn.addEventListener("click", () => {
    el.replOutput.textContent = "";
  });
  el.terminalForm.addEventListener("submit", sendTerminalCommand);
  el.editor.addEventListener("keydown", handleEditorKeydown);
  el.editor.addEventListener("input", () => {
    ensureDraftForTyping();
    markEditorDirty();
  });
  el.editor.addEventListener("scroll", syncEditorScroll);
  el.minimapCode.addEventListener("pointerdown", (event) => {
    scrollEditorFromMinimap(event);
    el.minimapCode.setPointerCapture(event.pointerId);
  });
  el.minimapCode.addEventListener("pointermove", (event) => {
    if (event.buttons === 1) scrollEditorFromMinimap(event);
  });
  window.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "j") {
      event.preventDefault();
      toggleTerminal();
      return;
    }
    if (event.key === "Escape" && state.editorFullscreen) {
      setEditorFullscreen(false);
    }
  });
}

bindEvents();
setTerminalTab("repl");
renderOpenTabs();
updateHighlight();
bootWorkspace();
pollLogs();
