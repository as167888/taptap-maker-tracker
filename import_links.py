import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from init_db import get_conn


def import_links(file_path):
    """
    从 txt / csv / xlsx 文件中导入游戏链接到数据库。
    支持格式：
      - txt: 第一行为表头（请求链接\t游戏名称），后续每行 tab 分隔
      - csv: 列名为"请求链接/详情页链接/url"和"游戏名称/name"
      - xlsx: 同 csv
    """
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 - {file_path}")
        return 0

    ext = os.path.splitext(file_path)[1].lower()
    rows = []

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        header = lines[0].strip().split("\t")
        url_idx = name_idx = -1
        for i, h in enumerate(header):
            if h in ("请求链接", "详情页链接", "url", "链接"):
                url_idx = i
            elif h in ("游戏名称", "name", "名称"):
                name_idx = i
        if url_idx == -1 or name_idx == -1:
            print(f"错误：txt 表头未找到链接/名称列，当前: {header}")
            return 0
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) > max(url_idx, name_idx):
                rows.append((parts[name_idx], parts[url_idx]))

    elif ext in (".csv", ".xlsx"):
        import pandas as pd
        df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
        url_col = name_col = None
        for c in df.columns:
            if c in ("请求链接", "详情页链接", "url", "链接"):
                url_col = c
            elif c in ("游戏名称", "name", "名称"):
                name_col = c
        if url_col is None or name_col is None:
            print(f"错误：文件中未找到链接/名称列，当前列: {list(df.columns)}")
            return 0
        for _, row in df.iterrows():
            name = str(row[name_col]) if pd.notna(row[name_col]) else ""
            url = str(row[url_col]) if pd.notna(row[url_col]) else ""
            if url:
                rows.append((name, url))
    else:
        print(f"错误：不支持的文件格式 {ext}，仅支持 txt/csv/xlsx")
        return 0

    # 清理 URL（去掉 ?os=android 等参数）
    conn = get_conn()
    cur = conn.cursor()
    count = 0
    skipped = 0

    for name, url in rows:
        url = url.strip()
        if "?" in url:
            url = url.split("?")[0]
        if not url:
            continue
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
    conn.close()
    print(f"导入完成: 新增 {count} 条, 跳过(重复) {skipped} 条")
    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="手动导入游戏链接到数据库")
    parser.add_argument("file", help="txt/csv/xlsx 文件路径")
    args = parser.parse_args()
    import_links(args.file)
