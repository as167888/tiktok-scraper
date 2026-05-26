"""
Data analysis module — compares daily tracking data with historical records
and calls DeepSeek API for AI-powered commentary.
"""

import csv
import json
import os
from datetime import date, datetime, timedelta
from collections import defaultdict

import requests

from config import DEEPSEEK_API_KEY, CSV_FILE, HASHTAG_CSV_FILE


def _parse_ts(ts_str: str):
    """Parse mixed-format timestamp strings found in CSV files."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _load_csv(filepath: str) -> list[dict]:
    rows = []
    if not os.path.exists(filepath):
        return rows
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if _parse_ts(row.get("timestamp", "")):
                rows.append(row)
    return rows


# ── comparison helpers ──────────────────────────────────────────────

def _to_num(val) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _latest_by_entity(rows, entity_key: str, metric_keys: list[str]):
    """Return {entity_name: {ts, metrics}} for the most recent row per entity."""
    out = {}
    for r in rows:
        ts = _parse_ts(r["timestamp"])
        name = r[entity_key]
        if name not in out or ts > out[name]["ts"]:
            out[name] = {
                "ts": ts,
                "metrics": {k: _to_num(r.get(k, 0)) or 0 for k in metric_keys},
            }
    return out


def _previous_day(rows, entity_key: str, metric_keys: list[str], today: date):
    """Return {entity_name: {ts, metrics}} for the most recent entry strictly before `today`.

    This guarantees a genuine cross-day comparison even when multiple scrapes
    exist on the same day.
    """
    out = {}
    for r in rows:
        ts = _parse_ts(r["timestamp"])
        if ts is None or ts.date() >= today:
            continue
        name = r[entity_key]
        if name not in out or ts > out[name]["ts"]:
            out[name] = {
                "ts": ts,
                "metrics": {k: _to_num(r.get(k, 0)) or 0 for k in metric_keys},
            }
    return out


def _closest_before(rows, entity_key: str, metric_keys: list[str], cutoff: datetime):
    """Return {entity_name: {ts, metrics}} for the row closest to (<=) cutoff."""
    out = {}
    for r in rows:
        ts = _parse_ts(r["timestamp"])
        name = r[entity_key]
        if ts <= cutoff:
            if name not in out or ts > out[name]["ts"]:
                out[name] = {
                    "ts": ts,
                    "metrics": {k: _to_num(r.get(k, 0)) or 0 for k in metric_keys},
                }
    return out


def _change(cur: dict, prev: dict, metric_keys: list[str]) -> dict:
    out = {}
    for k in metric_keys:
        c = cur.get(k, 0)
        p = prev.get(k, 0)
        d = c - p
        pct = round(d / p * 100, 2) if p != 0 else 0
        out[k] = {"当前": c, "对比": p, "变化": d, "变化率%": pct}
    return out


# ── analysis engine ─────────────────────────────────────────────────

def run_analysis() -> str:
    """Compare latest vs historical data, call DeepSeek, return a formatted report."""
    accounts = _load_csv(CSV_FILE)
    hashtags = _load_csv(HASHTAG_CSV_FILE)

    now = datetime.now()
    a_metrics = ["followers", "likes", "video_count"]
    h_metrics = ["view_count", "video_count"]

    # --- account side ---
    today_a = _latest_by_entity(accounts, "username", a_metrics)
    yesterday_a = _previous_day(accounts, "username", a_metrics, now.date())
    three_day_a = _closest_before(accounts, "username", a_metrics, now - timedelta(days=3))
    week_a = _closest_before(accounts, "username", a_metrics, now - timedelta(days=7))
    month_a = _closest_before(accounts, "username", a_metrics, now - timedelta(days=30))

    # --- hashtag side ---
    today_h = _latest_by_entity(hashtags, "hashtag", h_metrics)
    yesterday_h = _previous_day(hashtags, "hashtag", h_metrics, now.date())
    three_day_h = _closest_before(hashtags, "hashtag", h_metrics, now - timedelta(days=3))
    week_h = _closest_before(hashtags, "hashtag", h_metrics, now - timedelta(days=7))
    month_h = _closest_before(hashtags, "hashtag", h_metrics, now - timedelta(days=30))

    # --- build prompt data ---
    account_entries = []
    for name, t in today_a.items():
        entry = {"账号": name, "今日数据": t["metrics"]}
        if name in yesterday_a:
            entry["日环比"] = _change(t["metrics"], yesterday_a[name]["metrics"], a_metrics)
        if name in three_day_a:
            entry["3日对比"] = _change(t["metrics"], three_day_a[name]["metrics"], a_metrics)
        if name in week_a:
            entry["周同比"] = _change(t["metrics"], week_a[name]["metrics"], a_metrics)
        if name in month_a:
            entry["月同比"] = _change(t["metrics"], month_a[name]["metrics"], a_metrics)
        account_entries.append(entry)

    hashtag_entries = []
    for name, t in today_h.items():
        entry = {"话题": name, "今日数据": t["metrics"]}
        if name in yesterday_h:
            entry["日环比"] = _change(t["metrics"], yesterday_h[name]["metrics"], h_metrics)
        if name in three_day_h:
            entry["3日对比"] = _change(t["metrics"], three_day_h[name]["metrics"], h_metrics)
        if name in week_h:
            entry["周同比"] = _change(t["metrics"], week_h[name]["metrics"], h_metrics)
        if name in month_h:
            entry["月同比"] = _change(t["metrics"], month_h[name]["metrics"], h_metrics)
        hashtag_entries.append(entry)

    # --- call DeepSeek ---
    prompt = _build_prompt(account_entries, hashtag_entries)
    ai_text = _call_deepseek(prompt)

    # --- format full report ---
    return _format_report(ai_text, account_entries, hashtag_entries)


# ── DeepSeek ────────────────────────────────────────────────────────

def _build_prompt(accounts: list[dict], hashtags: list[dict]) -> str:
    data_block = json.dumps(
        {"账号分析": accounts, "话题分析": hashtags},
        ensure_ascii=False,
        indent=2,
    )
    return f"""请根据以下 TikTok 数据，用中文生成一段数据分析点评（200-400字），语气轻松专业。

