const { app, BrowserWindow, ipcMain, Menu, Tray, nativeImage, screen } = require("electron");
const { pathToFileURL } = require("url");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const APP_ROOT = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(__dirname, "..");
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

const DEFAULT_SETTINGS = {
  xp: { pace: "normal" },
  lifecycle: { deathEnabled: true },
  care: { callStrictness: "normal" },
  overlay: { alwaysOnTop: true, startMode: "compact", startMinimized: false },
  pets: { activePack: "default", starterForm: "" },
};

let mainWindow = null;
let tray = null;
let ownedWatcher = null;
let lastSnapshotJson = "";
let isQuitting = false;
let saveBoundsTimer = null;
let stateWatcherStarted = false;
let overlayMode = "compact";

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

function runPython(args, options = {}) {
  return spawnSync("py", ["-3", PLUGIN_SCRIPT, ...args], {
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
    throw new Error(message);
  }
  logOverlay(label, { action: "complete" });
  return publishSnapshot(true);
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
  if (isExternalWatcherRunning()) {
    logOverlay("watcher", { action: "reuse" });
    return;
  }
  ownedWatcher = spawn("py", ["-3", PLUGIN_SCRIPT, "watch", "--interval", "5"], {
    cwd: REPO_ROOT,
    stdio: "ignore",
    windowsHide: true,
  });
  logOverlay("watcher", { action: "start", pid: ownedWatcher.pid });
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
