import subprocess
import sys
import os
import json
import time
from pathlib import Path


def project_root() -> Path:
    # service/utils.py -> service/.. = root
    return Path(__file__).resolve().parents[1]


def get_script_path() -> Path:
    script_name = "export_with_comments.py"
    p = project_root() / script_name
    return p


def run_script(handle, days, max_comments, out_file="", ts_user="", ts_pass=""):
    """
    Executes the scraping script via subprocess.
    Returns: (return_code, stdout, stderr, duration_seconds, out_path_str)
    """
    start_time = time.time()

    root = project_root()
    script_path = get_script_path()

    if not script_path.exists():
        return 1, "", f"Script not found: {script_path}", 0.0, None

    # Always generate an absolute output path
    out_file = (out_file or "").strip()
    if out_file:
        # If user provided a relative name like "test_5.json", put it in root
        out_path = (Path(out_file) if Path(out_file).is_absolute() else (root / out_file)).resolve()
    else:
        out_path = (root / f"results_{handle}_{int(start_time)}.json").resolve()

    cmd = [
        sys.executable,
        str(script_path),
        "--handle", str(handle),
        "--days", str(int(days)),
        "--max-comments", str(int(max_comments)),
        "--out", str(out_path),
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Inject credentials (cover both conventions)
    if ts_user and ts_user.strip():
        u = ts_user.strip()
        env["TRUTHSOCIAL_USERNAME"] = u
        env["truthsocial_username"] = u
    if ts_pass:
        env["TRUTHSOCIAL_PASSWORD"] = ts_pass
        env["truthsocial_password"] = ts_pass

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=str(root),  # IMPORTANT: run from project root
            check=False,
        )
        duration = time.time() - start_time
        return result.returncode, (result.stdout or ""), (result.stderr or ""), duration, str(out_path)
    except Exception as e:
        duration = time.time() - start_time
        return 1, "", str(e), duration, str(out_path)


def load_data(file_path: str):
    try:
        p = Path(file_path)
        if not p.exists():
            return None
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def filter_posts(posts_list, search_term, show_only_with_comments):
    filtered = []
    term = search_term.lower() if search_term else ""

    for post in posts_list:
        content = post.get("content_text", "") or ""
        comments = post.get("comments", []) or []

        if show_only_with_comments and len(comments) == 0:
            continue

        if term:
            match_post = term in content.lower()
            match_comment = any((term in ((c.get("content_text", "") or "").lower())) for c in comments)
            if not match_post and not match_comment:
                continue

        filtered.append(post)

    return filtered
