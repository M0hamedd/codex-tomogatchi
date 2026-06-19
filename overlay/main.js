const { app, BrowserWindow, ipcMain, Menu, Tray, nativeImage, screen } = require("electron");
const { pathToFileURL } = require("url");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const { loadDefaultSettings } = require("./default_settings");

const APP_ROOT = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
const REPO_ROOT = APP_ROOT;
const PLUGIN_ROOT = path.join(APP_ROOT, "plugins", "codex-tomogatchi");
const PLUGIN_SCRIPT = path.join(PLUGIN_ROOT, "scripts", "tomogatchi.py");
const CODEX_HOME = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
const STATE_PATH = process.env.CODEX_TOMOGATCHI_STATE || path.join(CODEX_HOME, "codex-tomogatchi", "state.json");
const SETTINGS_PATH = process.env.CODEX_TOMOGATCHI_SETTINGS || path.join(CODEX_HOME, "codex-tomogatchi", "settings.json");
const OVERLAY_STATE_PATH = path.join(CODEX_HOME, "codex-tomogatchi", "overlay-state.json");
const OVERLAY_LOG_PATH = path.join(CODEX_HOME, "codex-tomogatchi", "overlay.log");
const PET_ROOT = path.join(CODEX_HOME, "pets");
const STAGES = ["baby", "teen", "adult"];
const PACK_ID_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const THRESHOLDS = { baby: 0, teen: 90, adult: 260 };
const COMPACT_SIZE = { width: 340, height: 330 };
const FULL_SIZE = { width: 560, height: 680 };
const MIN_SIZE = { width: 280, height: 260 };
const FRAME = {
  width: 192,
  height: 208,
  columns: 8,
  rows: 9,
  rowFrames: [6, 8, 8, 4, 5, 8, 6, 6, 6],
};

const DEFAULT_SETTINGS = loadDefaultSettings(APP_ROOT);
const SETUP_CHECK_TTL_MS = 15000;
const ACTIONABLE_DOCTOR_WARNINGS = new Set([
  "active pet pack",
  "Codex avatar config",
  "Electron dependency",
  "session logs",
  "settings",
  "state",
]);

let mainWindow = null;
let tray = null;
let ownedWatcher = null;
let lastSnapshotJson = "";
let isQuitting = false;
let saveBoundsTimer = null;
let stateWatcherStarted = false;
let overlayMode = "compact";
let pythonRunner = null;
let pythonRunnerChecked = false;
let lastSetupStatus = null;
let lastSetupCheckedAt = 0;

const gotSingleInstanceLock = app.requestSingleInstanceLock();

function logOverlay(event, details = {}) {
  try {
    fs.mkdirSync(path.dirname(OVERLAY_LOG_PATH), { recursive: true });
    fs.appendFileSync(
      OVERLAY_LOG_PATH,
      `${JSON.stringify({ at: new Date().toISOString(), event, ...details })}\n`,
      "utf8",
    );
  } catch {
    // Diagnostics should never be able to break the overlay.
  }
}

function pythonCandidates() {
  const candidates = [];
  if (process.env.PYTHON) {
    candidates.push({ command: process.env.PYTHON, prefix: [], label: process.env.PYTHON });
  }
  candidates.push({ command: "python", prefix: [], label: "python" });
  candidates.push({ command: "python3", prefix: [], label: "python3" });
  if (process.platform === "win32") {
    candidates.push({ command: "py", prefix: ["-3"], label: "py -3" });
  }
  return candidates;
}

function probePython(candidate) {
  const result = spawnSync(candidate.command, [
    ...candidate.prefix,
    "-c",
    "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)",
  ], {
    stdio: "ignore",
    windowsHide: true,
    timeout: 5000,
  });
  return !result.error && result.status === 0;
}

function getPythonRunner() {
  if (pythonRunnerChecked) {
    return pythonRunner;
  }
  pythonRunnerChecked = true;
  pythonRunner = pythonCandidates().find(probePython) || null;
  logOverlay("python", {
    action: pythonRunner ? "found" : "missing",
    runner: pythonRunner ? pythonRunner.label : "",
  });
  return pythonRunner;
}

