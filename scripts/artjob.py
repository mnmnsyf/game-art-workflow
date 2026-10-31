#!/usr/bin/env python3
"""Asset job ledger for game-art-workflow.

Records briefs, artifacts (with SHA256), stages, gate reviews, spend and events
under <root>/.art-workflow/jobs/<asset-id>/. Standard library only; never
stores credentials and never talks to the network.

    python artjob.py init house_a --kind 3d --title "Village house A"
    python artjob.py artifact house_a raw/concept_v1.png --role concept
    python artjob.py review house_a G2 --artifact concept_v1 --decision approved --by user --evidence "looks good"
    python artjob.py resume house_a
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "game-art-workflow/state@1"
STAGES = [
    "brief", "plan_review_pending", "concept_review_pending", "submitting",
    "asset_review_pending", "processing", "integration_ready",
    "integrated_review_pending", "accepted",
]
SIDE_STAGES = ["waiting_external", "needs_reconcile", "rework", "blocked"]
REVIEW_STAGES = {"plan_review_pending", "concept_review_pending", "asset_review_pending", "integrated_review_pending"}
GATES = ["G1", "G2", "G3"]
DECISIONS = ["approved", "rejected", "changes_requested"]
REVIEWERS = ["user", "delegated_agent"]
ROLES = ["plan", "concept", "reference", "raw_model", "model", "texture",
         "sprite", "sheet", "screenshot", "comparison", "source", "runtime", "other"]

NEXT_HINT = {
    "brief": "Finish the project profile and G1 plan, show it to the user (stage plan_review_pending).",
    "plan_review_pending": "Waiting on the user's G1 decision. End the turn; record it with `review` once they reply.",
    "concept_review_pending": "Show concept candidates (contact_sheet.py helps) and wait for the user's G2 decision. End the turn.",
    "submitting": "A remote submission may already have happened: check with the vendor for an existing job; do not resubmit.",
    "asset_review_pending": "Show the raw model front/back/bottom or the cut-outs/alpha/tiling and wait for the user's G2 decision. End the turn.",
    "processing": "Continue technical processing; appearance changes need review.",
    "integration_ready": "Integrate into the designated scene, run targeted checks, then show in-game screenshots.",
    "integrated_review_pending": "Waiting on the user's G3 decision. End the turn.",
    "accepted": "Accepted. The delivery note lists versions, cost, entry points, and rollback.",
    "waiting_external": "Waiting on external files or actions; check whether the blocker is resolved.",
    "needs_reconcile": "Remote result unclear: recover and download the original job; never resubmit or switch channels and pay again.",
    "rework": "Rework in progress: output a new version (--parent pointing at the old one) and give a same-angle comparison at review.",
    "blocked": "Read the blocker note and confirm the way forward with the user.",
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


class Job:
    def __init__(self, root: Path, asset_id: str):
        if not ID_RE.match(asset_id):
            die(f"asset-id may only contain letters, digits, _ . -: {asset_id!r}")
        self.root = root.resolve()
        self.id = asset_id
        self.base = self.root / ".art-workflow"
        self.dir = self.base / "jobs" / asset_id
        self.state_path = self.dir / "state.json"
        self.events_path = self.dir / "events.jsonl"

    # --- io -------------------------------------------------------------
    def exists(self) -> bool:
        return self.state_path.exists()

    def load(self) -> dict:
        if not self.exists():
            die(f"job not found: {self.dir} (run init first)")
        with self.state_path.open(encoding="utf-8") as f:
            return json.load(f)

    def save(self, state: dict) -> None:
        state["updated"] = now()
        fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".state.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.state_path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def log(self, etype: str, data: dict | None = None, note: str | None = None) -> None:
        rec = {"at": now(), "type": etype}
        if data:
            rec["data"] = data
        if note:
            rec["note"] = note
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def events(self) -> list[dict]:
        if not self.events_path.exists():
            return []
        out = []
        with self.events_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        out.append({"type": "corrupt_line", "raw": line[:200]})
        return out

    @contextmanager
    def lock(self, timeout: float = 10.0, stale: float = 120.0):
        lock = self.dir / ".lock"
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                break
            except FileExistsError:
                try:
                    if time.time() - lock.stat().st_mtime > stale:
                        lock.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    die(f"job is locked: {lock} (another process is writing; delete the file once you are sure none is)")
                time.sleep(0.1)
        try:
            yield
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass

    # --- paths ----------------------------------------------------------
    def resolve(self, p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (self.root / path)

    def rel(self, path: Path) -> str:
        path = path.resolve()
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


# --- checks ---------------------------------------------------------------
def check_artifacts(job: Job, state: dict) -> dict:
    """Return {name: 'ok'|'missing'|'changed'} for every registered artifact."""
    result = {}
    for name, art in state["artifacts"].items():
        p = job.resolve(art["path"])
        if not p.exists():
            result[name] = "missing"
        elif sha256(p) != art["sha256"]:
            result[name] = "changed"
        else:
            result[name] = "ok"
    return result


def review_validity(state: dict, art_status: dict) -> list[dict]:
    out = []
    for r in state["reviews"]:
        art = state["artifacts"].get(r["artifact"])
        valid = bool(art) and art["sha256"] == r["sha256"] and art_status.get(r["artifact"]) == "ok"
        out.append({**r, "valid": valid})
    return out


def gate_summary(reviews: list[dict]) -> dict:
    """Latest decision per (gate, artifact)."""
    latest = {}
    for r in reviews:
        latest[(r["gate"], r["artifact"])] = r
    summary = {g: [] for g in GATES}
    for (gate, _), r in latest.items():
        summary[gate].append(r)
    return summary


# --- commands -------------------------------------------------------------
def cmd_init(job: Job, a) -> None:
    if job.exists():
        die(f"job already exists: {job.dir} (use resume to continue)")
    # only the ledger lives here; raw/ and review/ are created on demand and scratch work goes to a temp dir
    job.dir.mkdir(parents=True, exist_ok=True)
    gdignore = job.base / ".gdignore"
    if not gdignore.exists():
        gdignore.write_text("", encoding="utf-8")
    brief = job.dir / "brief.json"
    template = Path(__file__).resolve().parent.parent / "templates" / "brief.json"
    if template.exists():
        data = json.loads(template.read_text(encoding="utf-8"))
        data.update({"asset_id": job.id, "title": a.title, "kind": a.kind})
        brief.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": SCHEMA, "asset_id": job.id, "title": a.title, "kind": a.kind,
        "created": now(), "updated": None, "stage": "brief", "stage_note": None,
        "artifacts": {}, "reviews": [], "spend": [], "remote": [],
    }
    job.save(state)
    job.log("init", {"kind": a.kind, "title": a.title})
    print(f"created job {job.id}: {job.dir}")


def cmd_artifact(job: Job, a) -> None:
    path = job.resolve(a.path)
    if not path.is_file():
        die(f"file not found: {path}")
    name = a.name or path.stem
    with job.lock():
        state = job.load()
        if name in state["artifacts"]:
            old = state["artifacts"][name]
            if old["sha256"] == sha256(path) and job.resolve(old["path"]).resolve() == path.resolve():
                print(f"artifact {name} already registered and unchanged.")
                return
            die(f"artifact name {name} exists with different content: register the new version under a new name (e.g. {name}_v2) with --parent {name}")
        if a.parent and a.parent not in state["artifacts"]:
            die(f"parent not registered: {a.parent}")
        if a.copy_to_raw:
            dest = job.dir / "raw" / path.name
            dest.parent.mkdir(exist_ok=True)
            if dest.exists() and sha256(dest) != sha256(path):
                die(f"raw/ already has a different file with this name: {dest}")
            shutil.copy2(path, dest)
            path = dest
        art = {
            "path": job.rel(path), "sha256": sha256(path), "bytes": path.stat().st_size,
            "role": a.role, "parent": a.parent, "added": now(), "note": a.note,
        }
        state["artifacts"][name] = art
        job.save(state)
        job.log("artifact", {"name": name, **{k: art[k] for k in ("path", "sha256", "role", "parent")}}, a.note)
    print(f"registered {name}  sha256={art['sha256'][:16]}…  {art['path']}")


def cmd_stage(job: Job, a) -> None:
    if a.stage in SIDE_STAGES and not a.note:
        die(f"entering {a.stage} requires --note naming the concrete blocker")
    with job.lock():
        state = job.load()
        prev = state["stage"]
        if a.stage == "accepted":
            valid = review_validity(state, check_artifacts(job, state))
            if not any(r["gate"] == "G3" and r["decision"] == "approved" and r["valid"] for r in valid):
                die("no valid G3 approval; cannot mark accepted")
        state["stage"], state["stage_note"] = a.stage, a.note
        job.save(state)
        job.log("stage", {"from": prev, "to": a.stage}, a.note)
    print(f"{job.id}: {prev} → {a.stage}")
    print("next: " + NEXT_HINT.get(a.stage, ""))
    if a.stage in REVIEW_STAGES:
        print("GATE: show the material to the user and end the turn. Do not continue until the user replies, "
              "even if the runtime encourages autonomous progress.")


def cmd_review(job: Job, a) -> None:
    if a.by == "delegated_agent" and not a.authorization:
        die("a delegated_agent review requires --authorization quoting the user's delegation")
    with job.lock():
        state = job.load()
        art = state["artifacts"].get(a.artifact)
        if not art:
            die(f"artifact not registered: {a.artifact} (register it with `artifact` first; reviews must bind a specific version)")
        p = job.resolve(art["path"])
        if not p.exists():
            die(f"artifact file missing: {p}")
        if sha256(p) != art["sha256"]:
            die(f"artifact {a.artifact} changed since registration: register it under a new name before reviewing")
        rec = {
            "gate": a.gate, "artifact": a.artifact, "sha256": art["sha256"],
            "decision": a.decision, "by": a.by, "evidence": a.evidence,
            "authorization": a.authorization, "at": now(),
        }
        state["reviews"].append(rec)
        job.save(state)
        job.log("review", rec)
    print(f"{a.gate} {a.decision} ← {a.artifact} ({a.by})")


def cmd_spend(job: Job, a) -> None:
    if a.estimated is None and a.actual is None:
        die("provide at least --estimated or --actual")
    with job.lock():
        state = job.load()
        rec = {"estimated": a.estimated, "actual": a.actual, "unit": a.unit,
               "channel": a.channel, "observed_at": now(), "note": a.note}
        state["spend"].append(rec)
        job.save(state)
        job.log("spend", rec)
    print("spend recorded.")


def cmd_event(job: Job, a) -> None:
    data = None
    if a.data:
        try:
            data = json.loads(a.data)
        except json.JSONDecodeError as e:
            die(f"--data is not valid JSON: {e}")
        if re.search(r"(api[_-]?key|token|secret|password|cookie)", a.data, re.I):
            die("event data looks like it contains credential fields; refusing to write")
    with job.lock():
        state = job.load()
        if a.type == "remote_task" and data:
            state["remote"].append({**data, "at": now()})
            job.save(state)
        job.log(a.type, data, a.note)
    print(f"event recorded: {a.type}")


def totals(state: dict) -> dict:
    t: dict[str, dict] = {}
    for s in state["spend"]:
        u = s.get("unit") or "?"
        d = t.setdefault(u, {"estimated": 0.0, "actual": 0.0})
        d["estimated"] += s.get("estimated") or 0
        d["actual"] += s.get("actual") or 0
    return t


def build_report(job: Job, state: dict) -> dict:
    status = check_artifacts(job, state)
    reviews = review_validity(state, status)
    gates = gate_summary(reviews)
    warnings = []
    for name, st in status.items():
        if st != "ok":
            warnings.append(f"artifact {name} {('is missing' if st == 'missing' else 'has changed')}: {state['artifacts'][name]['path']}")
    for r in reviews:
        if not r["valid"] and r["decision"] == "approved":
            warnings.append(f"{r['gate']} approval of {r['artifact']} is stale (file missing or modified)")
    if state["stage"] in ("submitting", "needs_reconcile"):
        warnings.append("remote submission state unclear: recover the original job first; do not resubmit")
    notices = []
    if state["stage"] in REVIEW_STAGES:
        notices.append(f"gate open ({state['stage']}): waiting on the user's reply; do not proceed past it")
    has_raw = any(v["role"] == "raw_model" for v in state["artifacts"].values())
    if state["kind"] == "3d" and state["stage"] in ("processing", "integration_ready") and not has_raw:
        warnings.append("3D job is in processing but no raw model (raw_model) is registered")
    gate_state = {}
    for g in GATES:
        latest = gates[g]
        if any(r["decision"] == "approved" and r["valid"] for r in latest):
            gate_state[g] = "approved"
        elif latest:
            last = latest[-1]
            gate_state[g] = "stale_approval" if last["decision"] == "approved" else last["decision"]
        else:
            gate_state[g] = "none"
    return {
        "asset_id": state["asset_id"], "title": state["title"], "kind": state["kind"],
        "stage": state["stage"], "stage_note": state["stage_note"],
        "next": NEXT_HINT.get(state["stage"]), "gates": gate_state,
        "artifacts": {k: {**v, "status": status[k]} for k, v in state["artifacts"].items()},
        "spend_totals": totals(state), "remote": state.get("remote", []),
        "warnings": warnings, "notices": notices,
    }


def print_report(rep: dict, events: list[dict] | None = None) -> None:
    print(f"# {rep['asset_id']}  {rep['title'] or ''}  [{rep['kind']}]")
    print(f"stage: {rep['stage']}" + (f" ({rep['stage_note']})" if rep["stage_note"] else ""))
    print("gates: " + "  ".join(f"{g}={s}" for g, s in rep["gates"].items()))
    if rep["artifacts"]:
        print("artifacts:")
        for name, v in rep["artifacts"].items():
            mark = {"ok": "ok", "missing": "MISSING", "changed": "CHANGED"}[v["status"]]
            parent = f" <- {v['parent']}" if v["parent"] else ""
            print(f"  [{mark}] {name} [{v['role']}] {v['path']}{parent}")
    if rep["spend_totals"]:
        print("spend: " + "; ".join(f"{u} estimated {d['estimated']:g} actual {d['actual']:g}" for u, d in rep["spend_totals"].items()))
    for r in rep["remote"]:
        print(f"remote job: {json.dumps(r, ensure_ascii=False)}")
    if events:
        print("recent events:")
        for e in events[-5:]:
            print(f"  {e.get('at', '?')} {e['type']}" + (f" — {e['note']}" if e.get("note") else ""))
    for w in rep["warnings"]:
        print(f"WARNING: {w}")
    for n in rep["notices"]:
        print(f"GATE: {n}")
    print(f"next: {rep['next']}")


def cmd_status(job: Job, a) -> None:
    rep = build_report(job, job.load())
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_report(rep)


def cmd_resume(job: Job, a) -> None:
    state = job.load()
    rep = build_report(job, state)
    job.log("resume", {"warnings": len(rep["warnings"])})
    if a.json:
        rep["recent_events"] = job.events()[-10:]
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_report(rep, job.events())


def cmd_verify(job: Job, a) -> None:
    rep = build_report(job, job.load())
    if rep["warnings"]:
        for w in rep["warnings"]:
            print(f"WARNING: {w}")
        sys.exit(1)
    print(f"{job.id}: {len(rep['artifacts'])} artifact hashes match; all approvals valid.")


def cmd_list(root: Path, a) -> None:
    jobs_dir = root.resolve() / ".art-workflow" / "jobs"
    if not jobs_dir.exists():
        print("no jobs.")
        return
    for d in sorted(jobs_dir.iterdir()):
        sp = d / "state.json"
        if sp.exists():
            s = json.loads(sp.read_text(encoding="utf-8"))
            print(f"{s['asset_id']:<28} {s['stage']:<26} {s.get('title') or ''}")


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="game-art-workflow job ledger")
    p.add_argument("--root", default=".", help="project root (default: current directory)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("asset_id")
    s.add_argument("--kind", required=True, choices=["2d", "3d", "texture", "kit", "mixed"])
    s.add_argument("--title")

    s = sub.add_parser("artifact"); s.add_argument("asset_id"); s.add_argument("path")
    s.add_argument("--role", required=True, choices=ROLES); s.add_argument("--name")
    s.add_argument("--parent"); s.add_argument("--note")
    s.add_argument("--copy-to-raw", action="store_true", help="copy into the job's raw/ to keep the original")

    s = sub.add_parser("stage"); s.add_argument("asset_id")
    s.add_argument("stage", choices=STAGES + SIDE_STAGES); s.add_argument("--note")

    s = sub.add_parser("review"); s.add_argument("asset_id"); s.add_argument("gate", choices=GATES)
    s.add_argument("--artifact", required=True); s.add_argument("--decision", required=True, choices=DECISIONS)
    s.add_argument("--by", required=True, choices=REVIEWERS)
    s.add_argument("--evidence", required=True, help="the user's words or the review basis")
    s.add_argument("--authorization", help="for delegated_agent: quote of the user's delegation")

    s = sub.add_parser("spend"); s.add_argument("asset_id")
    s.add_argument("--estimated", type=float); s.add_argument("--actual", type=float)
    s.add_argument("--unit", required=True); s.add_argument("--channel", required=True); s.add_argument("--note")

    s = sub.add_parser("event"); s.add_argument("asset_id"); s.add_argument("type")
    s.add_argument("--data", help="JSON object"); s.add_argument("--note")

    for name in ("status", "resume"):
        s = sub.add_parser(name); s.add_argument("asset_id"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("verify"); s.add_argument("asset_id")
    sub.add_parser("list")

    a = p.parse_args(argv)
    root = Path(a.root)
    if a.cmd == "list":
        return cmd_list(root, a)
    job = Job(root, a.asset_id)
    {
        "init": cmd_init, "artifact": cmd_artifact, "stage": cmd_stage, "review": cmd_review,
        "spend": cmd_spend, "event": cmd_event, "status": cmd_status, "resume": cmd_resume,
        "verify": cmd_verify,
    }[a.cmd](job, a)


if __name__ == "__main__":
    main()
