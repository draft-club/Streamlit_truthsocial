import argparse, subprocess, json, re, html, ast, time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def parse_iso_dt(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def html_to_text(content: str) -> str:
    if not content:
        return ""
    content = re.sub(r"(?i)<br\s*/?>", "\n", content)
    content = re.sub(r"</p>\s*<p>", "\n\n", content)
    content = re.sub(r"<[^>]+>", "", content)
    return html.unescape(content).strip()


def extract_comment_text(c: Dict[str, Any]) -> str:
    txt = html_to_text(c.get("content") or "")
    if txt:
        return txt

    txt = (c.get("text") or "").strip()
    if txt:
        return txt

    card = c.get("card") or {}
    if isinstance(card, dict):
        url = (card.get("url") or "").strip()
        title = (card.get("title") or "").strip()
        if url and title:
            return f"{title} — {url}"
        if url:
            return url

    media = c.get("media_attachments") or []
    if isinstance(media, list) and media:
        urls = []
        for m in media:
            if isinstance(m, dict):
                u = (m.get("url") or m.get("remote_url") or "").strip()
                if u:
                    urls.append(u)
        if urls:
            return "MEDIA: " + " | ".join(urls)

    return ""


def run_truthbrush(args: List[str]) -> str:
    p = subprocess.run(["truthbrush"] + args, capture_output=True, text=True, check=False)
    # IMPORTANT: keep stdout and stderr separate-ish but we concatenate for debugging
    return (p.stdout or "") + "\n" + (p.stderr or "")


def extract_dict_blocks_simple(text: str) -> List[str]:
    """
    Extract top-level {...} blocks by counting braces.
    Assumption: braces rarely appear inside the HTML content.
    Much more robust than trying to handle quotes/escapes.
    """
    blocks = []
    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    blocks.append(text[start:i+1])
                    start = None
    return blocks


def parse_truthbrush_output(text: str) -> List[Dict[str, Any]]:
    # 1) Try JSON line-by-line (rare)
    items: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    items.append(obj)
            except Exception:
                pass
    if items:
        return items

    # 2) Try python dict blocks (multi-line)
    blocks = extract_dict_blocks_simple(text)
    for b in blocks:
        b = b.strip()
        # First try python literal (most likely)
        try:
            obj = ast.literal_eval(b)
            if isinstance(obj, dict):
                items.append(obj)
                continue
        except Exception:
            pass

        # Then try JSON (fallback)
        try:
            obj = json.loads(b)
            if isinstance(obj, dict):
                items.append(obj)
        except Exception:
            pass

    return items


def fetch_statuses(handle: str) -> List[Dict[str, Any]]:
    return parse_truthbrush_output(run_truthbrush(["statuses", handle]))


def fetch_comments_once(status_id: str, top_num: int, debug: bool = False) -> List[Dict[str, Any]]:
    raw = run_truthbrush(["comments", status_id, "--includeall", "--onlyfirst", str(top_num)])
    if debug:
        with open(f"debug_comments_{status_id}.txt", "w", encoding="utf-8") as f:
            f.write(raw)
    return parse_truthbrush_output(raw)


def fetch_comments(status_id: str, top_num: int, retries: int = 2, debug: bool = False) -> List[Dict[str, Any]]:
    for i in range(retries + 1):
        comments = fetch_comments_once(status_id, top_num, debug=(debug and i == retries))
        if comments or i == retries:
            return comments
        time.sleep(1.0)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--max-comments", type=int, default=5000)
    ap.add_argument("--out", default="posts_last2days_with_comments.json")
    ap.add_argument("--debug-post-id", default="")
    args = ap.parse_args()

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=args.days)

    statuses = fetch_statuses(args.handle)

    selected = []
    for st in statuses:
        created_at = st.get("created_at")
        if not created_at:
            continue
        try:
            dt = parse_iso_dt(created_at)
        except Exception:
            continue
        if dt >= cutoff:
            selected.append(st)

    selected.sort(key=lambda x: parse_iso_dt(x["created_at"]), reverse=True)

    export_posts = []
    for st in selected:
        sid = st.get("id")
        if not sid:
            continue

        debug = (args.debug_post_id == sid)
        comments = fetch_comments(sid, args.max_comments, retries=2, debug=debug)

        post_obj = {
            "id": sid,
            "created_at": st.get("created_at"),
            "url": st.get("url"),
            "replies_count": st.get("replies_count"),
            "reblogs_count": st.get("reblogs_count"),
            "favourites_count": st.get("favourites_count"),
            "content_text": html_to_text(st.get("content") or ""),
            "comments_count_fetched": len(comments),
            "comments": [],
        }

        for c in comments:
            acc = c.get("account") or {}
            post_obj["comments"].append({
                "id": c.get("id"),
                "created_at": c.get("created_at"),
                "url": c.get("url"),
                "author_username": acc.get("username"),
                "author_display_name": acc.get("display_name"),
                "content_text": extract_comment_text(c),
            })

        export_posts.append(post_obj)

    result = {
        "handle": args.handle,
        "generated_at_utc": now_utc.isoformat(),
        "cutoff_utc": cutoff.isoformat(),
        "posts_count": len(export_posts),
        "posts": export_posts,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"OK ✅ Export terminé: {args.out} | posts={len(export_posts)}")


if __name__ == "__main__":
    main()