function missingPythonResult() {
  return {
    error: new Error("Python 3 was not found. Install Python 3, then reopen Codex Tomogatchi."),
    status: null,
    stdout: "",
    stderr: "Python 3 was not found. Install Python 3, then reopen Codex Tomogatchi.",
  };
}

function runPython(args, options = {}) {
  const runner = getPythonRunner();
  if (!runner) {
    return missingPythonResult();
  }
  return spawnSync(runner.command, [...runner.prefix, PLUGIN_SCRIPT, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    windowsHide: true,
    ...options,
  });
}

function runTomogatchi(args, label, timeout = 30000) {
  logOverlay(label, { action: "start" });
  const result = runPython(args, { timeout });
  if (result.error || result.status !== 0) {
    const message = result.stderr || result.error?.message || `${label} failed`;
    logOverlay(label, { action: "failed", status: result.status, message: String(message).slice(0, 240) });
    refreshSetupStatus(true);
    throw new Error(message);
  }
  logOverlay(label, { action: "complete" });
  clearSetupStatusCache();
  return publishSnapshot(true);
}

function clearSetupStatusCache() {
  lastSetupStatus = null;
  lastSetupCheckedAt = 0;
}

function parseDoctorJson(result) {
  try {
    return JSON.parse(result.stdout || "");
  } catch {
    return null;
  }
}

function statusRank(status) {
  if (status === "error") return 2;
  if (status === "warn") return 1;
  return 0;
}

function normalizeDoctorIssue(check) {
  const name = typeof check?.name === "string" ? check.name : "setup";
  const status = check?.status === "error" ? "error" : "warn";
  const detail = typeof check?.detail === "string" ? check.detail : "";

  if (name.startsWith("installed ") && name.endsWith(" pet")) {
    return {
      key: "pet-assets",
      status,
      title: "Pet assets need repair",
      detail: "One or more Codex pet stage files are missing.",
      action: "Click Install pet, then refresh Codex if the custom pet view is stale.",
    };
  }
  if (name === "session logs") {
    return {
      key: "session-logs",
      status,
      title: "No Codex activity found yet",
      detail,
      action: "Open Codex Desktop or run Codex CLI once, then click Sync.",
    };
  }
  if (name === "Codex avatar config") {
    return {
      key: "avatar-config",
      status,
      title: "Codex pet sync is not active",
      detail,
      action: "Click Install pet. Restart or refresh Codex if the custom pet view does not update.",
    };
  }
  if (name === "active pet pack") {
    return {
      key: "active-pack",
      status,
      title: "Active pet pack could not load",
      detail,
      action: "Click Install pet. If this keeps failing, select the default pack from the command line.",
    };
  }
  if (name === "settings") {
    return {
      key: "settings",
      status,
      title: "Settings need attention",
      detail,
      action: "Run setup again or fix the settings JSON shown below.",
    };
  }
  if (name === "state") {
    return {
      key: "state",
      status,
      title: "Pet state needs attention",
      detail,
      action: "Run doctor from this panel. Use reset only if you intend to start over.",
    };
  }
  if (name === "Electron dependency") {
    return {
      key: "electron",
      status,
      title: "Electron dependency is missing",
      detail,
      action: "For source installs, run npm install. For installer builds, reinstall the app.",
    };
  }
  return {
    key: name.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "setup",
    status,
    title: name,
    detail,
    action: "Run doctor for the full setup report.",
  };
}

function issueShouldSurface(check) {
  if (!check || check.status === "ok") {
    return false;
  }
  if (check.status === "error") {
    return true;
  }
  if (app.isPackaged && check.name === "Electron dependency") {
    return false;
  }
  return ACTIONABLE_DOCTOR_WARNINGS.has(check.name) || (typeof check.name === "string" && check.name.startsWith("installed "));
}

function summarizeDoctorChecks(checks) {
  const issueMap = new Map();
  for (const check of checks) {
    if (!issueShouldSurface(check)) {
      continue;
    }
    const issue = normalizeDoctorIssue(check);
    const existing = issueMap.get(issue.key);
    if (!existing || statusRank(issue.status) > statusRank(existing.status)) {
      issueMap.set(issue.key, issue);
    }
  }
  const issues = [...issueMap.values()].sort((left, right) => statusRank(right.status) - statusRank(left.status));
  const hasErrors = issues.some((issue) => issue.status === "error");
  return {
    ok: !hasErrors,
    severity: hasErrors ? "error" : issues.length ? "warn" : "ok",
    summary: hasErrors
      ? "Tomogatchi needs a setup fix before tracking is reliable."
      : issues.length
        ? "Tomogatchi is running, but a setup step is missing."
        : "Tomogatchi setup looks ready.",
    issues,
  };
}

