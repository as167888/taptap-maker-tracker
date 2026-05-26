import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "taptap_games.db")
TXT_PATH = os.path.join(BASE_DIR, "链接.txt")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            published_date TEXT,
            downloads TEXT,
            followers TEXT,
            rating TEXT,
            rating_count TEXT,
            detail_fetched INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detail_updated_at TIMESTAMP
        )
    """)

    # 兼容旧表：补充可能缺失的列
    existing = {row[1] for row in cur.execute("PRAGMA table_info(games)")}
    new_cols = [
        ("published_date", "TEXT"),
        ("downloads", "TEXT"),
        ("followers", "TEXT"),
        ("rating", "TEXT"),
        ("rating_count", "TEXT"),
        ("detail_fetched", "INTEGER DEFAULT 0"),
        ("detail_updated_at", "TIMESTAMP"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing:
            cur.execute(f"ALTER TABLE games ADD COLUMN {col_name} {col_type}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS crawl_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT,
            url TEXT,
            published_date TEXT,
            downloads TEXT,
            followers TEXT,
            rating TEXT,
            rating_count TEXT,
            crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn


def import_from_txt(conn):
    cur = conn.cursor()
    count = 0
    skipped = 0

    with open(TXT_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        url, name = parts[0], parts[1]
        try:
            cur.execute(
                "INSERT OR IGNORE INTO games (name, url) VALUES (?, ?)",
                (name, url),
            )
            if cur.rowcount > 0:
                count += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  跳过: {name} | 原因: {e}")
            skipped += 1

    conn.commit()
    print(f"导入完成: 新增 {count} 条, 跳过(重复) {skipped} 条")


def sync_from_xlsx(xlsx_path):
    """从爬虫输出的 xlsx 中读取链接，将新游戏插入数据库。返回新增数量。"""
    import pandas as pd

    conn = get_conn()
    cur = conn.cursor()

    df = pd.read_excel(xlsx_path)
    if "详情页链接" not in df.columns:
        print("错误: xlsx 中未找到'详情页链接'列")
        conn.close()
        return 0

    count = 0
    for _, row in df.iterrows():
        name = row.get("游戏名称", "")
        url = row.get("详情页链接", "")
        if not url:
            continue
        cur.execute(
            "INSERT OR IGNORE INTO games (name, url) VALUES (?, ?)",
            (name, url),
        )
        if cur.rowcount > 0:
            count += 1

    conn.commit()
    conn.close()
    print(f"DB 同步完成: 新增 {count} 条游戏记录")
    return count


def reset_all_pending():
    """将所有游戏的 detail_fetched 重置为 0，实现全量重新爬取"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE games SET detail_fetched = 0")
    conn.commit()
    conn.close()
    print(f"已重置 {cur.rowcount} 条游戏为待抓取状态")


def get_pending_games():
    """返回所有尚未爬取详情的游戏列表 (detail_fetched = 0)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, url FROM games WHERE detail_fetched = 0 ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_game_detail(game_id, data):
    """更新一条游戏的详情数据（成功抓取）"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """UPDATE games SET
            name = ?, published_date = ?, downloads = ?,
            followers = ?, rating = ?, rating_count = ?,
            detail_fetched = 1, detail_updated_at = CURRENT_TIMESTAMP
        WHERE id = ?""",
        (
            data.get("游戏名称", ""),
            data.get("发布日期", ""),
            data.get("下载量", ""),
            data.get("关注量", ""),
            data.get("评分", ""),
            data.get("评价数量", ""),
            game_id,
        ),
    )
    conn.commit()
    conn.close()


def mark_game_skipped(game_id):
    """标记游戏为跳过（404 / 解析失败），不再重试"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE games SET detail_fetched = -1, detail_updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (game_id,),
    )
    conn.commit()
    conn.close()


def save_crawl_record(data):
    """保存一条爬取记录到 crawl_history 表，带时间戳"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO crawl_history
           (game_name, url, published_date, downloads, followers, rating, rating_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("游戏名称", ""),
            data.get("请求链接", ""),
            data.get("发布日期", ""),
            data.get("下载量", ""),
            data.get("关注量", ""),
            data.get("评分", ""),
            data.get("评价数量", ""),
        ),
    )
    conn.commit()
    conn.close()


def show_summary(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM games")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM games WHERE detail_fetched = 1")
    fetched = cur.fetchone()[0]
    print(f"数据库共 {total} 条, 已抓详情 {fetched} 条, 待抓 {total - fetched} 条")


def main():
    print("初始化数据库...")
    conn = init_db()

    if os.path.exists(TXT_PATH):
        print("从 链接.txt 导入数据...")
        import_from_txt(conn)
    else:
        print(f"未找到 {TXT_PATH}，跳过导入")

    show_summary(conn)
    conn.close()


if __name__ == "__main__":
    main()
