import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from init_db import get_conn

PAGE_SIZE = 20


def query_stats():
    """概览统计"""
    conn = get_conn()
    cur = conn.cursor()

    print("=" * 50)
    print("  TapTap 游戏数据库统计")
    print("=" * 50)

    cur.execute("SELECT COUNT(*) FROM games")
    total = cur.fetchone()[0]
    print(f"  游戏总数:     {total}")

    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = 1")
    fetched = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = -1")
    skipped = cur.fetchone()[0]
    print(f"  已抓取详情:   {fetched}")
    print(f"  待抓取:       {total - fetched - skipped}")
    print(f"  已跳过:       {skipped}")

    cur.execute("SELECT name, url, created_at FROM games ORDER BY created_at DESC LIMIT 5")
    recent = cur.fetchall()
    if recent:
        print(f"\n--- 最近新增 ---")
        for r in recent:
            print(f"  {r['name']}  ({r['created_at']})")

    if fetched > 0:
        cur.execute(
            """SELECT name, downloads, followers, rating, rating_count
               FROM games WHERE detail_fetched = 1
               ORDER BY CAST(downloads AS INTEGER) DESC LIMIT 5"""
        )
        top_down = cur.fetchall()
        if top_down:
            print(f"\n--- 下载量 Top 5 ---")
            for r in top_down:
                print(f"  {r['name']}: 下载 {r['downloads']}, 关注 {r['followers']}, 评分 {r['rating']}")

    conn.close()
    print("\n" + "=" * 50)


