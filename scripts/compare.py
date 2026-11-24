#!/usr/bin/env python3
"""Compare two doc sets (branches, repos, or local vs remote) using inventory.py on each side.

Usage:
  python compare.py SOURCE_A SOURCE_B [--out DIR] [--work DIR] [--label-a X] [--label-b Y]
                    [--shallow] [--similarity 0.6] [-- INVENTORY_ARGS...]

SOURCE forms (A is the baseline/reference, B is the one being checked):
  owner/repo@ref                     e.g. valkey-io/valkey-doc@main
  https://github.com/owner/repo[/tree/ref]
  /local/path                        working tree as-is (uncommitted edits included)
  /local/path@ref                    a ref of a local git repo (read via a --shared clone in --work;
                                     the local repo itself is never modified)
Remote sources are cloned into --work (default ./.docs-compare) with only the named branch(es)
fetched; the same repo is cloned once and the second ref is added as a worktree. --shallow skips history (page ages become unknown).
Args after `--` go to inventory.py for both sides (e.g. --docs-dir . --type-rule 'commands/*.md=reference').

Writes to --out (default ./docs-compare):
  a/, b/                 full inventory of each side
  pages_compare.csv      one row per page: status (same|changed|renamed|only_a|only_b), similarity,
                         word/heading deltas, headings added/removed, last commit each side, newer side
  nav_compare.csv        per shared mkdocs config: entries only_a|only_b|moved|relabeled
  issues_compare.csv     broken links, undefined variables, orphans, missing nav files: fixed|introduced|both
  variables_compare.csv  variables.yml keys/values that differ
  commits_compare.csv    docs commits only in A / only in B (when both sides share git history)
  metrics_compare.csv    summary metrics side by side with delta
  compare.md             digest of all of the above
"""
import argparse, difflib, json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import safeio  # noqa: E402
GH = re.compile(r"^(?:https?://github\.com/)?([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/tree/(.+?))?/?$")

def sh(cmd, **kw):
    """subprocess.run without a shell, never prompting, with a timeout. A timeout counts as a failure."""
    kw.setdefault("env", safeio.GIT_ENV)
    kw.setdefault("timeout", safeio.GIT_TIMEOUT)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"timed out after {kw['timeout']}s")


def run(cmd, **kw):
    r = sh(cmd, **kw)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stderr.strip()}")
    return r.stdout

SAFE_REF = re.compile(r"^(?!-)(?!.*\.\.)[A-Za-z0-9._/+-]{1,200}$")
SAFE_REPO = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


def check_ref(ref):
    """Refuse refs git would read as an option (leading '-') or that hold odd characters."""
    if ref and not SAFE_REF.match(ref):
        sys.exit(f"refusing unsafe ref: {ref!r} (allowed: letters, digits, . _ / + -, not starting with -)")
    return ref


def parse(spec):
    """-> dict(kind=local|remote, path|owner/repo, ref)"""
    src = _parse(spec)
    check_ref(src["ref"])
    if src["kind"] == "remote" and not SAFE_REPO.match(src["repo"]):
        sys.exit(f"refusing unsafe repo name: {src['repo']!r}")
    return src


def _parse(spec):
    path, _, ref = spec.partition("@") if not spec.startswith("http") else (spec, "", "")
    if Path(path).expanduser().exists():
        return {"kind": "local", "path": Path(path).expanduser().resolve(), "ref": ref or None}
    m = GH.match(spec.split("@")[0] if "@" in spec and not spec.startswith("http") else spec)
    if not m:
        sys.exit(f"cannot parse source: {spec} (not a local path or owner/repo[@ref] / GitHub URL)")
    return {"kind": "remote", "repo": f"{m.group(1)}/{m.group(2)}", "ref": ref or m.group(3)}

