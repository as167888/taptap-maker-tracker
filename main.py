import sys
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, "1.爬取带TapTap制造tag的游戏"))
sys.path.insert(0, os.path.join(BASE_DIR, "2.爬取TapTap制造的游戏详细信息"))
sys.path.insert(0, os.path.join(BASE_DIR, "3.生成网站发布页面"))

from taptap_spider import scrape_taptap
from taptap_mk_detail import crawl_taptap_games
from generate_html import excel_to_html
from init_db import init_db, sync_from_xlsx, reset_all_pending
from db_query import query_stats, query_detailed
from import_links import import_links

GAME_LIST_FILE = os.path.join(BASE_DIR, "taptap_game_list.xlsx")
GAME_DETAIL_FILE = os.path.join(BASE_DIR, "taptap_game_detail.xlsx")
RESULT_HTML_FILE = os.path.join(BASE_DIR, "taptap_maker_result.html")
EXPORT_DIR = os.path.join(BASE_DIR, "export")


def main():
    print("=" * 60)
    print("  TapTap 制造游戏数据爬取 — 全流程启动")
    print("=" * 60)

    # 初始化数据库（含旧表兼容迁移）
    print("\n【初始化】检查数据库...")
    init_db()
    query_stats()

    # 阶段 1：爬取游戏链接
    print("\n【阶段 1/4】爬取带 TapTap制造 标签的游戏链接...")
    scrape_taptap(GAME_LIST_FILE)

    if not os.path.exists(GAME_LIST_FILE):
        print(f"错误：阶段 1 未生成预期文件 {GAME_LIST_FILE}，流程终止。")
        return

    # 阶段 2：同步链接到数据库
    print("\n【阶段 2/4】同步新链接到数据库...")
    sync_from_xlsx(GAME_LIST_FILE)

    # 阶段 3：全量重新爬取详情
    print("\n【阶段 3/4】爬取所有游戏的详细信息...")
    reset_all_pending()
    crawl_taptap_games(GAME_DETAIL_FILE)

    if not os.path.exists(GAME_DETAIL_FILE):
        print("警告：阶段 3 未生成详情 Excel，可能无新游戏需要爬取。")
        # 尝试用已有数据生成 HTML
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
            df.to_excel(GAME_DETAIL_FILE, index=False)
            print(f"已从数据库生成 {len(df)} 条记录到 {GAME_DETAIL_FILE}")
        else:
            print("数据库中无已抓取详情的数据，跳过 HTML 生成。")
            return

    # 阶段 4：生成 HTML
    print("\n【阶段 4/4】生成可视化 HTML 页面...")
    excel_to_html(GAME_DETAIL_FILE, RESULT_HTML_FILE)

    # 导出备份
    if os.path.exists(RESULT_HTML_FILE):
        os.makedirs(EXPORT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        export_detail = os.path.join(EXPORT_DIR, f"{ts}_taptap_game_detail.xlsx")
        if os.path.exists(GAME_DETAIL_FILE):
            shutil.copy2(GAME_DETAIL_FILE, export_detail)
            print(f"\n📁 游戏详情已导出至：{export_detail}")

        export_html = os.path.join(EXPORT_DIR, f"{ts}_taptap_maker_result.html")
        shutil.copy2(RESULT_HTML_FILE, export_html)
        print(f"📁 结果页面已导出至：{export_html}")

    # 最终数据库统计
    query_stats()

    print("\n" + "=" * 60)
    print("  全流程完成！")
    print(f"  游戏列表：{GAME_LIST_FILE}")
    print(f"  游戏详情：{GAME_DETAIL_FILE}")
    print(f"  结果页面：{RESULT_HTML_FILE}")
    print(f"  导出目录：{EXPORT_DIR}")
    print("=" * 60)


def show_menu():
    print("\n" + "=" * 40)
    print("  TapTap 制造游戏数据 — 主菜单")
    print("=" * 40)
    print("  1. 启动全流程（爬取链接 → 详情 → HTML）")
    print("  2. 查看数据库详细数据")
    print("  3. 导入链接文件到数据库")
    print("  0. 退出")
    print("=" * 40)

    while True:
        choice = input("请输入选项 [0-3]: ").strip()
        if choice in ("0", "1", "2", "3"):
            return choice
        print("无效选项，请重新输入")


def run_import():
    file_path = input("请输入链接文件路径 (txt/csv/xlsx): ").strip()
    if file_path:
        init_db()
        import_links(file_path)
        query_stats()


if __name__ == "__main__":
    init_db()
    while True:
        choice = show_menu()
        if choice == "0":
            print("退出。")
            break
        elif choice == "1":
            main()
        elif choice == "2":
            query_detailed()
        elif choice == "3":
            run_import()