def query_detailed():
    """详细数据查看，支持分页和筛选"""
    conn = get_conn()
    cur = conn.cursor()

    # 获取各状态数量
    cur.execute("SELECT COUNT(*) FROM games")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = 1")
    fetched = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = 0")
    pending_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = -1")
    skipped = cur.fetchone()[0]

    filter_mode = "all"  # all / fetched / pending / skipped
    page = 0
    sort_by = "id"
    sort_order = "ASC"

    while True:
        # 构建查询
        where_clause = {
            "all": "1=1",
            "fetched": "detail_fetched = 1",
            "pending": "detail_fetched = 0",
            "skipped": "detail_fetched = -1",
        }.get(filter_mode, "1=1")

        allowed_sort = {"id", "name", "downloads", "followers", "rating", "rating_count", "published_date", "created_at"}
        if sort_by not in allowed_sort:
            sort_by = "id"

        cur.execute(f"SELECT COUNT(*) FROM games WHERE {where_clause}")
        filtered_total = cur.fetchone()[0]
        total_pages = max(1, (filtered_total + PAGE_SIZE - 1) // PAGE_SIZE)

        cur.execute(
            f"""SELECT id, name, url, published_date, downloads, followers,
                       rating, rating_count, detail_fetched, created_at
                FROM games WHERE {where_clause}
                ORDER BY {sort_by} {sort_order}
                LIMIT {PAGE_SIZE} OFFSET {page * PAGE_SIZE}"""
        )
        rows = cur.fetchall()

        status_labels = {1: "已抓", 0: "待抓", -1: "跳过"}

        print("\n" + "=" * 80)
        print(f"  详细数据 | 筛选: {filter_mode} | 排序: {sort_by} {sort_order}")
        print(f"  第 {page + 1}/{total_pages} 页 (共 {filtered_total} 条)")
        print(f"  全部 {total} | 已抓 {fetched} | 待抓 {pending_count} | 跳过 {skipped}")
        print("=" * 80)

        if not rows:
            print("  (无数据)")
        else:
            header = f"  {'ID':<5} {'名称':<20} {'发布日期':<12} {'下载':<8} {'关注':<8} {'评分':<5} {'评价数':<7} {'状态'}"
            print(header)
            print("  " + "-" * 76)
            for r in rows:
                status = status_labels.get(r["detail_fetched"], "?")
                name = r["name"][:18] if r["name"] else "-"
                date = (r["published_date"] or "-")[:10]
                dl = str(r["downloads"] or "-")[:7]
                fw = str(r["followers"] or "-")[:7]
                rt = str(r["rating"] or "-")[:4]
                rc = str(r["rating_count"] or "-")[:6]
                print(f"  {r['id']:<5} {name:<20} {date:<12} {dl:<8} {fw:<8} {rt:<5} {rc:<7} {status}")

        print("\n  [N]下一页  [P]上一页  [A]全部  [F]已抓  [W]待抓  [S]跳过")
        print("  [排序: 1-ID 2-名称 3-下载量 4-关注 5-评分 6-发布日期]")
        print("  [0]返回主菜单")

        cmd = input("> ").strip().lower()
        if cmd == "0":
            break
        elif cmd == "n":
            if page < total_pages - 1:
                page += 1
        elif cmd == "p":
            if page > 0:
                page -= 1
        elif cmd == "a":
            filter_mode = "all"
            page = 0
        elif cmd == "f":
            filter_mode = "fetched"
            page = 0
        elif cmd == "w":
            filter_mode = "pending"
            page = 0
        elif cmd == "s":
            filter_mode = "skipped"
            page = 0
        elif cmd == "1":
            sort_by = "id"
        elif cmd == "2":
            sort_by = "name"
        elif cmd == "3":
            sort_by = "downloads"
            sort_order = "DESC"
        elif cmd == "4":
            sort_by = "followers"
            sort_order = "DESC"
        elif cmd == "5":
            sort_by = "rating"
            sort_order = "DESC"
        elif cmd == "6":
            sort_by = "published_date"
            sort_order = "DESC"

    conn.close()


if __name__ == "__main__":
    query_detailed()


def query_history():
    """查看爬取历史记录"""
    conn = get_conn()
    cur = conn.cursor()

    # 统计数据
    cur.execute("SELECT COUNT(*) FROM crawl_history")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT crawl_time) FROM crawl_history")
    run_count = cur.fetchone()[0]
    cur.execute("SELECT MIN(crawl_time), MAX(crawl_time) FROM crawl_history")
    time_range = cur.fetchone()

    if total == 0:
        print("\n暂无爬取历史记录。")
        conn.close()
        return

    page = 0

    while True:
        cur.execute(
            """SELECT id, game_name, downloads, followers, rating, rating_count, crawl_time
               FROM crawl_history
               ORDER BY crawl_time DESC, id DESC
               LIMIT ? OFFSET ?""",
            (PAGE_SIZE, page * PAGE_SIZE),
        )
        rows = cur.fetchall()
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

        print("\n" + "=" * 90)
        print(f"  爬取历史记录 | 共 {total} 条记录, {run_count} 次爬取")
        if time_range[0]:
            print(f"  时间范围: {time_range[0]} ~ {time_range[1]}")
        print(f"  第 {page + 1}/{total_pages} 页")
        print("=" * 90)

        if not rows:
            print("  (无数据)")
        else:
            header = f"  {'ID':<5} {'游戏名称':<22} {'下载':<8} {'关注':<8} {'评分':<5} {'评价数':<7} {'爬取时间'}"
            print(header)
            print("  " + "-" * 80)
            for r in rows:
                name = r["game_name"][:20] if r["game_name"] else "-"
                dl = str(r["downloads"] or "-")[:7]
                fw = str(r["followers"] or "-")[:7]
                rt = str(r["rating"] or "-")[:4]
                rc = str(r["rating_count"] or "-")[:6]
                print(f"  {r['id']:<5} {name:<22} {dl:<8} {fw:<8} {rt:<5} {rc:<7} {r['crawl_time']}")

        print("\n  [N]下一页  [P]上一页  [0]返回")

        cmd = input("> ").strip().lower()
        if cmd == "0":
            break
        elif cmd == "n":
            if page < total_pages - 1:
                page += 1
        elif cmd == "p":
            if page > 0:
                page -= 1

    conn.close()


if __name__ == "__main__":
    query_detailed()
