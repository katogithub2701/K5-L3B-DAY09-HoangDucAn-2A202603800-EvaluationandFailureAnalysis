"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _row_keys(report: dict) -> set[tuple[str, int]]:
    return {(str(r.get("item_id")), int(r.get("seed"))) for r in report.get("rows") or []}


def _slice_map(report: dict) -> dict[str, tuple[str, ...]]:
    """item_id -> sorted slice tags (one entry per item; rows repeat the same tags)."""
    out: dict[str, tuple[str, ...]] = {}
    for r in report.get("rows") or []:
        out.setdefault(str(r.get("item_id")), tuple(sorted(str(s) for s in (r.get("slices") or []))))
    return out


def _looser(spec_metric: dict, base_metric: dict) -> list[str]:
    """Return the reasons `spec_metric` is laxer than `base_metric` (empty = not looser)."""
    reasons: list[str] = []
    th, bth = spec_metric.get("threshold") or {}, base_metric.get("threshold") or {}
    if "max" in bth and (("max" not in th) or th["max"] > bth["max"]):
        reasons.append("max rose or disappeared")
    if "min" in bth and (("min" not in th) or th["min"] < bth["min"]):
        reasons.append("min fell or disappeared")
    if "max_increase" in bth and (("max_increase" not in th) or th["max_increase"] > bth["max_increase"]):
        reasons.append("max_increase rose or disappeared")
    if bth.get("no_significant_drop") and not th.get("no_significant_drop"):
        reasons.append("no_significant_drop dropped")
    if base_metric.get("blocking") and not spec_metric.get("blocking"):
        reasons.append("blocking became non-blocking")
    return reasons


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    rows = pr.get("rows") or []
    manifest = pr.get("manifest") or {}

    for metric, value in (pr.get("metrics") or {}).items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            problems.append(f"metric {metric} is not a finite number ({value})")

    items, seeds = manifest.get("items"), manifest.get("seeds") or []
    if isinstance(items, int):
        expected = items * len(seeds)
        if len(rows) != expected:
            problems.append(f"rows {len(rows)} != manifest items x seeds ({items} x {len(seeds)} = {expected})")

    keys = [(str(r.get("item_id")), int(r.get("seed"))) for r in rows]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        problems.append(f"duplicate (item_id, seed) rows: {len(duplicates)}")

    base_keys = _row_keys(base)
    present = set(keys)
    missing, extra = sorted(base_keys - present), sorted(present - base_keys)
    if missing:
        problems.append(f"{len(missing)} row(s) missing vs baseline, e.g. {missing[:3]}")
    if extra:
        problems.append(f"{len(extra)} row(s) not in baseline, e.g. {extra[:3]}")

    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s) in the run")

    # A None for a metric the spec grades means the grader crashed and the row silently
    # dropped out of the mean. Only check ids that actually appear in the rows.
    graded = [m["id"] for m in spec.get("metrics") or []
              if m.get("id") in GRADERS and rows and m["id"] in rows[0]]
    for row in rows:
        missing_values = [m for m in graded if row.get(m) is None]
        if missing_values:
            problems.append(f"{row.get('item_id')}@{row.get('seed')}: None for {missing_values} (grader crashed?)")

    # Slice tags must not change between the baseline and the PR.
    base_slices, pr_slices = _slice_map(base), _slice_map(pr)
    for item_id in sorted(set(base_slices) & set(pr_slices)):
        if base_slices[item_id] != pr_slices[item_id]:
            problems.append(f"{item_id}: slice tags {list(pr_slices[item_id])} != baseline {list(base_slices[item_id])}")

    # Ratchet: a report on the same eval set may not be graded by a looser spec. check() has
    # already refused a different eval_set_sha, so applying this whenever a base spec is given
    # is safe and also catches a version-string bump used to dodge the comparison.
    if base_spec is not None:
        by_id = {m["id"]: m for m in base_spec.get("metrics") or []}
        for metric in spec.get("metrics") or []:
            mid = metric.get("id")
            if mid not in by_id:
                continue
            reasons = _looser(metric, by_id[mid])
            if reasons:
                problems.append(f"ratchet: {mid} is looser than base spec ({', '.join(reasons)})")
        current_ids = {m.get("id") for m in spec.get("metrics") or []}
        for mid in sorted(set(by_id) - current_ids):
            problems.append(f"ratchet: metric {mid} disappeared from the spec")

        base_slices_spec = {(s.get("name"), s.get("metric")): s for s in base_spec.get("slices") or []}
        current_slices = {(s.get("name"), s.get("metric")): s
                          for s in spec.get("slices") or []}
        for key, old in base_slices_spec.items():
            new = current_slices.get(key)
            if new is None:
                problems.append(f"ratchet: slice {key[0]}/{key[1]} disappeared")
                continue
            if "min" in old and (("min" not in new) or new["min"] < old["min"]):
                problems.append(f"ratchet: slice {key[0]}/{key[1]} min fell or disappeared")
            if old.get("no_significant_drop") and not new.get("no_significant_drop"):
                problems.append(f"ratchet: slice {key[0]}/{key[1]} lost no_significant_drop")
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: slice {key[0]}/{key[1]} became non-blocking")
    return problems



def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices") or []:
        name, metric = entry["name"], entry["metric"]
        current = per_item(pr, metric, slice_name=name)
        previous = per_item(base, metric, slice_name=name)
        value = sum(current.values()) / len(current) if current else None
        verdict, note = "ok", ""
        mid = f"slice:{name}/{metric}"
        if not current:
            verdict, note = "missing", "no rows in this slice"
        elif "min" in entry and value < entry["min"]:
            verdict = "fail"
        if entry.get("no_significant_drop") and current and previous:
            keys = sorted(set(current) & set(previous))
            if keys:
                diffs = [current[k] - previous[k] for k in keys]
                d, lo, hi = stats.paired_bootstrap(diffs, [0.0] * len(diffs),
                                                   n_resamples=bs.get("n_resamples", 1000),
                                                   rng=bs.get("rng", 2027))
                note = (f"{note} Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]").strip()
                if hi < 0:
                    verdict = "fail"
        if verdict != "ok" and entry.get("blocking", True):
            blocked.append(mid)
        label = "BLOCK" if verdict == "fail" and entry.get("blocking", True) else verdict
        shown = "—" if value is None else f"{value:.4f}"
        lines.append(f"  {mid:<32} {shown:<8} {json.dumps(entry, ensure_ascii=False):<52} {note:<26} {label}")
    return blocked, lines



def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