function setupStatusFromFailure(result) {
  const detail = String(result.stderr || result.error?.message || "Doctor could not run.").trim();
  const pythonMissing = Boolean(result.error) && /python/i.test(detail);
  return {
    ok: false,
    severity: "error",
    summary: pythonMissing ? "Python 3 is required before Tomogatchi can track Codex activity." : "Doctor could not finish.",
    checkedAt: new Date().toISOString(),
    checks: [],
    python: { ok: Boolean(getPythonRunner()), runner: getPythonRunner()?.label || "" },
    issues: [
      {
        key: pythonMissing ? "python" : "doctor",
        status: "error",
        title: pythonMissing ? "Python 3 is missing" : "Doctor failed",
        detail,
        action: pythonMissing ? "Install Python 3, then reopen Codex Tomogatchi." : "Run doctor again and check the overlay log if it keeps failing.",
      },
    ],
  };
}

function refreshSetupStatus(force = false) {
  const now = Date.now();
  if (!force && lastSetupStatus && now - lastSetupCheckedAt < SETUP_CHECK_TTL_MS) {
    return lastSetupStatus;
  }

  const result = runPython(["doctor", "--json"], { timeout: 30000 });
  const parsed = parseDoctorJson(result);
  if (!parsed || !Array.isArray(parsed.checks)) {
    lastSetupStatus = setupStatusFromFailure(result);
    lastSetupCheckedAt = now;
    logOverlay("doctor", { action: "failed", message: lastSetupStatus.issues[0]?.detail?.slice(0, 240) || "" });
    return lastSetupStatus;
  }

  const summary = summarizeDoctorChecks(parsed.checks);
  lastSetupStatus = {
    ...summary,
    checkedAt: new Date().toISOString(),
    checks: parsed.checks,
    python: { ok: Boolean(getPythonRunner()), runner: getPythonRunner()?.label || "" },
  };
  lastSetupCheckedAt = now;
  logOverlay("doctor", {
    action: "complete",
    severity: lastSetupStatus.severity,
    issues: lastSetupStatus.issues.length,
  });
  return lastSetupStatus;
}

