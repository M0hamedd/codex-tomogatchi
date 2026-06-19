"use strict";

const fs = require("fs");
const path = require("path");

const FALLBACK_DEFAULT_SETTINGS = {
  xp: { pace: "normal" },
  lifecycle: { deathEnabled: true },
  care: { callStrictness: "normal" },
  overlay: { alwaysOnTop: true, startMode: "compact", startMinimized: false },
  pets: { activePack: "default", starterForm: "" },
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function loadDefaultSettings(root = path.resolve(__dirname, "..")) {
  const configPath = path.join(root, "config", "default-settings.json");
  if (!fs.existsSync(configPath)) {
    return clone(FALLBACK_DEFAULT_SETTINGS);
  }
  return JSON.parse(fs.readFileSync(configPath, "utf8"));
}

module.exports = {
  FALLBACK_DEFAULT_SETTINGS,
  loadDefaultSettings,
};
