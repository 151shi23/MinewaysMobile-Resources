#!/usr/bin/env python3
"""Validate the split resource catalog. Exit 1 on any hard error."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FILES = ["items.json", "creators.json", "collections.json",
         "featured.json", "rankings.json", "search.json"]
REPO = "151shi23/MinewaysMobile-Resources"
TAG_RE = re.compile(r"^res-[a-z0-9-]+-v[0-9][a-z0-9.]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
CAT_RE = re.compile(r"^cat-[a-z0-9-]{1,60}$")
PROVIDERS = {"baidu", "quark", "aliyun", "123", "lanzou", "other"}
TYPES = {"map", "model", "texture", "other"}
errors = []


def err(msg):
    errors.append(msg)


def load(name):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except Exception as e:
        err(f"{name}: cannot parse: {e}")
        return {}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def https(s):
    try:
        u = urlparse(s or "")
        return u.scheme == "https" and bool(u.netloc)
    except Exception:
        return False


def release_url(tag, asset):
    return f"https://github.com/{REPO}/releases/download/{tag}/{asset}"


def under_release(url, tag):
    return (url or "").startswith(
        f"https://github.com/{REPO}/releases/download/{tag}/")


def main():
    catalog = load("catalog.json")
    if catalog.get("schema") != 2:
        err("catalog.json: schema must be 2")
    version = catalog.get("catalog_version", "")
    if not version:
        err("catalog.json: missing catalog_version")
    if catalog.get("repo") != REPO:
        err("catalog.json: repo mismatch")
    declared = {f.get("name"): f for f in catalog.get("files", []) if isinstance(f, dict)}
    for name in FILES:
        if name not in declared:
            err(f"catalog.json: missing file {name}")
            continue
        want = declared[name].get("sha256", "")
        got = sha256(ROOT / name)
        if want != got:
            err(f"{name}: sha256 mismatch (catalog {want[:12]} actual {got[:12]})")

    docs = {name: load(name) for name in FILES}
    for name, doc in docs.items():
        if doc.get("schema") != 2:
            err(f"{name}: schema must be 2")
        if doc.get("catalog_version") != version:
            err(f"{name}: catalog_version mismatch")

    search = docs["search.json"]
    big_ids = set()
    sub_parent = {}
    for i, c in enumerate(search.get("categories", []) or []):
        if not isinstance(c, dict):
            err(f"search.categories[{i}]: not an object")
            continue
        cid = c.get("id", "")
        level = c.get("level", "small")
        if not CAT_RE.match(cid or ""):
            err(f"search.categories[{i}]: bad id")
            continue
        if level not in ("big", "small"):
            err(f"{cid}: level must be big/small")
        if level == "big":
            if c.get("parent"):
                err(f"{cid}: big category cannot have parent")
            big_ids.add(cid)
        else:
            parent = c.get("parent", "")
            if not CAT_RE.match(parent or ""):
                err(f"{cid}: small category needs parent")
            sub_parent[cid] = parent
    for cid, parent in sub_parent.items():
        if parent not in big_ids:
            err(f"{cid}: parent {parent} is not a big category")

    items = docs["items.json"].get("items", [])
    if not isinstance(items, list) or len(items) > 500:
        err("items.json: items must be a list <= 500")
        items = []
    items_by_id = {}
    tags = set()
    for i, it in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(it, dict):
            err(f"{where}: not an object")
            continue
        iid = it.get("id", "")
        if not ID_RE.match(iid or ""):
            err(f"{where}: bad id")
            continue
        if iid in items_by_id:
            err(f"{where}: duplicate id {iid}")
        items_by_id[iid] = it
        if it.get("source") not in ("official", "cloud"):
            err(f"{iid}: bad source")
        if it.get("type") not in TYPES:
            err(f"{iid}: bad type")
        if not it.get("title") or len(it.get("title", "")) > 120:
            err(f"{iid}: bad title")
        if not it.get("license"):
            err(f"{iid}: missing license")
        license_url = it.get("license_url", "")
        if license_url and not https(license_url):
            err(f"{iid}: license_url must be https")
        cat = it.get("category", "")
        sub = it.get("subcategory", "")
        if not CAT_RE.match(cat or ""):
            err(f"{iid}: 大分类 category 必选")
        elif cat not in big_ids:
            err(f"{iid}: unknown big category {cat}")
        if not CAT_RE.match(sub or ""):
            err(f"{iid}: 小分类 subcategory 必选")
        elif sub_parent.get(sub) != cat:
            err(f"{iid}: subcategory {sub} not under {cat}")
        if it.get("third_party") and not (it.get("attribution") or "").strip():
            err(f"{iid}: third_party 需要 attribution 声明")
        model = it.get("model") or {}
        if isinstance(model, dict) and model:
            if model.get("protocol") and not re.match(r"^[A-Za-z0-9._:-]{1,40}$",
                                                      str(model.get("protocol"))):
                err(f"{iid}: bad model.protocol")
            mu = model.get("protocol_url", "")
            if mu and not https(mu):
                err(f"{iid}: model.protocol_url must be https")
            if len(str(model.get("usage", ""))) > 600:
                err(f"{iid}: model.usage too long")
        if not it.get("updated_at"):
            err(f"{iid}: missing updated_at")
        if len(it.get("summary", "")) > 500:
            err(f"{iid}: summary too long")
        if it.get("source") == "official":
            tag = it.get("release_tag", "")
            if not TAG_RE.match(tag or ""):
                err(f"{iid}: bad release_tag")
            f = it.get("file") or {}
            asset = f.get("asset_name", "")
            if not asset or "/" in asset or "\\" in asset or ".." in asset:
                err(f"{iid}: bad asset_name")
            if not isinstance(f.get("size"), int) or f.get("size", 0) <= 0:
                err(f"{iid}: bad size")
            if not SHA_RE.match((f.get("sha256") or "").lower()):
                err(f"{iid}: bad sha256")
            if tag and asset and tag in tags:
                err(f"{iid}: duplicate release_tag {tag}")
            tags.add(tag)
            pv = it.get("preview") or {}
            for key in ("cover", "model_3d"):
                u = pv.get(key, "")
                if u and not under_release(u, tag):
                    err(f"{iid}: preview {key} not in same release")
            for j, u in enumerate(pv.get("gallery", []) or []):
                if not under_release(u, tag):
                    err(f"{iid}: gallery[{j}] not in same release")
        elif it.get("source") == "cloud":
            c = it.get("cloud") or {}
            if not https(c.get("share_url", "")):
                err(f"{iid}: cloud share_url must be https")
            provider = it.get("provider") or c.get("provider") or ""
            if provider not in PROVIDERS:
                err(f"{iid}: bad cloud provider")
            if not it.get("reviewed_at"):
                err(f"{iid}: missing reviewed_at")

    creators = docs["creators.json"].get("creators", [])
    creator_ids = set()
    for i, c in enumerate(creators if isinstance(creators, list) else []):
        cid = (c or {}).get("id", "")
        if not ID_RE.match(cid or ""):
            err(f"creators[{i}]: bad id")
        elif cid in creator_ids:
            err(f"creators[{i}]: duplicate id")
        creator_ids.add(cid)
        if not (c or {}).get("name"):
            err(f"creators[{i}]: missing name")
        if (c or {}).get("avatar") and not https(c.get("avatar")):
            err(f"creators[{i}]: avatar must be https")

    for iid, it in items_by_id.items():
        cid = it.get("creator_id", "")
        if cid and cid not in creator_ids:
            err(f"{iid}: creator_id not found: {cid}")

    collections = docs["collections.json"].get("collections", [])
    for i, c in enumerate(collections if isinstance(collections, list) else []):
        cid = (c or {}).get("id", "")
        if not ID_RE.match(cid or ""):
            err(f"collections[{i}]: bad id")
        kind = (c or {}).get("kind")
        if kind not in ("theme", "creator"):
            err(f"collections[{i}]: bad kind")
        ids = c.get("items", [])
        if not isinstance(ids, list):
            err(f"collections[{i}]: items must be a list")
            continue
        for x in ids:
            if x not in items_by_id:
                err(f"collections[{i}]: item not found {x}")
        if kind == "creator":
            own = c.get("creator_id", "")
            if not own or own not in creator_ids:
                err(f"collections[{i}]: creator_id missing/unknown")
            for x in ids:
                it = items_by_id.get(x)
                if it and it.get("creator_id") != own:
                    err(f"collections[{i}]: item {x} belongs to another creator")

    featured = docs["featured.json"].get("ids", [])
    for x in featured if isinstance(featured, list) else []:
        if x not in items_by_id:
            err(f"featured: item not found {x}")

    rankings = docs["rankings.json"].get("rankings", [])
    seen_rank = set()
    for i, r in enumerate(rankings if isinstance(rankings, list) else []):
        rid = (r or {}).get("id", "")
        if not ID_RE.match(rid or ""):
            err(f"rankings[{i}]: bad id")
        if rid in seen_rank:
            err(f"rankings[{i}]: duplicate id")
        seen_rank.add(rid)
        if (r or {}).get("kind") not in ("editorial", "new", "downloads"):
            err(f"rankings[{i}]: bad kind")
        for x in r.get("items", []) or []:
            if x.get("id") not in items_by_id:
                err(f"rankings[{i}]: item not found {x.get('id')}")

    search = docs["search.json"]
    for x in search.get("hot", []) or []:
        if not isinstance(x, str) or len(x) > 40:
            err("search: bad hot word")
    aliases = search.get("aliases", {}) or {}
    for iid in aliases:
        if iid not in items_by_id:
            err(f"search.aliases: unknown item {iid}")

    if errors:
        print("VALIDATION FAILED", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        return 1
    print(f"OK: {len(items_by_id)} items, {len(creator_ids)} creators, "
          f"{len(collections)} collections, {len(rankings)} rankings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