function copyBundledPetAssets() {
  for (const stage of STAGES) {
    const sourceDir = pluginAssetDir(stage);
    const targetDir = stageDir(stage);
    const sourceManifestPath = path.join(sourceDir, "pet.json");
    const sourceSpritePath = path.join(sourceDir, "spritesheet.webp");
    const targetSpriteName = `spritesheet-${stage}.webp`;

    if (!fs.existsSync(sourceManifestPath) || !fs.existsSync(sourceSpritePath)) {
      continue;
    }

    fs.mkdirSync(targetDir, { recursive: true });
    fs.copyFileSync(sourceSpritePath, path.join(targetDir, targetSpriteName));

    const sourceManifest = readJson(sourceManifestPath) || {};
    const manifest = {
      id: `codex-tomogatchi-${stage}`,
      displayName: sourceManifest.displayName || stage,
      description: sourceManifest.description || "",
      spritesheetPath: targetSpriteName,
    };
    fs.writeFileSync(path.join(targetDir, "pet.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  }
}

function ensurePetAssets() {
  const result = runPython(["install"], { timeout: 30000 });
  if (!result.error && result.status === 0) {
    logOverlay("assets", { action: "install-active-pack" });
    return;
  }
  const message = result.stderr || result.error?.message || "install failed";
  logOverlay("assets", { action: "fallback-bundled", message: String(message).slice(0, 240) });
  copyBundledPetAssets();
}

function isExternalWatcherRunning() {
  if (process.platform !== "win32") {
    return false;
  }
  const ps = [
    "$matches = Get-CimInstance Win32_Process | Where-Object {",
    "($_.Name -in @('py.exe','python.exe','pythonw.exe')) -and",
    "$_.CommandLine -like '*tomogatchi.py*watch*'",
    "};",
    "if ($matches) { 'yes' }",
  ].join(" ");
  const result = spawnSync("powershell.exe", ["-NoProfile", "-Command", ps], {
    encoding: "utf8",
    windowsHide: true,
    timeout: 5000,
  });
  return result.stdout.includes("yes");
}

function startWatcherIfNeeded() {
  if (process.env.CODEX_TOMOGATCHI_OVERLAY_WATCH === "0") {
    logOverlay("watcher", { action: "disabled" });
    return;
  }
  const runner = getPythonRunner();
  if (!runner) {
    logOverlay("watcher", { action: "python-missing" });
    return;
  }
  if (isExternalWatcherRunning()) {
    logOverlay("watcher", { action: "reuse" });
    return;
  }
  ownedWatcher = spawn(runner.command, [...runner.prefix, PLUGIN_SCRIPT, "watch", "--interval", "5"], {
    cwd: REPO_ROOT,
    stdio: "ignore",
    windowsHide: true,
  });
  logOverlay("watcher", { action: "start", pid: ownedWatcher.pid });
  ownedWatcher.on("error", (error) => {
    clearSetupStatusCache();
    logOverlay("watcher", { action: "error", message: error.message });
    ownedWatcher = null;
    publishSnapshot(true);
  });
  ownedWatcher.on("exit", (code, signal) => {
    logOverlay("watcher", { action: "exit", code, signal });
    ownedWatcher = null;
  });
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function mergeSettings(rawSettings) {
  const settings = JSON.parse(JSON.stringify(DEFAULT_SETTINGS));
  const raw = rawSettings && typeof rawSettings === "object" ? rawSettings : {};
  for (const [section, values] of Object.entries(raw)) {
    if (!settings[section] || !values || typeof values !== "object") {
      continue;
    }
    for (const [key, value] of Object.entries(values)) {
      if (Object.prototype.hasOwnProperty.call(settings[section], key)) {
        settings[section][key] = value;
      }
    }
  }
  if (!["slow", "normal", "fast"].includes(settings.xp.pace)) settings.xp.pace = "normal";
  if (!["relaxed", "normal", "strict"].includes(settings.care.callStrictness)) settings.care.callStrictness = "normal";
  settings.lifecycle.deathEnabled = Boolean(settings.lifecycle.deathEnabled);
  settings.overlay.alwaysOnTop = Boolean(settings.overlay.alwaysOnTop);
  settings.overlay.startMode = settings.overlay.startMode === "full" ? "full" : "compact";
  settings.overlay.startMinimized = Boolean(settings.overlay.startMinimized);
  if (typeof settings.pets.activePack !== "string" || !PACK_ID_PATTERN.test(settings.pets.activePack)) {
    settings.pets.activePack = "default";
  }
  if (typeof settings.pets.starterForm !== "string" || (settings.pets.starterForm && !PACK_ID_PATTERN.test(settings.pets.starterForm))) {
    settings.pets.starterForm = "";
  }
  return settings;
}

function readSettings() {
  return mergeSettings(readJson(SETTINGS_PATH));
}

function overlaySettings() {
  return readSettings().overlay;
}

function shouldStartMinimized() {
  if (["1", "true", "yes", "on"].includes(String(process.env.CODEX_TOMOGATCHI_START_MINIMIZED || "").toLowerCase())) {
    return true;
  }
  return overlaySettings().startMinimized;
}

function defaultState() {
  const now = new Date().toISOString();
  return {
    stage: "baby",
    xp: 0,
    level: 1,
    stats: { fullness: 72, energy: 80, mood: 70, stress: 15 },
    counters: { prompts: 0, sessions: 0, turns: 0, toolUses: 0, successfulTools: 0, failedTools: 0 },
    lifecycle: { status: "alive", lastInteractionAt: now, deathDueAt: null, diedAt: null, rebirthDueAt: null },
    reaction: { id: "", kind: "", message: "", at: "", expiresAt: "", sequence: 0 },
    careCall: {
      sequence: 0,
      active: false,
      id: "",
      kind: "",
      reason: "",
      createdAt: null,
      dueAt: null,
      lastClosedAt: null,
      lastStatus: "none",
    },
    evolution: { generation: 1, formId: "sparkbit", formName: "Sparkbit", path: "starter", careMistakes: 0 },
    updatedAt: null,
  };
}

function stageDir(stage) {
  return path.join(PET_ROOT, `codex-tomogatchi-${stage}`);
}

function pluginAssetDir(stage) {
  return path.join(PLUGIN_ROOT, "assets", "stages", stage);
}

function resolveStagePackage(stage) {
  const preferred = stageDir(stage);
  const fallback = pluginAssetDir(stage);
  const packageDir = fs.existsSync(path.join(preferred, "pet.json")) ? preferred : fallback;
  const manifest = readJson(path.join(packageDir, "pet.json")) || {};
  const spriteName = manifest.spritesheetPath || "spritesheet.webp";
  return {
    packageDir,
    manifest,
    spritePath: path.join(packageDir, spriteName),
  };
}

function nextThreshold(stage) {
  if (stage === "baby") {
    return THRESHOLDS.teen;
  }
  if (stage === "teen") {
    return THRESHOLDS.adult;
  }
  return null;
}

function secondsUntil(value) {
  if (!value) {
    return 0;
  }
  const target = Date.parse(value);
  if (!Number.isFinite(target)) {
    return 0;
  }
  return Math.max(0, Math.floor((target - Date.now()) / 1000));
}

function normalizeReaction(rawReaction) {
  const raw = rawReaction && typeof rawReaction === "object" ? rawReaction : {};
  const id = typeof raw.id === "string" ? raw.id : "";
  const kind = typeof raw.kind === "string" ? raw.kind : "";
  const message = typeof raw.message === "string" ? raw.message : "";
  const at = typeof raw.at === "string" ? raw.at : "";
  const expiresAt = typeof raw.expiresAt === "string" ? raw.expiresAt : "";
  return {
    id,
    kind,
    message,
    at,
    expiresAt,
    active: Boolean(id && kind && secondsUntil(expiresAt) > 0),
  };
}

function readSnapshot() {
  const raw = readJson(STATE_PATH) || defaultState();
  const stage = STAGES.includes(raw.stage) ? raw.stage : "baby";
  const pet = resolveStagePackage(stage);
  const next = nextThreshold(stage);
  const xp = Number(raw.xp || 0);
  const base = THRESHOLDS[stage] || 0;
  const lifecycle = raw.lifecycle && typeof raw.lifecycle === "object" ? raw.lifecycle : defaultState().lifecycle;
  const lifecycleStatus = lifecycle.status === "dead" ? "dead" : "alive";
  const evolution = raw.evolution && typeof raw.evolution === "object" ? raw.evolution : defaultState().evolution;
  const assets = raw.assets && typeof raw.assets === "object" ? raw.assets : {};
  const careCall = raw.careCall && typeof raw.careCall === "object" ? raw.careCall : defaultState().careCall;
  const progress = next == null ? 1 : Math.max(0, Math.min(1, (xp - base) / Math.max(1, next - base)));
  return {
    statePath: STATE_PATH,
    codexHome: CODEX_HOME,
    overlay: {
      mode: overlayMode,
      bounds: mainWindow && !mainWindow.isDestroyed() ? mainWindow.getBounds() : readOverlayState().bounds || null,
    },
    setup: refreshSetupStatus(),
    stage,
    petPack: {
      id: typeof assets.activePetPack === "string" ? assets.activePetPack : readSettings().pets.activePack,
      name: typeof assets.activePetPackName === "string" ? assets.activePetPackName : "",
    },
    displayName: evolution.formName || pet.manifest.displayName || stage,
    description: pet.manifest.description || "",
    spriteUrl: fs.existsSync(pet.spritePath) ? pathToFileURL(pet.spritePath).toString() : null,
    spritePath: pet.spritePath,
    frame: FRAME,
    xp,
    level: Number(raw.level || 1),
    nextXp: next,
    xpToNext: next == null ? 0 : Math.max(0, next - xp),
    progress: lifecycleStatus === "dead" ? 0 : progress,
    stats: raw.stats || defaultState().stats,
    counters: raw.counters || defaultState().counters,
    reaction: normalizeReaction(raw.reaction),
    careCall: {
      active: Boolean(careCall.active && careCall.kind),
      id: typeof careCall.id === "string" ? careCall.id : "",
      kind: typeof careCall.kind === "string" ? careCall.kind : "",
      reason: typeof careCall.reason === "string" ? careCall.reason : "",
      createdAt: careCall.createdAt || null,
      dueAt: careCall.dueAt || null,
      responseInSeconds: careCall.active ? secondsUntil(careCall.dueAt) : 0,
      lastStatus: typeof careCall.lastStatus === "string" ? careCall.lastStatus : "none",
    },
    evolution: {
      generation: Number(evolution.generation || 1),
      formId: typeof evolution.formId === "string" ? evolution.formId : "",
      formName: typeof evolution.formName === "string" ? evolution.formName : pet.manifest.displayName || stage,
      path: typeof evolution.path === "string" ? evolution.path : "balanced",
      reason: typeof evolution.reason === "string" ? evolution.reason : "",
      careMistakes: Number(evolution.careMistakes || 0),
      carePoints: evolution.carePoints || {},
      careCalls: evolution.careCalls || {},
      focusPoints: evolution.focusPoints || {},
      trainingPoints: evolution.trainingPoints || {},
    },
    lifecycle: {
      status: lifecycleStatus,
      lastInteractionAt: lifecycle.lastInteractionAt || null,
      deathDueAt: lifecycle.deathDueAt || null,
      diedAt: lifecycle.diedAt || null,
      rebirthDueAt: lifecycle.rebirthDueAt || null,
      rebornAt: lifecycle.rebornAt || null,
      deathInSeconds: lifecycleStatus === "alive" ? secondsUntil(lifecycle.deathDueAt) : 0,
      rebirthInSeconds: lifecycleStatus === "dead" ? secondsUntil(lifecycle.rebirthDueAt) : 0,
      deaths: Number(lifecycle.deaths || 0),
      rebirths: Number(lifecycle.rebirths || 0),
    },
    updatedAt: raw.updatedAt || null,
  };
}

function publishSnapshot(force = false) {
  const snapshot = readSnapshot();
  const encoded = JSON.stringify(snapshot);
  if (!force && encoded === lastSnapshotJson) {
    return snapshot;
  }
  lastSnapshotJson = encoded;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("tomogatchi:snapshot", snapshot);
  }
  return snapshot;
}

function clampNumber(value, min, max) {
  if (max < min) {
    return min;
  }
  const numeric = Number.isFinite(value) ? value : min;
  return Math.max(min, Math.min(max, numeric));
}

function normalizeMode(mode) {
  return mode === "full" ? "full" : "compact";
}

function sizeForMode(mode) {
  return normalizeMode(mode) === "full" ? FULL_SIZE : COMPACT_SIZE;
}

function defaultBounds(mode = overlayMode) {
  const primary = screen.getPrimaryDisplay();
  const size = sizeForMode(mode);
  return {
    width: size.width,
    height: size.height,
    x: Math.max(20, primary.workArea.x + primary.workArea.width - size.width - 28),
    y: Math.max(20, primary.workArea.y + primary.workArea.height - size.height - 28),
  };
}

function clampBounds(bounds, mode = overlayMode) {
  const fallback = defaultBounds(mode);
  const candidate = {
    ...fallback,
    ...(bounds || {}),
  };
  const display = screen.getDisplayMatching(candidate) || screen.getPrimaryDisplay();
  const area = display.workArea;
  const width = Math.round(clampNumber(Number(candidate.width), MIN_SIZE.width, Math.max(MIN_SIZE.width, area.width)));
  const height = Math.round(clampNumber(Number(candidate.height), MIN_SIZE.height, Math.max(MIN_SIZE.height, area.height)));
  return {
    width,
    height,
    x: Math.round(clampNumber(Number(candidate.x), area.x, area.x + area.width - width)),
    y: Math.round(clampNumber(Number(candidate.y), area.y, area.y + area.height - height)),
  };
}

function readOverlayState() {
  const state = readJson(OVERLAY_STATE_PATH);
  return state && typeof state === "object" ? state : {};
}

function saveOverlayState(patch) {
  const current = readOverlayState();
  writeJson(OVERLAY_STATE_PATH, { ...current, ...patch, updatedAt: new Date().toISOString() });
}

function persistWindowBounds() {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }
  saveOverlayState({ bounds: mainWindow.getBounds(), mode: overlayMode });
}

function schedulePersistWindowBounds() {
  clearTimeout(saveBoundsTimer);
  saveBoundsTimer = setTimeout(persistWindowBounds, 250);
}

function makeTrayIcon() {
  const iconPath = path.join(pluginAssetDir("baby"), "contact-sheet.png");
  const image = nativeImage.createFromPath(iconPath);
  if (!image.isEmpty()) {
    return image.resize({ width: 16, height: 16 });
  }
  return nativeImage.createFromDataURL(
    "data:image/svg+xml;utf8," +
      encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" rx="4" fill="#ff6952"/><circle cx="6" cy="7" r="1.5" fill="#111"/><circle cx="10" cy="7" r="1.5" fill="#111"/><path d="M5 11h6" stroke="#111" stroke-width="1.5" stroke-linecap="round"/></svg>',
      ),
  );
}

function buildTrayMenu() {
  return Menu.buildFromTemplate([
    {
      label: "Show",
      click: () => showWindow("tray-show"),
    },
    {
      label: "Hide",
      click: () => hideWindow("tray-hide"),
    },
    { type: "separator" },
    {
      label: "Sync now",
      click: () => {
        try {
          runTomogatchi(["sync"], "tray-sync");
          showWindow("tray-sync");
        } catch {
          showWindow("tray-sync-error");
        }
      },
    },
    {
      label: "Reset from now",
      click: () => {
        try {
          runTomogatchi(["reset", "--confirm", "--from-now"], "tray-reset-from-now", 60000);
          showWindow("tray-reset-from-now");
        } catch {
          showWindow("tray-reset-error");
        }
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        logOverlay("tray", { action: "quit" });
        isQuitting = true;
        app.quit();
      },
    },
  ]);
}

function createTray() {
  if (tray && !tray.isDestroyed()) {
    return;
  }
  tray = new Tray(makeTrayIcon());
  tray.setToolTip("Codex Tomogatchi");
  tray.setContextMenu(buildTrayMenu());
  tray.on("click", () => showWindow("tray-click"));
  logOverlay("tray", { action: "create" });
}

function showWindow(source = "api") {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    return;
  }
  const clamped = clampBounds(mainWindow.getBounds(), overlayMode);
  mainWindow.setBounds(clamped);
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.moveTop();
  if (overlaySettings().alwaysOnTop) {
    mainWindow.setAlwaysOnTop(true, "floating");
  }
  publishSnapshot(true);
  logOverlay("window", { action: "show", source });
}