数据中每条记录包含"今日数据"（当前值）以及多个时间维度的对比：
- 日环比（与昨日对比的变化量/变化率）
- 3日对比（与3天前对比的变化量/变化率）
- 周同比（与7天前对比的变化量/变化率）
- 月同比（与30天前对比的变化量/变化率）

每个维度都标注了"变化"（增量/减量绝对值）和"变化率%"（百分比）。

要求：
1. 先概括今日各账号粉丝/点赞/作品数概况
2. 逐一分析日环比、3日对比、周同比、月同比中涨跌显著的账号，引用具体增量数值（如"+1200粉"）
3. 话题侧同样逐时间维度分析，引用播放量增量
4. 指出增长加速或减速的信号（对比不同时间窗口的变化率可判断趋势）
5. 若有明显异常数据请重点标注
6. 结尾给一句简短运营建议

数据如下：
{data_block}"""


def _call_deepseek(prompt: str) -> str:
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("your_"):
        return "[未配置 DEEPSEEK_API_KEY，请在 .env 中填入你的 DeepSeek API Key]"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个 TikTok 社交媒体数据分析助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[DeepSeek API 调用失败: {e}]"


# ── report formatter ────────────────────────────────────────────────

def _fmt(n) -> str:
    if not isinstance(n, (int, float)):
        return str(n)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.2f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.2f}万"
    return f"{n:,}"


def _format_report(ai_text: str, accounts: list[dict], hashtags: list[dict]) -> str:
    lines = [
        "=" * 50,
        "  AI 数据趋势分析",
        "=" * 50,
        "",
        ai_text.strip(),
        "",
        "-" * 50,
        "  今日数据摘要",
        "-" * 50,
    ]

    for a in accounts:
        lines.append(f"\n  @{a['账号']}:")
        for k, v in a["今日数据"].items():
            lines.append(f"    {k}: {_fmt(v)}")

    for h in hashtags:
        lines.append(f"\n  #{h['话题']}:")
        for k, v in h["今日数据"].items():
            lines.append(f"    {k}: {_fmt(v)}")

    return "\n".join(lines)
