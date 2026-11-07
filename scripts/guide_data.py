"""Shared local-book loading and prose-preserving navigation conversion."""

from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ANCHOR = re.compile(r'<a id="[^"]+"></a>\s*')
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")


def readable(text, book_link):
    text = ANCHOR.sub("", text)

    def replace_link(match):
        image, label, address = match.groups()
        if image:
            return "图示说明：" + label
        if address.startswith("#"):
            return f"[{label}]({book_link}{address})"
        return match.group(0)

    return LINK.sub(replace_link, text).strip()


def safe_path(root, relative):
    root = root.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError("资料路径超出本 Skill 目录。")
    return target


def load_book(root=ROOT):
    index = (root / "references/section-index.json").read_bytes()
    expected_index = (root / "references/section-index.sha256").read_text(encoding="ascii").strip()
    if sha256(index).hexdigest() != expected_index:
        raise ValueError("资料索引校验失败，停止引用其中的标题、范围和片段。")
    manifest = json.loads(index)
    if manifest.get("schema") != 1:
        raise ValueError("资料索引版本不支持。")
    raw = safe_path(root, manifest["source"]).read_bytes()
    if sha256(raw).hexdigest() != manifest["source_sha256"]:
        raise ValueError("书稿校验失败，停止按此版本引用。")
    return manifest, raw.decode("utf-8")


def read_part(root, part):
    raw = safe_path(root, part["path"]).read_bytes()
    if sha256(raw).hexdigest() != part["sha256"]:
        raise ValueError(f"原文片段校验失败：{part['path']}")
    return raw.decode("utf-8")
