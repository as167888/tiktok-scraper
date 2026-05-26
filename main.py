"""
TikTok 数据抓取工具 — 基于 Apify + TikHub

用法:
    python main.py                       # 直接抓取 config.py 中预设的账号和话题，保存到 CSV
    python main.py account <username>      # 查账号粉丝/点赞
    python main.py hashtag <topic>         # 查话题播放量
    python main.py both <username> <topic> # 同时查
    python main.py bulk accounts user1,user2,user3  # 批量查账号
    python main.py bulk hashtags topic1,topic2      # 批量查话题
    python main.py track                  # 抓取追踪账号列表，保存到 CSV
    python main.py track_hashtags         # 抓取追踪话题列表，保存到 CSV
"""

import argparse
import csv
import io
import os
import sys
from datetime import datetime

# Fix Windows console encoding for Chinese characters
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tiktok_scraper import TikTokScraper
from config import APIFY_API_TOKEN, PROXY_URL, TRACKING_ACCOUNTS, TRACKING_HASHTAGS, CSV_FILE, HASHTAG_CSV_FILE


def fmt(n: int) -> str:
    return f"{n:,}"


# ══════════════════════════════════════════════════════════════════
#  CLI 输出函数
# ══════════════════════════════════════════════════════════════════

def print_account(stats: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  账号: @{stats['username']}")
    print(f"{'='*50}")
    if "error" in stats:
        print(f"  [错误] {stats['error']}")
        return
    print(f"  昵称:     {stats.get('nickname', '-')}")
    print(f"  粉丝数:   {stats['followers']:,}")
    print(f"  点赞数:   {stats['likes']:,}")
    print(f"  关注数:   {stats['following']:,}")
    print(f"  作品数:   {stats['video_count']:,}")
    print(f"  认证:     {'是' if stats.get('verified') else '否'}")
    print(f"  私密:     {'是' if stats.get('private') else '否'}")
    print(f"  简介:     {stats.get('bio', '-')}")
    print(f"{'='*50}\n")


def print_hashtag(stats: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  话题: #{stats['hashtag']}")
    print(f"{'='*50}")
    if "error" in stats:
        print(f"  [错误] {stats['error']}")
        return
    print(f"  播放量:   {stats['view_count']:,}")
    vc = stats.get('video_count')
    if vc is not None:
        print(f"  作品数:   {vc:,}")
    print(f"{'='*50}\n")


# ══════════════════════════════════════════════════════════════════
#  CSV 追踪
# ══════════════════════════════════════════════════════════════════

def do_track_accounts(proxy: str | None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"通过代理 {proxy}" if proxy else "直连"
    print(f"\n[{label}] 正在抓取 {len(TRACKING_ACCOUNTS)} 个追踪账号 ...\n")

    file_exists = os.path.exists(CSV_FILE)
    scraper = TikTokScraper(proxy=proxy)

    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "username", "followers", "likes", "video_count"])

        for username in TRACKING_ACCOUNTS:
            try:
                r = scraper.get_account_stats(username)
            except Exception as e:
                print(f"  @{username}: [错误] {e}")
                continue

            if "error" in r:
                print(f"  @{username}: [错误] {r['error']}")
                writer.writerow([now, username, "ERROR", "ERROR", "ERROR"])
                continue

            writer.writerow([now, username, r["followers"], r["likes"], r["video_count"]])
            print(f"  @{username: <20} 粉丝: {fmt(r['followers']): >12}  点赞: {fmt(r['likes']): >12}  作品: {r['video_count']}")

    print(f"\n已保存到 {CSV_FILE}")


def do_track_hashtags(proxy: str | None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"通过代理 {proxy}" if proxy else "直连"
    print(f"\n[{label}] 正在抓取 {len(TRACKING_HASHTAGS)} 个追踪话题 ...\n")

    file_exists = os.path.exists(HASHTAG_CSV_FILE)
    scraper = TikTokScraper(proxy=proxy)

    with open(HASHTAG_CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "hashtag", "view_count", "video_count"])

        for hashtag in TRACKING_HASHTAGS:
            try:
                r = scraper.get_hashtag_stats(hashtag)
            except Exception as e:
                print(f"  #{hashtag}: [错误] {e}")
                continue

            if "error" in r:
                print(f"  #{hashtag}: [错误] {r['error']}")
                writer.writerow([now, hashtag, "ERROR", "ERROR"])
                continue

            writer.writerow([now, hashtag, r["view_count"], r["video_count"]])
            print(f"  #{hashtag: <25} 播放: {fmt(r['view_count']): >15}  作品: {fmt(r['video_count'])}")

    print(f"\n已保存到 {HASHTAG_CSV_FILE}")


# ══════════════════════════════════════════════════════════════════
#  命令行模式
# ══════════════════════════════════════════════════════════════════

def run_cli():
    parser = argparse.ArgumentParser(description="TikTok 数据抓取工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("account", help="查询账号粉丝/点赞")
    p.add_argument("username", help="TikTok 用户名 (不带 @)")
    p.add_argument("--proxy", "-p", help="代理地址 (如 http://127.0.0.1:7993)")

    p = sub.add_parser("hashtag", help="查询话题播放量")
    p.add_argument("topic", help="话题名 (不带 #)")
    p.add_argument("--proxy", "-p", help="代理地址")

    both = sub.add_parser("both", help="同时查询账号和话题")
    both.add_argument("username", help="TikTok 用户名")
    both.add_argument("topic", help="话题名")
    both.add_argument("--proxy", "-p", help="代理地址")

    bulk = sub.add_parser("bulk", help="批量查询")
    bulk_sub = bulk.add_subparsers(dest="bulk_type", required=True)
    bulk_sub.add_parser("accounts", help="批量查账号").add_argument(
        "usernames", help="逗号分隔的用户名列表"
    )
    bulk_sub.add_parser("hashtags", help="批量查话题").add_argument(
        "topics", help="逗号分隔的话题列表"
    )
    bulk.add_argument("--proxy", "-p", help="代理地址")

    sub.add_parser("track", help="抓取追踪账号列表并保存到 CSV")
    sub.add_parser("track_hashtags", help="抓取追踪话题列表并保存到 CSV")

    args = parser.parse_args()
    proxy = getattr(args, "proxy", None) or PROXY_URL or None

    if args.command == "account":
        scraper = TikTokScraper(proxy=proxy)
        print_account(scraper.get_account_stats(args.username))

    elif args.command == "hashtag":
        scraper = TikTokScraper(proxy=proxy)
        print_hashtag(scraper.get_hashtag_stats(args.topic))

    elif args.command == "both":
        scraper = TikTokScraper(proxy=proxy)
        print_account(scraper.get_account_stats(args.username))
        print_hashtag(scraper.get_hashtag_stats(args.topic))

    elif args.command == "bulk":
        scraper = TikTokScraper(proxy=proxy)
        if args.bulk_type == "accounts":
            names = [n.strip() for n in args.usernames.split(",")]
            for r in scraper.get_multiple_accounts(names):
                print_account(r)
        elif args.bulk_type == "hashtags":
            tags = [t.strip() for t in args.topics.split(",")]
            for r in scraper.get_multiple_hashtags(tags):
                print_hashtag(r)

    elif args.command == "track":
        do_track_accounts(proxy)
    elif args.command == "track_hashtags":
        do_track_hashtags(proxy)


# ══════════════════════════════════════════════════════════════════
#  默认模式 — 自动抓取 config.py 中预设的账号和话题
# ══════════════════════════════════════════════════════════════════

def run_default():
    if not APIFY_API_TOKEN:
        print("[错误] 未设置 APIFY_API_TOKEN，请在 .env 中配置")
        print("获取: https://console.apify.com/account#/integrations")
        sys.exit(1)

    proxy = PROXY_URL or None

    print("═" * 50)
    print("  TikTok 数据抓取工具 — 自动模式")
    print("═" * 50)
    print(f"  代理: {proxy or '(直连)'}")
    print(f"  追踪账号: {', '.join(TRACKING_ACCOUNTS)}")
    print(f"  追踪话题: {', '.join(TRACKING_HASHTAGS)}")
    print("═" * 50)

    do_track_accounts(proxy)
    do_track_hashtags(proxy)

    print("\n全部抓取完成。")


# ══════════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) > 1:
        run_cli()
    else:
        run_default()


if __name__ == "__main__":
    main()