function setOverlayMode(mode, source = "api") {
  overlayMode = normalizeMode(mode);
  if (mainWindow && !mainWindow.isDestroyed()) {
    const current = mainWindow.getBounds();
    const size = sizeForMode(overlayMode);
    const nextBounds = clampBounds({ ...current, width: size.width, height: size.height }, overlayMode);
    mainWindow.setResizable(true);
    mainWindow.setBounds(nextBounds, true);
    saveOverlayState({ mode: overlayMode, bounds: nextBounds });
    publishSnapshot(true);
    logOverlay("window", { action: "mode", mode: overlayMode, source, bounds: nextBounds });
  } else {
    saveOverlayState({ mode: overlayMode });
  }
  return readSnapshot();
}

function resizeWindow(width, height) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return readSnapshot();
  }
  const current = mainWindow.getBounds();
  const nextBounds = clampBounds({ ...current, width: Number(width), height: Number(height) }, overlayMode);
  mainWindow.setBounds(nextBounds);
  saveOverlayState({ bounds: nextBounds, mode: overlayMode });
  return readSnapshot();
}

function hideWindow(source = "api") {
  if (mainWindow && !mainWindow.isDestroyed()) {
    persistWindowBounds();
    mainWindow.hide();
    logOverlay("window", { action: "hide", source });
  }
}