def materialize(src, work, side, shallow, clones):
    """Return a directory holding the requested tree."""
    if src["kind"] == "local":
        if not src["ref"]:
            return src["path"]
        # separate clone sharing objects: leaves the user's repo untouched (no worktree entries)
        dest = work / f"{side}-local-{src['path'].name}"
        if not dest.exists():
            run(["git", "clone", "-q", "--shared", "--no-checkout", str(src["path"]), str(dest)])
        else:
            run(["git", "-C", str(dest), "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*"])
        ref = src["ref"]
        ok = lambda r: sh(["git", "-C", str(dest), "rev-parse", "--verify", "-q", r]).returncode == 0
        run(["git", "-C", str(dest), "checkout", "-q", "--detach", f"origin/{ref}" if ok(f"origin/{ref}") else ref])
        return dest
    repo = src["repo"]
    # Only the named branches are fetched (no other branches' history is downloaded).
    def fetch_ref(dest, ref):
        if ref:
            cmd = ["git", "-C", str(dest), "fetch", "-q", "origin", f"+refs/heads/{ref}:refs/remotes/origin/{ref}"]
        else:
            cmd = ["git", "-C", str(dest), "fetch", "-q", "origin"]
        if shallow:
            cmd[4:4] = ["--depth", "1"]
        r = sh(cmd)
        if r.returncode and ref:  # a tag or commit, not a branch
            run(["git", "-C", str(dest), "fetch", "-q", "origin", ref] + (["--depth", "1"] if shallow else []))
        return f"origin/{ref}" if ref and r.returncode == 0 else (ref or "origin/HEAD")
    def ensure_clone():
        dest = work / repo.replace("/", "__")
        if not dest.exists():
            cmd = ["git", "clone", "-q", "--no-checkout", "--single-branch", f"https://github.com/{repo}.git", str(dest)]
            if src["ref"]:
                cmd[4:4] = ["--branch", src["ref"]]
            if shallow:
                cmd[4:4] = ["--depth", "1"]
            if sh(cmd).returncode:  # ref may be a tag/commit
                run(["git", "clone", "-q", "--no-checkout", "--single-branch", f"https://github.com/{repo}.git", str(dest)])
        return dest
    if repo not in clones:
        dest = ensure_clone()
        clones[repo] = dest
        target = fetch_ref(dest, src["ref"])
        run(["git", "-C", str(dest), "checkout", "-q", "--detach", target if src["ref"] else "FETCH_HEAD"])
        return dest
    base = clones[repo]
    dest = work / f"{repo.replace('/', '__')}__{side}"
    if dest.exists():
        run(["git", "-C", str(base), "worktree", "remove", "--force", str(dest)])
    target = fetch_ref(base, src["ref"])
    run(["git", "-C", str(base), "worktree", "add", "--detach", str(dest), target if src["ref"] else "FETCH_HEAD"])
    return dest

def label(src):
    base = str(src["path"].name) if src["kind"] == "local" else src["repo"]
    return f"{base}@{src['ref']}" if src["ref"] else (f"{base} (working tree)" if src["kind"] == "local" else base)

def rcsv(p):
    if not Path(p).exists():
        return []
    return safeio.read_csv(p)

def headings(text):
    out, code = [], False
    for ln in text.splitlines():
        if re.match(r"^\s*(```|~~~)", ln):
            code = not code
        elif not code:
            m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", ln)
            if m:
                out.append(m.group(2).strip())
    return out

def norm_text(t):
    """Front matter stripped; one entry per non-blank line, whitespace-normalized (line-level diff is fast)."""
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)
    return [re.sub(r"\s+", " ", l).strip().lower() for l in t.splitlines() if l.strip()]

