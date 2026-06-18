const canvas = document.getElementById("petCanvas");
const ctx = canvas.getContext("2d");
const petName = document.getElementById("petName");
const petStage = document.getElementById("petStage");
const progressFill = document.getElementById("progressFill");
const xpText = document.getElementById("xpText");
const moodText = document.getElementById("moodText");
const stressText = document.getElementById("stressText");
const careButtons = [...document.querySelectorAll("[data-care]")];
const syncButton = document.getElementById("syncButton");
const modeButton = document.getElementById("modeButton");
const closeButton = document.getElementById("closeButton");
const toast = document.getElementById("toast");
const resizeGrip = document.getElementById("resizeGrip");
const fullnessMeter = document.getElementById("fullnessMeter");
const energyMeter = document.getElementById("energyMeter");
const moodMeter = document.getElementById("moodMeter");
const stressMeter = document.getElementById("stressMeter");
const fullnessValue = document.getElementById("fullnessValue");
const energyValue = document.getElementById("energyValue");
const moodValue = document.getElementById("moodValue");
const stressValue = document.getElementById("stressValue");
const pathValue = document.getElementById("pathValue");
const careValue = document.getElementById("careValue");
const focusValue = document.getElementById("focusValue");
const workValue = document.getElementById("workValue");
const setupPanel = document.getElementById("setupPanel");
const setupKicker = document.getElementById("setupKicker");
const setupTitle = document.getElementById("setupTitle");
const setupSummary = document.getElementById("setupSummary");
const setupIssueList = document.getElementById("setupIssueList");
const setupDismissButton = document.getElementById("setupDismissButton");
const setupInstallButton = document.getElementById("setupInstallButton");
const setupSyncButton = document.getElementById("setupSyncButton");
const setupDoctorButton = document.getElementById("setupDoctorButton");

let snapshot = null;
let sprite = new Image();
let spriteReady = false;
let animationFrame = 0;
let lastStage = "";
let lastLifecycleStatus = "";
let lastRebornAt = "";
let lastTick = 0;
let bob = 0;
let toastTimer = null;
let activeReaction = null;
let lastReactionId = "";
let lastCareCallId = "";
let particles = [];
let lastDrawTime = 0;
let overlayMode = "compact";
let resizeState = null;
let dismissedSetupSignature = window.localStorage.getItem("tomogatchi.dismissedSetupSignature") || "";

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function loadSprite(url) {
  if (!url || sprite.src === url) {
    return;
  }
  spriteReady = false;
  const next = new Image();
  next.onload = () => {
    sprite = next;
    spriteReady = true;
    animationFrame = 0;
    draw();
  };
  next.onerror = () => {
    spriteReady = false;
    draw();
  };
  next.src = url;
}

function stageLabel(stage) {
  if (stage === "baby") return "Baby";
  if (stage === "teen") return "Teen";
  if (stage === "adult") return "Adult";
  return "Unknown";
}

function pathLabel(path) {
  if (!path) return "";
  return String(path).replace(/(^|-)([a-z])/g, (_match, dash, letter) => `${dash ? " " : ""}${letter.toUpperCase()}`);
}

function careLabel(kind) {
  if (kind === "feed") return "Feed";
  if (kind === "rest") return "Rest";
  if (kind === "play") return "Play";
  if (kind === "comfort") return "Comfort";
  return "Care";
}

function dominantLabel(points) {
  const entries = Object.entries(points || {});
  if (!entries.length) return "None";
  const [key] = entries.reduce((best, item) => {
    const bestValue = Number(best[1] || 0);
    const itemValue = Number(item[1] || 0);
    return itemValue > bestValue ? item : best;
  });
  return pathLabel(key) || "None";
}

function setupSignature(setup) {
  const issues = Array.isArray(setup?.issues) ? setup.issues : [];
  return issues.map((issue) => `${issue.key}:${issue.status}:${issue.detail}`).join("|");
}

function setupNeedsAction(setup) {
  return setup?.severity === "error" || setup?.severity === "warn";
}

function showSetupPanel(show) {
  setupPanel.hidden = !show;
  document.body.classList.toggle("has-setup-panel", show);
}

function renderSetupIssues(issues) {
  setupIssueList.textContent = "";
  const visibleIssues = issues.slice(0, 3);
  for (const issue of visibleIssues) {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    const detail = document.createElement("span");
    const action = document.createElement("em");
    title.textContent = issue.title || "Setup issue";
    detail.textContent = issue.detail || "";
    action.textContent = issue.action || "Run doctor for details.";
    item.dataset.status = issue.status === "error" ? "error" : "warn";
    item.append(title, detail, action);
    setupIssueList.append(item);
  }
  if (issues.length > visibleIssues.length) {
    const more = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = `${issues.length - visibleIssues.length} more checks need attention`;
    more.append(title);
    setupIssueList.append(more);
  }
}