function recreateWindowAfterCrash(details) {
  logOverlay("renderer", { action: "gone", reason: details?.reason, exitCode: details?.exitCode });
  if (isQuitting) {
    return;
  }
  const crashedWindow = mainWindow;
  mainWindow = null;
  setTimeout(() => {
    if (crashedWindow && !crashedWindow.isDestroyed()) {
      crashedWindow.destroy();
    }
    showWindow("renderer-recreate");
  }, 400);
}

function createWindow() {
  const overlayState = readOverlayState();
  overlayMode = normalizeMode(overlayState.mode || overlaySettings().startMode);
  const bounds = clampBounds(overlayState.bounds, overlayMode);
  const alwaysOnTop = overlaySettings().alwaysOnTop;
  mainWindow = new BrowserWindow({
    ...bounds,
    frame: false,
    transparent: true,
    resizable: true,
    minWidth: MIN_SIZE.width,
    minHeight: MIN_SIZE.height,
    alwaysOnTop,
    skipTaskbar: true,
    hasShadow: false,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  logOverlay("window", { action: "create", bounds });
  if (alwaysOnTop) {
    mainWindow.setAlwaysOnTop(true, "floating");
  }
  mainWindow.loadFile(path.join(__dirname, "renderer.html"));
  mainWindow.once("ready-to-show", () => {
    if (shouldStartMinimized()) {
      hideWindow("ready-minimized");
    } else {
      showWindow("ready");
    }
  });
  mainWindow.on("move", schedulePersistWindowBounds);
  mainWindow.on("resize", schedulePersistWindowBounds);
  mainWindow.on("close", (event) => {
    persistWindowBounds();
    if (!isQuitting) {
      event.preventDefault();
      hideWindow("window-close");
    }
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
    logOverlay("window", { action: "closed" });
  });
  mainWindow.on("unresponsive", () => {
    logOverlay("window", { action: "unresponsive" });
  });
  mainWindow.webContents.on("render-process-gone", (_event, details) => recreateWindowAfterCrash(details));
}

function startStateWatcher() {
  if (stateWatcherStarted) {
    return;
  }
  fs.watchFile(STATE_PATH, { interval: 750 }, () => publishSnapshot());
  stateWatcherStarted = true;
  logOverlay("state-watcher", { action: "start", statePath: STATE_PATH });
}

ipcMain.handle("tomogatchi:getSnapshot", () => readSnapshot());
ipcMain.handle("tomogatchi:care", (_event, kind) => {
  if (!["feed", "rest", "play", "comfort"].includes(kind)) {
    throw new Error(`Unsupported care action: ${kind}`);
  }
  return runTomogatchi(["care", kind], `care-${kind}`);
});
ipcMain.handle("tomogatchi:sync", () => runTomogatchi(["sync"], "sync"));
ipcMain.handle("tomogatchi:install", () => runTomogatchi(["install"], "install"));
ipcMain.handle("tomogatchi:doctor", () => {
  refreshSetupStatus(true);
  return publishSnapshot(true);
});
ipcMain.handle("tomogatchi:setMode", (_event, mode) => setOverlayMode(mode, "ipc"));
ipcMain.handle("tomogatchi:resize", (_event, width, height) => resizeWindow(width, height));
ipcMain.handle("tomogatchi:hide", () => hideWindow("ipc-hide"));
ipcMain.handle("tomogatchi:close", () => hideWindow("ipc-close"));
ipcMain.handle("tomogatchi:quit", () => {
  isQuitting = true;
  app.quit();
});

if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    logOverlay("app", { action: "second-instance" });
    showWindow("second-instance");
  });

  app.whenReady().then(() => {
    logOverlay("app", { action: "start", repoRoot: REPO_ROOT, statePath: STATE_PATH });
    ensurePetAssets();
    createTray();
    startWatcherIfNeeded();
    createWindow();
    startStateWatcher();
  });

  app.on("activate", () => showWindow("activate"));

  app.on("window-all-closed", () => {
    logOverlay("window", { action: "all-closed" });
  });

  app.on("before-quit", () => {
    isQuitting = true;
    persistWindowBounds();
    clearTimeout(saveBoundsTimer);
    fs.unwatchFile(STATE_PATH);
    if (ownedWatcher) {
      ownedWatcher.kill();
      ownedWatcher = null;
    }
    if (tray && !tray.isDestroyed()) {
      tray.destroy();
      tray = null;
    }
    logOverlay("app", { action: "quit" });
  });
}
