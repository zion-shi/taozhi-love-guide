"""Read a small, verified packet from the locally bundled v1.2 guide."""

import argparse
from pathlib import Path
import re
import sys

from guide_data import LINK, ROOT, load_book, readable, read_part


TASKS = {
    "self": ("自我定位.md", "7.2"),
    "plan": ("择偶规划.md", "3.4"),
    "advance": ("关系推进.md", "A.3"),
    "conflict": ("解决冲突.md", "8.4"),
    "marriage": ("适婚协商.md", "E.2"),
    "home": ("家庭分工财务.md", "G.1"),
    "risk": ("风险与退出.md", "M.1"),
}


def plain(text):
    return LINK.sub(lambda match: match.group(2), readable(text, ""))


def full_section(manifest, source, unit):
    entry = manifest["sections"][unit]
    body = plain(source[entry["start"]:entry["end"]])
    return (f"《人间爱情指南》v1.2 · {unit} {entry['title']}\n"
            f"已读范围：本小节全文。来源 {manifest['source']}#{entry['anchor']}\n\n{body}")


def continuation(unit, part):
    return f"python3 scripts/read_guide.py --section {unit} --part {part}"


def read_packet(root=ROOT, task=None, sections=None, part=None, max_chars=3600):
    if not 600 <= max_chars <= 12000:
        raise ValueError("读取预算应在 600—12000 字符之间。")
    manifest, source = load_book(root)
    selected = list(dict.fromkeys(sections or ([TASKS[task][1]] if task else [])))
    if not selected:
        raise ValueError("请指定 --task 或 --section，也可用 --search 查找。")
    if len(selected) > 4:
        raise ValueError("一次至多选四个小节，请分批读取。")
    for unit in selected:
        if unit not in manifest["sections"]:
            raise ValueError(f"不存在小节 {unit}，请核对编号或用 --search。")
    if part is not None:
        if len(selected) != 1 or not 1 <= part <= len(manifest["sections"][selected[0]]["parts"]):
            raise ValueError("--part 需要一个有效小节和该节内的片段序号。")

    pieces = []
    if task:
        instruction = (root / "references" / TASKS[task][0]).read_text(encoding="utf-8").strip()
        if len(instruction) + 400 > max_chars:
            raise ValueError("本预算不足以容纳任务说明和原文，请增大 --max-chars 或仅指定 --section。")
        pieces.append("任务说明（方法提炼）\n\n" + instruction)
    footer = []
    for index, unit in enumerate(selected):
        entry = manifest["sections"][unit]
        content = full_section(manifest, source, unit)
        used = len("\n\n".join(pieces))
        if part is None and used + len(content) + 320 <= max_chars:
            pieces.append(content)
            continue

        first = part or 1
        number = first
        while number <= len(entry["parts"]):
            record = entry["parts"][number - 1]
            text = read_part(root, record)
            display = f"片段文件 {record['path']}\n\n{plain(text)}"
            used = len("\n\n".join(pieces))
            if used + len(display) + 320 > max_chars:
                break
            pieces.append(display)
            number += 1
        if number == first:
            required = len(plain(read_part(root, entry["parts"][first - 1]))) + 450
            footer.append(f"{unit} 本批未载入原文。读取一个完整片段至少预留约 {required} 字符。")
        else:
            footer.append(f"{unit} 本批读取第 {first}—{number-1}/{len(entry['parts'])} 片。")
        if number <= len(entry["parts"]):
            footer.append(f"后续尚未读取，必要时继续：{continuation(unit, number)}")
        if first > 1:
            footer.append(f"本批不含起始前提；若前文已不在上下文，先读 {unit} 第 1 片。")
        remaining = selected[index + 1:]
        if remaining:
            footer.append("尚未读到的小节：" + "、".join(remaining) + "。请另用 --section 指定。")
        break
    result = "\n\n".join(pieces + footer)
    if len(result) > max_chars:
        raise ValueError("完整片段超出本批预算，请减少指定内容或增加 --max-chars。")
    return result


def search(root, query, limit=5):
    terms = [term for term in re.split(r"\s+", query.strip()) if term]
    if not terms or len(query) > 120:
        raise ValueError("请给出 1—120 字符的关键词，可用空格分开。")
    manifest, source = load_book(root)
    ranked = []
    for unit, entry in manifest["sections"].items():
        body = source[entry["start"]:entry["end"]]
        score = sum(body.count(term) + 5 * entry["title"].count(term) for term in terms)
        if score:
            ranked.append((score, unit, entry))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    lines = ["检索仅定位出处。打开原文并核对适用条件后再分析。"]
    for _, unit, entry in ranked[:limit]:
        matches = []
        for ordinal, passage in enumerate(entry["parts"], 1):
            body = "\n".join(source[span["start"]:span["end"]] for span in passage["ranges"])
            score = sum(body.count(term) for term in terms)
            if score:
                matches.append((score, ordinal, passage))
        matches.sort(key=lambda match: (-match[0], match[1]))
        locators = matches[:2] or [(0, 1, entry["parts"][0])]
        lines.append(f"{unit} {entry['title']}")
        for _, ordinal, passage in locators:
            lines.append(f"  命中片段 {ordinal}/{len(entry['parts'])}：{passage['path']}\n"
                         f"  {continuation(unit, ordinal)}")
    if ranked:
        lines.append("中间片段不一定包含案例起点；依指针补读其前提和限定。")
    if not ranked:
        lines.append("没有找到该关键词。可换具体行为或按任务说明中的小节号读取。")
    return "\n\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=TASKS)
    parser.add_argument("--section", nargs="+")
    parser.add_argument("--part", type=int)
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--search")
    args = parser.parse_args()
    if args.search is not None and (args.task or args.section or args.part is not None):
        parser.error("--search 与读取选项分别使用。")
    try:
        result = search(ROOT, args.search) if args.search is not None else read_packet(
            ROOT, args.task, args.section, args.part, args.max_chars)
    except (OSError, ValueError, KeyError) as error:
        print(f"未读取：{error}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
