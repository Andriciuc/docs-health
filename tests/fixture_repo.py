"""Builds a tiny MkDocs repo with git history, shared by the inventory and compare tests."""
import os, shutil, subprocess, tempfile
from pathlib import Path

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull}

DUP = ("This paragraph is repeated on purpose so the duplicate detector has more than "
       "twenty five words to work with in both pages of the fixture.")

MKDOCS = """site_name: T
site_url: https://example.com/t/
nav:
  - Home: index.md
  - Guide:
      - Install: guide/install.md
      - Missing: guide/missing.md
markdown_extensions:
  - pymdownx.snippets:
      base_path: docs/snippets
"""


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)


def write(root, files):
    for rel, text in files.items():
        p = Path(root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def make_a():
    """index (front-matter title, one broken link), a task page using a snippet, an orphan,
    a nav entry for a missing file, and one paragraph duplicated across two pages."""
    repo = Path(tempfile.mkdtemp()) / "a"
    write(repo, {
        "mkdocs.yml": MKDOCS,
        "docs/index.md": f"---\ntitle: Home\n---\n# Home\n\nSee [install](guide/install.md) and [gone](nope.md).\n\n{DUP}\n",
        "docs/guide/install.md": f'# Install\n\n1. Run `apt install x`\n2. Start it\n\n```bash\napt install x\n```\n\n--8<-- "note.md"\n\n{DUP}\n',
        "docs/orphan.md": "# Orphan\n\nNot in nav.\n",
        "docs/snippets/note.md": "A note.\n",
    })
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    return repo


def make_b(a):
    """A copy of A with history: orphan removed, install rewritten, new page replacing the missing nav entry."""
    repo = a.parent / "b"
    shutil.copytree(a, repo)
    (repo / "docs/orphan.md").unlink()
    write(repo, {
        "docs/new.md": "# New\n\nBrand new page.\n",
        "docs/guide/install.md": "# Install\n\nDifferent text now entirely.\n",
        "mkdocs.yml": MKDOCS.replace("Missing: guide/missing.md", "New: new.md"),
    })
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "change")
    return repo
