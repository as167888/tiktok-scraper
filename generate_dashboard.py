"""
读取 tracking CSV 文件，将数据嵌入 dashboard.html。
用法: python generate_dashboard.py
"""
import csv
import re
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "tracking_data.csv")
HASHTAG_CSV_FILE = os.path.join(SCRIPT_DIR, "tracking_hashtags.csv")
TEMPLATE_FILE = os.path.join(SCRIPT_DIR, "dashboard.html")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "dashboard.html")


def parse_ts(ts_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue
    return None


def load_and_sort(filepath: str) -> list[dict]:
    rows = []
    if not os.path.exists(filepath):
        return rows
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ts = parse_ts(row.get("timestamp", ""))
            if ts:
                row["_ts"] = ts
                rows.append(row)
    rows.sort(key=lambda r: r["_ts"])
    return rows


def build_account_js(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        ts = r["_ts"].strftime("%Y-%m-%dT%H:%M:%S")
        line = (
            f"{{timestamp:\"{ts}\","
            f"username:\"{r['username']}\","
            f"followers:{r['followers']},"
            f"likes:{r['likes']},"
            f"video_count:{r['video_count']}"
            f"}},"
        )
        lines.append(line)
    return "\n".join(lines)


def build_hashtag_js(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        ts = r["_ts"].strftime("%Y-%m-%dT%H:%M:%S")
        line = (
            f"{{timestamp:\"{ts}\","
            f"hashtag:\"{r['hashtag']}\","
            f"view_count:{r['view_count']},"
            f"video_count:{r['video_count']}"
            f"}},"
        )
        lines.append(line)
    return "\n".join(lines)


def replace_between(template: str, begin_marker: str, end_marker: str,
                    replacement: str) -> str:
    pattern = re.escape(begin_marker) + r".*?" + re.escape(end_marker)
    new_content = begin_marker + "\n" + replacement + "\n" + end_marker
    return re.sub(pattern, new_content, template, flags=re.DOTALL)


def main():
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    accounts = load_and_sort(CSV_FILE)
    hashtags = load_and_sort(HASHTAG_CSV_FILE)

    acc_js = build_account_js(accounts)
    tag_js = build_hashtag_js(hashtags)

    result = replace_between(template, "// BEGIN_ACCOUNT_DATA",
                             "// END_ACCOUNT_DATA", acc_js)
    result = replace_between(result, "// BEGIN_HASHTAG_DATA",
                             "// END_HASHTAG_DATA", tag_js)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Generated {OUTPUT_FILE}")
    print(f"  Accounts: {len(accounts)} rows")
    print(f"  Hashtags: {len(hashtags)} rows")
    if accounts:
        latest = max(r["_ts"] for r in accounts)
        print(f"  Latest data: {latest.strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
