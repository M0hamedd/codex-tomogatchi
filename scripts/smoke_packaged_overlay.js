#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const TIMEOUT_MS = Number(process.env.CODEX_TOMOGATCHI_PACKAGED_SMOKE_TIMEOUT_MS || 20000);

function candidateApps() {
  if (process.env.CODEX_TOMOGATCHI_PACKAGED_APP) {
    return [process.env.CODEX_TOMOGATCHI_PACKAGED_APP];
  }
  if (process.platform === "win32") {
    return [path.join(ROOT, "dist", "win-unpacked", "Codex Tomogatchi.exe")];
  }
  if (process.platform === "darwin") {
    return [
      path.join(ROOT, "dist", "mac", "Codex Tomogatchi.app", "Contents", "MacOS", "Codex Tomogatchi"),
      path.join(ROOT, "dist", "mac-arm64", "Codex Tomogatchi.app", "Contents", "MacOS", "Codex Tomogatchi"),
    ];
  }
  return [path.join(ROOT, "dist", "linux-unpacked", "codex-tomogatchi-overlay")];
}

function findPackagedApp() {
  const found = candidateApps().find((candidate) => fs.existsSync(candidate));
  if (!found) {
    throw new Error(`Packaged app was not found. Run npm run package first. Checked: ${candidateApps().join(", ")}`);
  }
  return found;
}

function resourcesDirForApp(appPath) {
  if (process.platform === "darwin") {
    return path.resolve(appPath, "..", "..", "Resources");
  }
  return path.join(path.dirname(appPath), "resources");
}

function assertPackagedResources(appPath) {
  const resourcesDir = resourcesDirForApp(appPath);
  const required = [
    path.join(resourcesDir, "config", "default-settings.json"),
    path.join(resourcesDir, "plugins", "codex-tomogatchi", "scripts", "tomogatchi.py"),
  ];
  for (const filePath of required) {
    if (!fs.existsSync(filePath)) {
      throw new Error(`Packaged resource is missing: ${filePath}`);
    }
  }
}

function readLog(logPath) {
  try {
    return fs.readFileSync(logPath, "utf8");
  } catch {
    return "";
  }
}

function hasEvidence(logText) {
  return logText.includes('"event":"doctor","action":"complete"') && logText.includes('"event":"window","action":"show"');
}

function hasKnownFailure(logText) {
  return logText.includes("ENOTDIR") || logText.includes("app.asar");
}

async function stopProcess(child) {
  if (child.exitCode !== null || child.signalCode !== null) {
    return;
  }

  const closed = new Promise((resolve) => {
    child.once("close", resolve);
  });
  child.kill();
  await Promise.race([closed, new Promise((resolve) => setTimeout(resolve, 3000))]);
}

function removeDir(dirPath) {
  fs.rmSync(dirPath, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}

async function main() {
  if (process.platform === "linux" && !process.env.DISPLAY && !process.env.WAYLAND_DISPLAY) {
    throw new Error("No Linux display is available. Run with xvfb-run -a npm run smoke:packaged.");
  }

  const appPath = findPackagedApp();
  assertPackagedResources(appPath);
  const codexHome = fs.mkdtempSync(path.join(os.tmpdir(), "codex-tomogatchi-smoke-"));
  const smokeCwd = fs.mkdtempSync(path.join(os.tmpdir(), "codex-tomogatchi-cwd-"));
  const logPath = path.join(codexHome, "codex-tomogatchi", "overlay.log");
  const child = spawn(appPath, [], {
    cwd: smokeCwd,
    env: {
      ...process.env,
      CODEX_HOME: codexHome,
      CODEX_TOMOGATCHI_OVERLAY_WATCH: "0",
    },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });

  const startedAt = Date.now();
  try {
    while (Date.now() - startedAt < TIMEOUT_MS) {
      const logText = readLog(logPath);
      if (hasKnownFailure(logText)) {
        throw new Error(`Packaged overlay logged a known startup failure:\n${logText}`);
      }
      if (hasEvidence(logText)) {
        console.log(`Packaged overlay smoke passed: ${appPath}`);
        return;
      }
      if (child.exitCode !== null) {
        throw new Error(`Packaged overlay exited before startup evidence. code=${child.exitCode}\n${stderr}`);
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error(`Timed out waiting for packaged overlay startup evidence.\n${readLog(logPath)}\n${stderr}`);
  } finally {
    await stopProcess(child);
    removeDir(codexHome);
    removeDir(smokeCwd);
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