def load_vars(root, summary):
    for cand in [root / "variables.yml", root / Path(summary.get("docs_dir", ".")).parent / "variables.yml"]:
        if safeio.readable(cand, root):
            try:
                import yaml
            except ImportError:
                return {}
            try:
                with open(cand, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except (OSError, ValueError, yaml.YAMLError) as e:
                safeio.warn(f"cannot read {cand}: {e}")
                return {}
    return {}

def flat(d, pre=""):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flat(v, f"{pre}{k}."))
        else:
            out[f"{pre}{k}"] = "" if v is None else str(v)
    return out

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:
        i = argv.index("--"); argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--out", default="docs-compare"); ap.add_argument("--work", default=".docs-compare")
    ap.add_argument("--label-a"); ap.add_argument("--label-b")
    ap.add_argument("--shallow", action="store_true")
    ap.add_argument("--similarity", type=float, default=0.6, help="min text similarity to call an unmatched pair a rename")
    a = ap.parse_args(argv)

    out, work = Path(a.out), Path(a.work); out.mkdir(parents=True, exist_ok=True); work.mkdir(parents=True, exist_ok=True)
    sa, sb = parse(a.a), parse(a.b)
    clones = {}
    ra = materialize(sa, work.resolve(), "a", a.shallow, clones)
    rb = materialize(sb, work.resolve(), "b", a.shallow, clones)
    la, lb = a.label_a or label(sa), a.label_b or label(sb)

    for side, root in (("a", ra), ("b", rb)):
        r = sh([sys.executable, str(HERE / "inventory.py"), str(root), "--out", str(out / side), *extra])
        if r.returncode:
            sys.exit(f"inventory failed for {side} ({root}):\n{r.stderr}")
    SA = json.loads((out / "a/summary.json").read_text(encoding="utf-8"))
    SB = json.loads((out / "b/summary.json").read_text(encoding="utf-8"))
    PA = {r["path"]: r for r in rcsv(out / "a/pages.csv")}; PB = {r["path"]: r for r in rcsv(out / "b/pages.csv")}
    da = Path(ra) / SA["docs_dir"]; db = Path(rb) / SB["docs_dir"]
    txt = lambda d, p: (d / p).read_text(encoding="utf-8-sig", errors="replace")

    # ---------- pages ----------
    rows = []
    def page_row(status, pa, pb, sim=""):
        A, B = PA.get(pa, {}), PB.get(pb, {})
        ha = headings(txt(da, pa)) if pa else []; hb = headings(txt(db, pb)) if pb else []
        ca, cb = A.get("last_commit", ""), B.get("last_commit", "")
        newer = "" if not (ca and cb) or ca == cb else ("a" if ca > cb else "b")
        wa, wb = int(A.get("words") or 0), int(B.get("words") or 0)
        return {"status": status, "path_a": pa or "", "path_b": pb or "", "title": B.get("title") or A.get("title", ""),
                "similarity": sim, "words_a": wa if pa else "", "words_b": wb if pb else "",
                "words_delta": (wb - wa) if pa and pb else "",
                "headings_added": " | ".join(h for h in hb if h not in ha),
                "headings_removed": " | ".join(h for h in ha if h not in hb),
                "type_a": A.get("type_guess", ""), "type_b": B.get("type_guess", ""),
                "last_commit_a": ca, "last_commit_b": cb, "newer_side": newer}
    for p in sorted(set(PA) & set(PB)):
        ta, tb = norm_text(txt(da, p)), norm_text(txt(db, p))
        if ta == tb:
            rows.append(page_row("same", p, p, 1.0)); continue
        sim = round(difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio(), 3)
        rows.append(page_row("changed", p, p, sim))
    only_a = sorted(set(PA) - set(PB)); only_b = sorted(set(PB) - set(PA))
    # rename detection: same title first, then text similarity
    used_b = set()
    cache_b = {p: norm_text(txt(db, p)) for p in only_b}
    for p in list(only_a):
        if PA[p].get("type_guess") == "release-notes":
            continue  # a new release's notes are not a rename of an old one
        best, score = None, 0.0
        ta = norm_text(txt(da, p))
        for q in only_b:
            if q in used_b or PB[q].get("type_guess") == "release-notes":
                continue
            if PA[p]["title"] and PA[p]["title"] == PB[q]["title"]:
                best, score = q, max(score, 0.99); break
            sm = difflib.SequenceMatcher(None, ta, cache_b[q], autojunk=False)
            if sm.real_quick_ratio() < a.similarity or sm.quick_ratio() < a.similarity:
                continue
            s = sm.ratio()
            if s > score:
                best, score = q, s
        if best and score >= a.similarity:
            used_b.add(best); only_a.remove(p)
            rows.append(page_row("renamed", p, best, round(score, 3)))
    only_b = [q for q in only_b if q not in used_b]
    rows += [page_row("only_a", p, None) for p in only_a] + [page_row("only_b", None, q) for q in only_b]
    fields = list(rows[0]) if rows else ["status"]
    with open(out / "pages_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    # ---------- nav ----------
    NA, NB = rcsv(out / "a/nav.csv"), rcsv(out / "b/nav.csv")
    nav_rows = []
    for cfg in sorted({r["config"] for r in NA} & {r["config"] for r in NB}):
        ea = {r["path"]: r for r in NA if r["config"] == cfg and r["path"]}
        eb = {r["path"]: r for r in NB if r["config"] == cfg and r["path"]}
        for p in sorted(set(ea) | set(eb)):
            x, y = ea.get(p), eb.get(p)
            if x and not y: st = "only_a"
            elif y and not x: st = "only_b"
            elif (x["section"], x["depth"]) != (y["section"], y["depth"]): st = "moved"
            elif x["title"] != y["title"]: st = "relabeled"
            else: continue
            nav_rows.append({"config": cfg, "status": st, "path": p,
                             "section_a": x["section"] if x else "", "section_b": y["section"] if y else "",
                             "title_a": x["title"] if x else "", "title_b": y["title"] if y else "",
                             "depth_a": x["depth"] if x else "", "depth_b": y["depth"] if y else ""})
    unshared = sorted({r["config"] for r in NA} ^ {r["config"] for r in NB})
    with open(out / "nav_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["config", "status", "path", "section_a", "section_b", "title_a", "title_b", "depth_a", "depth_b"])
        w.writeheader(); w.writerows(nav_rows)

    # ---------- issues ----------
    def issue_set(S):
        s = set()
        for l in S.get("broken_internal", []): s.add(("broken_link", l["page"], l["target"]))
        for pg, v in S.get("undefined_variables", {}).items():
            for var in v.split(): s.add(("undefined_variable", pg, var))
        for pg in S.get("orphans_not_in_any_nav", []): s.add(("orphan", pg, ""))
        for cfg, pc in S.get("per_config", {}).items():
            for m in pc.get("nav_missing_files", []): s.add(("nav_missing_file", cfg, m))
        for pg in S.get("pages_multiple_h1", []): s.add(("multiple_h1", pg, ""))
        return s
    IA, IB = issue_set(SA), issue_set(SB)
    iss = [{"issue": k, "where": w_, "detail": d, "status": "fixed_in_b" if (k, w_, d) in IA - IB else
            "introduced_in_b" if (k, w_, d) in IB - IA else "both"} for (k, w_, d) in sorted(IA | IB)]
    with open(out / "issues_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["issue", "where", "detail", "status"]); w.writeheader(); w.writerows(iss)

    # ---------- variables ----------
    VA, VB = flat(load_vars(Path(ra), SA)), flat(load_vars(Path(rb), SB))
    var_rows = [{"key": k, "a": VA.get(k, ""), "b": VB.get(k, ""),
                 "status": "only_a" if k not in VB else "only_b" if k not in VA else "changed"}
                for k in sorted(set(VA) | set(VB)) if VA.get(k) != VB.get(k)]
    with open(out / "variables_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["key", "a", "b", "status"]); w.writeheader(); w.writerows(var_rows)

    # ---------- metrics ----------
    def m(S):
        d = {"pages": S["pages"], "words_total": S["words_total"], "orphans": len(S["orphans_not_in_any_nav"]),
             "broken_internal": len(S["broken_internal"]), "pages_undefined_vars": len(S["undefined_variables"]),
             "duplicate_paragraph_groups": S["duplicate_paragraph_groups"],
             "median_age_days": S["age_days"]["median"], "pages_over_365d": S["age_days"]["over_365"],
             "pages_with_front_matter": max([0] + list(S["front_matter_usage"].values()))}
        for t, n in S["type_mix_guess"].items(): d[f"type:{t}"] = n
        for cfg, pc in S["per_config"].items():
            d[f"nav:{cfg}:pages"] = pc["nav_pages"]; d[f"nav:{cfg}:max_depth"] = pc["max_depth"]
            d[f"nav:{cfg}:missing_files"] = len(pc["nav_missing_files"])
        return d
    MA, MB = m(SA), m(SB)
    met = []
    for k in list(dict.fromkeys(list(MA) + list(MB))):
        x, y = MA.get(k, ""), MB.get(k, "")
        met.append({"metric": k, "a": x, "b": y,
                    "delta": (y - x) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else ""})
    with open(out / "metrics_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["metric", "a", "b", "delta"]); w.writeheader(); w.writerows(met)

    # ---------- commits (only when both sides share git history) ----------
    def git(root, *args):
        r = sh(["git", "-C", str(root), *args])
        return r.stdout.strip() if r.returncode == 0 else None
    sha_a, sha_b = git(ra, "rev-parse", "HEAD"), git(rb, "rev-parse", "HEAD")
    commit_rows, ahead_behind = [], None
    if sha_a and sha_b and sha_a != sha_b:
        # Work in a repo that has both commits. Only our own clones under --work are ever fetched into;
        # a user's local repo is read, never written.
        under_work = lambda r: safeio.inside(r, work)
        scratch = None
        for repo_dir, other in ((rb, ra), (ra, rb)):
            other_sha = sha_a if other is ra else sha_b
            if git(repo_dir, "cat-file", "-e", f"{other_sha}^{{commit}}") is not None:
                scratch = repo_dir; break
            if under_work(repo_dir) and git(repo_dir, "fetch", "-q", str(Path(other).resolve()), other_sha) is not None:
                scratch = repo_dir; break
        if scratch:
            dd = SB["docs_dir"]
            for side, rng in (("only_a", f"{sha_b}..{sha_a}"), ("only_b", f"{sha_a}..{sha_b}")):
                log = git(scratch, "log", "--no-merges", "--format=%h%x09%cs%x09%an%x09%s", rng, "--", dd) or ""
                for ln in log.splitlines():
                    h, d, au, subj = (ln.split("\t") + ["", "", ""])[:4]
                    commit_rows.append({"side": side, "commit": h, "date": d, "author": au, "subject": subj})
            ahead_behind = (sum(r["side"] == "only_a" for r in commit_rows), sum(r["side"] == "only_b" for r in commit_rows))
    with open(out / "commits_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = safeio.DictWriter(f, fieldnames=["side", "commit", "date", "author", "subject"]); w.writeheader(); w.writerows(commit_rows)

    # ---------- digest ----------
    cnt = lambda st: sum(1 for r in rows if r["status"] == st)
    changed = sorted([r for r in rows if r["status"] == "changed"], key=lambda r: float(r["similarity"] or 1))
    md = [f"# Doc set comparison: A = {la}, B = {lb}", "",
          f"- A: `{ra}` (docs_dir `{SA['docs_dir']}`), B: `{rb}` (docs_dir `{SB['docs_dir']}`)",
          f"- pages: A {SA['pages']}, B {SB['pages']}; same {cnt('same')}, changed {cnt('changed')}, "
          f"renamed {cnt('renamed')}, only in A {cnt('only_a')}, only in B {cnt('only_b')}",
          f"- issues: fixed in B {sum(1 for i in iss if i['status']=='fixed_in_b')}, "
          f"introduced in B {sum(1 for i in iss if i['status']=='introduced_in_b')}, in both {sum(1 for i in iss if i['status']=='both')}",
          f"- nav differences (shared configs): {len(nav_rows)}" + (f"; configs on one side only: {unshared}" if unshared else ""),
          f"- variables differing: {len(var_rows)}",
          (f"- docs commits only in A: {ahead_behind[0]}, only in B: {ahead_behind[1]} (commits_compare.csv)" if ahead_behind
           else "- commits: sides don't share git history (or same commit); commits_compare.csv empty")]
    if a.shallow or SA.get("git_shallow") or SB.get("git_shallow"):
        md.append("- SHALLOW history on at least one side: last-commit dates/newer_side are unreliable")
    md += ["", "## Metrics", "| metric | A | B | Δ |", "|---|---|---|---|"]
    md += [f"| {r['metric']} | {r['a']} | {r['b']} | {r['delta']} |" for r in met if r["a"] != r["b"]]
    def lst(title, items, n=25):
        if items:
            md.extend(["", f"## {title} ({len(items)})"] + [f"- {x}" for x in items[:n]] + (["- … see CSV"] if len(items) > n else []))
    lst("Only in A (missing from B)", [f"`{r['path_a']}` {r['title']}" for r in rows if r["status"] == "only_a"])
    lst("Only in B (new in B)", [f"`{r['path_b']}` {r['title']}" for r in rows if r["status"] == "only_b"])
    lst("Renamed/moved", [f"`{r['path_a']}` → `{r['path_b']}` (sim {r['similarity']})" for r in rows if r["status"] == "renamed"])
    lst("Most-changed pages (lowest similarity)", [f"`{r['path_a']}` sim {r['similarity']}, words {r['words_delta']:+}, newer: {r['newer_side'] or '?'}"
                                                    for r in changed], 15)
    lst("Issues introduced in B", [f"{i['issue']}: {i['where']} {i['detail']}" for i in iss if i["status"] == "introduced_in_b"])
    lst("Issues fixed in B", [f"{i['issue']}: {i['where']} {i['detail']}" for i in iss if i["status"] == "fixed_in_b"])
    lst("Nav differences", [f"[{r['config']}] {r['status']}: `{r['path']}` {r['section_a']}→{r['section_b']}" for r in nav_rows])
    lst("Docs commits only in A (candidates to port to B)", [f"{r['commit']} {r['date']} {r['subject']}" for r in commit_rows if r["side"] == "only_a"], 20)
    lst("Docs commits only in B", [f"{r['commit']} {r['date']} {r['subject']}" for r in commit_rows if r["side"] == "only_b"], 20)
    lst("Variables", [f"{r['key']}: `{r['a']}` → `{r['b']}`" for r in var_rows])
    (out / "compare.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:9]))
    print(f"\nwrote {out}/: compare.md pages_compare.csv nav_compare.csv issues_compare.csv variables_compare.csv metrics_compare.csv commits_compare.csv a/ b/")

if __name__ == "__main__":
    main()
