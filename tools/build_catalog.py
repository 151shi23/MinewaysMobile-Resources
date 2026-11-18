#!/usr/bin/env python3
"""Generate catalog.json from the split JSON files. Standard library only."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["items.json", "creators.json", "collections.json",
         "featured.json", "rankings.json", "search.json"]
REPO = "151shi23/MinewaysMobile-Resources"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    catalog_path = ROOT / "catalog.json"
    old = {}
    if catalog_path.exists():
        old = json.loads(catalog_path.read_text(encoding="utf-8"))
    version = old.get("catalog_version") or "2026-11-17.1"
    updated = old.get("updated_at") or "2026-11-17"
    files = []
    for name in FILES:
        path = ROOT / name
        data = json.loads(path.read_text(encoding="utf-8"))
        count = None
        for key in ("items", "creators", "collections", "rankings"):
            if isinstance(data.get(key), list):
                count = len(data[key])
                break
        entry = {"name": name, "sha256": sha256(path)}
        if count is not None:
            entry["count"] = count
        files.append(entry)
    out = {
        "schema": 2,
        "catalog_version": version,
        "updated_at": updated,
        "repo": REPO,
        "release_model": "per_resource",
        "files": files,
    }
    # 用 bytes 写出，避免 Windows 下 write_text 把换行翻成 CRLF（CI 用 LF 比对会全文件 diff）
    catalog_path.write_bytes(
        (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print("wrote", catalog_path)
    for f in files:
        print(f['name'], f['sha256'][:12], f.get('count', ''))


if __name__ == "__main__":
    main()
