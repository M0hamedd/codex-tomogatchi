#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");

const args = process.argv.slice(2);

if (args.length === 0) {
  console.error("Usage: node scripts/run_python.js <script.py> [...args]");
  process.exit(2);
}

const candidates = [];

if (process.env.PYTHON) {
  candidates.push({ command: process.env.PYTHON, prefix: [], label: "$PYTHON" });
}

if (process.platform === "win32") {
  candidates.push({ command: "py", prefix: ["-3"], label: "py -3" });
  candidates.push({ command: "python3", prefix: [], label: "python3" });
  candidates.push({ command: "python", prefix: [], label: "python" });
} else {
  candidates.push({ command: "python3", prefix: [], label: "python3" });
  candidates.push({ command: "python", prefix: [], label: "python" });
  candidates.push({ command: "py", prefix: ["-3"], label: "py -3" });
}

function supportsPython3(candidate) {
  const probe = spawnSync(
    candidate.command,
    [
      ...candidate.prefix,
      "-c",
      "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)",
    ],
    { stdio: "ignore" },
  );

  return !probe.error && probe.status === 0;
}

const python = candidates.find(supportsPython3);

if (!python) {
  console.error(
    "Python 3 was not found. Install Python 3, or set PYTHON to a Python 3 executable.",
  );
  process.exit(1);
}

const result = spawnSync(python.command, [...python.prefix, ...args], {
  stdio: "inherit",
});

if (result.error) {
  console.error(`Failed to run Python through ${python.label}: ${result.error.message}`);
  process.exit(1);
}

if (result.signal) {
  console.error(`Python process stopped with signal ${result.signal}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
