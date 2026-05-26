import sys
import os
import shutil
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, "1.爬取带TapTap制造tag的游戏"))
sys.path.insert(0, os.path.join(BASE_DIR, "2.爬取TapTap制造的游戏详细信息"))
sys.path.insert(0, os.path.join(BASE_DIR, "3.生成网站发布页面"))

from taptap_spider import scrape_taptap
from taptap_mk_detail import crawl_taptap_games
from generate_html import excel_to_html
from init_db import init_db, sync_from_xlsx, reset_all_pending
from db_query import query_stats, query_detailed, query_history
from import_links import import_links

EXPORT_DIR = os.path.join(BASE_DIR, "export")
DOCS_DIR = os.path.join(BASE_DIR, "docs")


def run_full_pipeline():
    """全流程：爬取链接 → 同步数据库 → 爬取详情 → 生成 HTML"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("  TapTap 制造游戏数据爬取 — 全流程启动")
    print("=" * 60)

    os.makedirs(EXPORT_DIR, exist_ok=True)

    print("\n【初始化】检查数据库...")
    init_db()
    query_stats()

    # 阶段 1：爬取游戏链接
    game_list_file = os.path.join(EXPORT_DIR, f"{ts}_taptap_game_list.xlsx")
    print("\n【阶段 1/4】爬取带 TapTap制造 标签的游戏链接...")
    scrape_taptap(game_list_file)

    if not os.path.exists(game_list_file):
        print(f"错误：阶段 1 未生成预期文件 {game_list_file}，流程终止。")
        return

    # 阶段 2：同步链接到数据库
    print("\n【阶段 2/4】同步新链接到数据库...")
    sync_from_xlsx(game_list_file)

    # 阶段 3：全量重新爬取详情
    game_detail_file = os.path.join(EXPORT_DIR, f"{ts}_taptap_game_detail.xlsx")
    print("\n【阶段 3/4】爬取所有游戏的详细信息...")
    reset_all_pending()
    crawl_taptap_games(game_detail_file)

    if not os.path.exists(game_detail_file):
        print("警告：阶段 3 未生成详情 Excel，可能无新游戏需要爬取。")
        print("尝试从数据库已有记录生成展示页面...")
        import pandas as pd
        from init_db import get_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, url, published_date, downloads, followers, rating, rating_count FROM games WHERE detail_fetched = 1")
        rows = cur.fetchall()
        conn.close()
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            df.rename(columns={
                "url": "请求链接", "name": "游戏名称",
                "published_date": "发布日期", "downloads": "下载量",
                "followers": "关注量", "rating": "评分",
                "rating_count": "评价数量",
            }, inplace=True)
            df.to_excel(game_detail_file, index=False)
            print(f"已从数据库生成 {len(df)} 条记录到 {game_detail_file}")
        else:
            print("数据库中无已抓取详情的数据，跳过 HTML 生成。")
            return

    # 阶段 4：生成 HTML
    result_html_file = os.path.join(EXPORT_DIR, f"{ts}_taptap_maker_result.html")
    print("\n【阶段 4/4】生成可视化 HTML 页面...")
    excel_to_html(game_detail_file, result_html_file)

    # 同步到 docs/ 用于 GitHub Pages 发布
    if os.path.exists(result_html_file):
        os.makedirs(DOCS_DIR, exist_ok=True)
        docs_index = os.path.join(DOCS_DIR, "index.html")
        shutil.copy2(result_html_file, docs_index)
        print(f"\nGitHub Pages 页面已更新：{docs_index}")

    query_stats()

    print("\n" + "=" * 60)
    print("  全流程完成！")
    print(f"  游戏列表：{game_list_file}")
    print(f"  游戏详情：{game_detail_file}")
    print(f"  结果页面：{result_html_file}")
    print(f"  导出目录：{EXPORT_DIR}")
    print("=" * 60)


def show_menu():
    print("\n" + "=" * 40)
    print("  TapTap 制造游戏数据 — 主菜单")
    print("=" * 40)
    print("  1. 启动全流程（爬取链接 → 详情 → HTML）")
    print("  2. 查看数据库详细数据")
    print("  3. 导入链接文件到数据库")
    print("  4. 查看爬取历史记录")
    print("  0. 退出")
    print("=" * 40)

    while True:
        choice = input("请输入选项 [0-4]: ").strip()
        if choice in ("0", "1", "2", "3", "4"):
            return choice
        print("无效选项，请重新输入")


def run_import():
    file_path = input("请输入链接文件路径 (txt/csv/xlsx): ").strip()
    if file_path:
        init_db()
        import_links(file_path)
        query_stats()


def main():
    parser = argparse.ArgumentParser(description="TapTap Maker 游戏数据追踪系统")
    parser.add_argument("--full", action="store_true", help="非交互模式：直接运行全流程")
    args = parser.parse_args()

    init_db()

    if args.full:
        run_full_pipeline()
        return

    # 交互式菜单
    while True:
        choice = show_menu()
        if choice == "0":
            print("退出。")
            break
        elif choice == "1":
            run_full_pipeline()
        elif choice == "2":
            query_detailed()
        elif choice == "3":
            run_import()
        elif choice == "4":
            query_history()


if __name__ == "__main__":
    main()