function updateSetupPanel(setup) {
  if (!setupNeedsAction(setup)) {
    dismissedSetupSignature = "";
    window.localStorage.removeItem("tomogatchi.dismissedSetupSignature");
    showSetupPanel(false);
    return;
  }

  const signature = setupSignature(setup);
  if (signature && signature === dismissedSetupSignature) {
    showSetupPanel(false);
    return;
  }

  const issues = Array.isArray(setup.issues) ? setup.issues : [];
  setupKicker.textContent = setup.severity === "error" ? "Setup error" : "Setup warning";
  setupTitle.textContent = setup.severity === "error" ? "Needs a fix" : "Almost ready";
  setupSummary.textContent = setup.summary || "Run doctor for details.";
  renderSetupIssues(issues);
  setupInstallButton.hidden = !issues.some((issue) => ["active-pack", "avatar-config", "pet-assets"].includes(issue.key));
  setupSyncButton.hidden = !issues.some((issue) => issue.key === "session-logs");
  showSetupPanel(true);
}

function formatRemaining(seconds) {
  seconds = Math.max(0, Number(seconds || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function reactionDuration(kind) {
  if (kind === "test_pass" || kind === "test_fail") return 1600;
  if (kind === "death" || kind === "rebirth") return 1800;
  if (kind === "tool_failure") return 950;
  return 760;
}

function startReaction(reaction) {
  if (!reaction?.active || !reaction.kind) {
    return;
  }
  const now = performance.now();
  activeReaction = {
    ...reaction,
    startedAt: now,
    duration: reactionDuration(reaction.kind),
  };
  spawnParticles(reaction.kind, now);
  pulseHud(reaction.kind);
  if (reaction.message) {
    showToast(reaction.message);
  }
}

function pulseHud(kind) {
  const classes = ["react-good", "react-bad", "react-care"];
  document.body.classList.remove(...classes);
  const mapped =
    kind === "tool_failure" || kind === "test_fail" || kind === "death" || kind === "care_miss"
      ? "react-bad"
      : kind === "care" || kind === "care_call" || kind === "care_answered"
        ? "react-care"
        : "react-good";
  document.body.classList.add(mapped);
  setTimeout(() => document.body.classList.remove(mapped), 700);
}

function spawnParticles(kind, now) {
  const good = kind === "tool_success" || kind === "test_pass" || kind === "rebirth" || kind === "care" || kind === "care_answered";
  const bad = kind === "tool_failure" || kind === "test_fail" || kind === "death" || kind === "care_miss";
  if (!good && !bad) {
    return;
  }
  const count = kind === "test_pass" || kind === "rebirth" ? 24 : kind === "death" ? 16 : 12;
  const palette = good ? ["#ffd166", "#68d391", "#fff5e8"] : ["#ff6952", "#a0a7af", "#fff5e8"];
  for (let i = 0; i < count; i += 1) {
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.28;
    const speed = 28 + Math.random() * (good ? 64 : 38);
    particles.push({
      x: 96 + Math.cos(angle) * 24,
      y: 104 + Math.sin(angle) * 18,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - (good ? 18 : 0),
      size: 2 + Math.random() * 3,
      bornAt: now,
      life: 700 + Math.random() * 420,
      color: palette[i % palette.length],
    });
  }
}

function reactionEffect(now) {
  const base = { x: 0, y: 0, scale: 1, rotation: 0, alpha: 1, tint: null, tintAlpha: 0 };
  if (!activeReaction) {
    return base;
  }
  const elapsed = now - activeReaction.startedAt;
  const progress = clamp(elapsed / activeReaction.duration, 0, 1);
  const fade = 1 - progress;
  if (progress >= 1) {
    activeReaction = null;
    return base;
  }

  if (activeReaction.kind === "prompt" || activeReaction.kind === "wake") {
    base.y = -Math.sin(progress * Math.PI) * 18;
    base.scale = 1 + Math.sin(progress * Math.PI) * 0.04;
  } else if (activeReaction.kind === "tool_success" || activeReaction.kind === "care" || activeReaction.kind === "care_answered" || activeReaction.kind === "rebirth") {
    base.y = -Math.sin(progress * Math.PI) * 10;
    base.scale = 1 + Math.sin(progress * Math.PI) * (activeReaction.kind === "rebirth" ? 0.16 : 0.1);
    base.tint = "#68d391";
    base.tintAlpha = 0.15 * fade;
  } else if (activeReaction.kind === "care_call") {
    base.y = -Math.sin(progress * Math.PI * 2) * 6 * fade;
    base.scale = 1 + Math.sin(progress * Math.PI) * 0.07;
    base.tint = "#ffd166";
    base.tintAlpha = 0.16 * fade;
  } else if (activeReaction.kind === "test_pass") {
    base.y = -Math.sin(progress * Math.PI * 2) * 13 * fade;
    base.scale = 1 + Math.sin(progress * Math.PI) * 0.16;
    base.rotation = Math.sin(progress * Math.PI * 4) * 0.04 * fade;
    base.tint = "#ffd166";
    base.tintAlpha = 0.2 * fade;
  } else if (activeReaction.kind === "tool_failure" || activeReaction.kind === "test_fail" || activeReaction.kind === "death" || activeReaction.kind === "care_miss") {
    base.x = Math.sin(progress * Math.PI * 12) * (activeReaction.kind === "death" ? 5 : 9) * fade;
    base.rotation = Math.sin(progress * Math.PI * 8) * 0.08 * fade;
    base.scale = 1 - Math.sin(progress * Math.PI) * (activeReaction.kind === "death" ? 0.05 : 0.02);
    base.alpha = activeReaction.kind === "death" ? 0.55 + 0.45 * fade : 1;
    base.tint = "#ff6952";
    base.tintAlpha = 0.18 * fade;
  }
  return base;
}

function setMeter(fill, valueNode, value, invert = false) {
  const numeric = clamp(Number(value || 0), 0, 100);
  fill.style.width = `${Math.round(numeric)}%`;
  valueNode.textContent = String(Math.round(numeric));
  fill.dataset.level = invert && numeric > 70 ? "bad" : numeric < 30 ? "low" : "ok";
}

function updateHud(next) {
  const status = next.lifecycle?.status || "alive";
  const dead = status === "dead";
  overlayMode = next.overlay?.mode === "full" ? "full" : "compact";
  document.body.classList.toggle("full-mode", overlayMode === "full");
  document.body.classList.toggle("dead", dead);
  petName.textContent = next.displayName || "Tomogatchi";
  const path = pathLabel(next.evolution?.path);
  petStage.textContent = dead ? "Dead" : path ? `${stageLabel(next.stage)} | ${path}` : stageLabel(next.stage);
  const xp = Number(next.xp || 0);
  const progress = Number.isFinite(next.progress) ? next.progress : 0;
  const xpToNext = Number(next.xpToNext || 0);
  const activeCall = !dead && next.careCall?.active ? next.careCall : null;
  progressFill.style.width = `${Math.round(clamp(progress, 0, 1) * 100)}%`;
  xpText.textContent = dead
    ? `Rebirth in ${formatRemaining(next.lifecycle?.rebirthInSeconds)}`
    : next.nextXp == null
      ? `${xp} XP | Max stage`
      : `${xp} XP | ${xpToNext} to next`;
  moodText.textContent = dead ? "Waiting" : activeCall ? `Wants ${careLabel(activeCall.kind)}` : `Mood ${next.stats?.mood ?? 0}`;
  stressText.textContent = dead
    ? `Deaths ${next.lifecycle?.deaths ?? 0}`
    : activeCall
      ? `${formatRemaining(activeCall.responseInSeconds)} left`
      : `Stress ${next.stats?.stress ?? 0}`;
  document.body.classList.toggle("needs-care", Boolean(activeCall));
  careButtons.forEach((button) => {
    button.disabled = dead;
    button.classList.toggle("requested", Boolean(activeCall && activeCall.kind === button.dataset.care));
  });
  modeButton.title = overlayMode === "full" ? "Compact" : "Expand";
  modeButton.setAttribute("aria-label", overlayMode === "full" ? "Compact" : "Expand");
  setMeter(fullnessMeter, fullnessValue, next.stats?.fullness);
  setMeter(energyMeter, energyValue, next.stats?.energy);
  setMeter(moodMeter, moodValue, next.stats?.mood);
  setMeter(stressMeter, stressValue, next.stats?.stress, true);
  pathValue.textContent = pathLabel(next.evolution?.path) || "Starter";
  const answered = Number(next.evolution?.careCalls?.answered || 0);
  const missed = Number(next.evolution?.careCalls?.missed || 0);
  careValue.textContent = `${answered}/${missed}`;
  focusValue.textContent = dominantLabel(next.evolution?.focusPoints);
  workValue.textContent = String(Number(next.counters?.turns || 0));
}

function showToast(message) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("show");
  toastTimer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2400);
}

function applySnapshot(next) {
  snapshot = next;
  updateHud(next);
  updateSetupPanel(next.setup);
  const status = next.lifecycle?.status || "alive";
  const rebornAt = next.lifecycle?.rebornAt || "";
  const reaction = next.reaction;
  const reactionStarted = Boolean(reaction?.active && reaction.id && reaction.id !== lastReactionId);
  if (reactionStarted) {
    lastReactionId = reaction.id;
    startReaction(reaction);
  } else if (next.careCall?.active && next.careCall.id && next.careCall.id !== lastCareCallId) {
    lastCareCallId = next.careCall.id;
    showToast(`Wants ${careLabel(next.careCall.kind)}`);
  } else if (lastLifecycleStatus && status !== lastLifecycleStatus) {
    showToast(status === "dead" ? "Tomogatchi died. Rebirth queued." : `Reborn as ${next.displayName || "baby"}`);
  } else if (lastRebornAt && rebornAt && rebornAt !== lastRebornAt) {
    showToast(`Reborn as ${next.displayName || "baby"}`);
  } else if (lastStage && next.stage !== lastStage) {
    document.body.animate(
      [
        { transform: "scale(1)" },
        { transform: "scale(1.025)" },
        { transform: "scale(1)" },
      ],
      { duration: 260, easing: "ease-out" },
    );
    showToast(`Evolved to ${next.displayName || stageLabel(next.stage)}`);
  }
  lastLifecycleStatus = status;
  lastRebornAt = rebornAt;
  if (next.stage !== lastStage) {
    lastStage = next.stage;
  }
  if (!next.careCall?.active) {
    lastCareCallId = "";
  }
  loadSprite(next.spriteUrl);
  draw(performance.now());
}

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawFallback() {
  clearCanvas();
  ctx.save();
  ctx.fillStyle = "rgba(20, 24, 30, 0.78)";
  ctx.strokeStyle = "rgba(255, 250, 242, 0.4)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.roundRect(38, 42, 116, 116, 24);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "rgba(255, 250, 242, 0.78)";
  ctx.font = "700 14px system-ui";
  ctx.textAlign = "center";
  ctx.fillText("Loading", 96, 104);
  ctx.restore();
}

function drawParticles(now) {
  particles = particles.filter((particle) => now - particle.bornAt < particle.life);
  for (const particle of particles) {
    const age = now - particle.bornAt;
    const progress = clamp(age / particle.life, 0, 1);
    const x = particle.x + particle.vx * (age / 1000);
    const y = particle.y + particle.vy * (age / 1000) + 42 * progress * progress;
    ctx.save();
    ctx.globalAlpha = 1 - progress;
    ctx.fillStyle = particle.color;
    ctx.beginPath();
    ctx.arc(x, y, particle.size * (1 - progress * 0.35), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

function draw(now = performance.now()) {
  if (!snapshot || !spriteReady || !sprite.complete) {
    drawFallback();
    return;
  }

  const frame = snapshot.frame || { width: 192, height: 208, columns: 8, rows: 9 };
  const row = 0;
  const frameCount = rowFrameCount(frame, row);
  const column = animationFrame % frameCount;
  const sx = column * frame.width;
  const sy = row * frame.height;
  const y = Math.round(Math.sin(bob) * 3);
  const effect = reactionEffect(now);

  clearCanvas();
  ctx.save();
  ctx.translate(canvas.width / 2 + effect.x, canvas.height / 2 + y + effect.y);
  ctx.rotate(effect.rotation);
  ctx.scale(effect.scale, effect.scale);
  ctx.globalAlpha = effect.alpha;
  ctx.drawImage(sprite, sx, sy, frame.width, frame.height, -canvas.width / 2, -canvas.height / 2, canvas.width, canvas.height);
  if (effect.tint && effect.tintAlpha > 0) {
    ctx.globalCompositeOperation = "source-atop";
    ctx.globalAlpha = effect.tintAlpha;
    ctx.fillStyle = effect.tint;
    ctx.fillRect(-canvas.width / 2, -canvas.height / 2, canvas.width, canvas.height);
  }
  ctx.restore();
  drawParticles(now);
}

function rowFrameCount(frame, row) {
  const rowFrames = Array.isArray(frame.rowFrames) ? frame.rowFrames : [];
  const count = Number(rowFrames[row] || frame.frameCount || frame.columns || 1);
  return Math.max(1, Math.min(Number(frame.columns || count), count));
}

function tick(now) {
  const hasLiveEffect = Boolean(activeReaction || particles.length);
  if (now - lastTick > 135) {
    lastTick = now;
    const frame = snapshot && snapshot.frame ? snapshot.frame : { columns: 8, rowFrames: [6] };
    animationFrame = (animationFrame + 1) % rowFrameCount(frame, 0);
    bob += 0.42;
    draw(now);
  } else if (hasLiveEffect && now - lastDrawTime > 16) {
    draw(now);
  }
  lastDrawTime = now;
  window.requestAnimationFrame(tick);
}

async function callCare(kind, button) {
  button.disabled = true;
  try {
    const next = await window.tomogatchi.care(kind);
    applySnapshot(next);
  } finally {
    if (snapshot?.lifecycle?.status !== "dead") {
      button.disabled = false;
    }
  }
}

async function runSetupAction(button, action, successMessage) {
  button.disabled = true;
  try {
    const next = await action();
    applySnapshot(next);
    showToast(successMessage);
  } catch (error) {
    showToast(error?.message || "Setup action failed");
  } finally {
    button.disabled = false;
  }
}

careButtons.forEach((button) => {
  button.addEventListener("click", () => callCare(button.dataset.care, button));
});

syncButton.addEventListener("click", async () => {
  syncButton.disabled = true;
  try {
    const next = await window.tomogatchi.sync();
    applySnapshot(next);
  } finally {
    syncButton.disabled = false;
  }
});

setupInstallButton.addEventListener("click", () => {
  runSetupAction(setupInstallButton, () => window.tomogatchi.install(), "Pet install refreshed");
});

setupSyncButton.addEventListener("click", () => {
  runSetupAction(setupSyncButton, () => window.tomogatchi.sync(), "Sync complete");
});

setupDoctorButton.addEventListener("click", () => {
  runSetupAction(setupDoctorButton, () => window.tomogatchi.doctor(), "Doctor refreshed");
});

setupDismissButton.addEventListener("click", () => {
  dismissedSetupSignature = setupSignature(snapshot?.setup);
  if (dismissedSetupSignature) {
    window.localStorage.setItem("tomogatchi.dismissedSetupSignature", dismissedSetupSignature);
  }
  showSetupPanel(false);
});

modeButton.addEventListener("click", async () => {
  modeButton.disabled = true;
  try {
    const nextMode = overlayMode === "full" ? "compact" : "full";
    const next = await window.tomogatchi.setMode(nextMode);
    applySnapshot(next);
  } finally {
    modeButton.disabled = false;
  }
});

closeButton.addEventListener("click", () => {
  window.tomogatchi.close();
});

resizeGrip.addEventListener("pointerdown", (event) => {
  if (!snapshot?.overlay?.bounds) {
    return;
  }
  event.preventDefault();
  resizeGrip.setPointerCapture(event.pointerId);
  resizeState = {
    pointerId: event.pointerId,
    startX: event.screenX,
    startY: event.screenY,
    width: Number(snapshot.overlay.bounds.width || window.innerWidth),
    height: Number(snapshot.overlay.bounds.height || window.innerHeight),
    scheduled: false,
    nextWidth: Number(snapshot.overlay.bounds.width || window.innerWidth),
    nextHeight: Number(snapshot.overlay.bounds.height || window.innerHeight),
  };
  document.body.classList.add("resizing");
});

resizeGrip.addEventListener("pointermove", (event) => {
  if (!resizeState || resizeState.pointerId !== event.pointerId) {
    return;
  }
  resizeState.nextWidth = resizeState.width + (event.screenX - resizeState.startX);
  resizeState.nextHeight = resizeState.height + (event.screenY - resizeState.startY);
  if (resizeState.scheduled) {
    return;
  }
  resizeState.scheduled = true;
  window.requestAnimationFrame(async () => {
    if (!resizeState) {
      return;
    }
    resizeState.scheduled = false;
    const next = await window.tomogatchi.resize(resizeState.nextWidth, resizeState.nextHeight);
    snapshot = next;
  });
});

function endResize(event) {
  if (!resizeState || resizeState.pointerId !== event.pointerId) {
    return;
  }
  resizeGrip.releasePointerCapture(event.pointerId);
  resizeState = null;
  document.body.classList.remove("resizing");
}

resizeGrip.addEventListener("pointerup", endResize);
resizeGrip.addEventListener("pointercancel", endResize);

window.tomogatchi.onSnapshot(applySnapshot);
window.tomogatchi.getSnapshot().then(applySnapshot);
window.requestAnimationFrame(tick);
