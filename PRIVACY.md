# Privacy

Codex Tomogatchi is designed to be local-first and counter-based.

## Stored Locally

State is stored under:

```text
${CODEX_HOME:-~/.codex}/codex-tomogatchi/
```

The app stores:

- XP, level, stage, lifecycle status, and timestamps.
- Pet stats: fullness, energy, mood, and stress.
- Aggregate counters: prompts, sessions, turns, tool uses, successful tools, and failed tools.
- Aggregate evolution metadata: care points, missed/answered care-call counts, care mistakes, focus points, training points, DW1-style derived raising stats, and lineage.
- Live reaction metadata: reaction kind, canned message, timestamp, expiry, and sequence id.
- Session-log checkpoints: hashed file path keys, byte offsets, file sizes, mtimes, and whether a session start was already counted.
- Overlay settings and window bounds.

## Never Stored

The app must not store:

- Prompt text.
- Command text.
- Tool output.
- Screenshots.
- Raw hook payloads.
- Raw session-log records.
- File contents from your projects.

## Session Log Reading

The hook-free watcher reads Codex session JSONL logs to infer privacy-safe event classes. It uses raw records only transiently while syncing, then stores aggregate counters and checkpoints.

For test-like tool output, the output text is inspected only in memory to decide whether the live reaction should be `test_pass` or `test_fail`. The output text is discarded.

## Network

The tracker and overlay do not send pet state or Codex activity anywhere. Network access is only used by normal developer tooling such as `npm install`, package builds, or GitHub Actions.

## Inspect Your State

Run:

```powershell
py -3 plugins/codex-tomogatchi/scripts/tomogatchi.py status --json
```

or:

```bash
python3 plugins/codex-tomogatchi/scripts/tomogatchi.py status --json
```
