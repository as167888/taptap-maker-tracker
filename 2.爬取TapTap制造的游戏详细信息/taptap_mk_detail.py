import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time
import os
import sys
from datetime import datetime
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from init_db import get_pending_games, update_game_detail, mark_game_skipped, reset_all_pending, save_crawl_record


def crawl_taptap_games(output_file=None):
    print("从数据库读取待爬取的游戏列表...")
    pending = get_pending_games()

    if not pending:
        print("没有待爬取详情的游戏，所有游戏已是最新。")
        return

    print(f"共 {len(pending)} 款游戏待爬取详情。\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    results = []

    for index, game in enumerate(pending, start=1):
        url = game["url"].strip()
        # 去掉已有 query string，统一拼接 ?os=android
        if "?" in url:
            url = url.split("?")[0]
        target_url = f"{url}?os=android"

        print(f"\n[{index}/{len(pending)}] 正在爬取: {game['name']}...")

        game_data = {
            "请求链接": target_url,
            "游戏名称": "获取失败",
            "发布日期": "获取失败",
            "下载量": "获取失败",
            "关注量": "获取失败",
            "评分": "获取失败",
            "评价数量": "获取失败",
        }

        try:
            response = requests.get(target_url, headers=headers, timeout=15)

            if response.status_code == 404:
                print(f"  -> 游戏已下线 (404)，标记跳过")
                mark_game_skipped(game["id"])
                save_crawl_record(game_data)
                results.append(game_data)
                continue

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # JSON-LD 解析
            json_scripts = soup.find_all("script", type="application/ld+json")
            parsed_success = False
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "VideoGame":
                        game_data["游戏名称"] = data.get("name", "未找到")

                        raw_date = data.get("datePublished", "未找到")
                        if raw_date and raw_date != "未找到":
                            game_data["发布日期"] = str(raw_date).split("T")[0].split(" ")[0]
                        else:
                            game_data["发布日期"] = "未找到"

                        interaction = data.get("interactionStatistic", {})
                        game_data["下载量"] = interaction.get("userInteractionCount", "未找到")

                        aggregate = data.get("aggregateRating", {})
                        game_data["评分"] = aggregate.get("ratingValue", "未找到")
                        game_data["评价数量"] = aggregate.get("ratingCount", "未找到")

                        parsed_success = True
                        break
                except json.JSONDecodeError:
                    continue

            # Nuxt 数据中的关注量
            try:
                nuxt_script = soup.find("script", id="__NUXT_DATA__")
                if nuxt_script:
                    nuxt_data = json.loads(nuxt_script.string)
                    if isinstance(nuxt_data, list):
                        for item in nuxt_data:
                            if isinstance(item, dict) and "fans_count" in item:
                                fans_count_idx = item["fans_count"]
                                if isinstance(fans_count_idx, int) and fans_count_idx < len(nuxt_data):
                                    game_data["关注量"] = nuxt_data[fans_count_idx]
                                break
            except Exception as e:
                print(f"  -> 解析关注量异常: {e}")

            if parsed_success:
                print("  -> 成功提取数据：")
                for key, value in game_data.items():
                    print(f"     - {key}: {value}")
                update_game_detail(game["id"], game_data)
            else:
                print("  -> 提取失败：未找到匹配的 JSON 数据结构，标记跳过")
                mark_game_skipped(game["id"])

        except requests.exceptions.RequestException as e:
            print(f"  -> 请求失败: {e}，标记跳过")
            mark_game_skipped(game["id"])

        # 每款游戏的爬取结果都保存到 crawl_history，带当前时间戳
        save_crawl_record(game_data)

        results.append(game_data)

        time.sleep(random.uniform(1, 3))

    # 导出 xlsx
    print("\n正在保存爬取结果到 Excel...")
    if output_file:
        output_filename = output_file
    else:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{current_time}_taptap_spider_result.xlsx"

    try:
        output_df = pd.DataFrame(results)
        output_df.to_excel(output_filename, index=False)
        print(f"Excel 已保存至: {output_filename}")
    except Exception as e:
        print(f"保存 Excel 失败: {e}")

    # 汇总
    success_count = sum(1 for r in results if r["游戏名称"] != "获取失败")
    print(f"\n本次爬取 {len(results)} 款, 成功 {success_count} 款, 失败 {len(results) - success_count} 款")


if __name__ == "__main__":
    reset_all_pending()
    _export = os.path.join(BASE_DIR, "export")
    os.makedirs(_export, exist_ok=True)
    crawl_taptap_games(os.path.join(_export, "taptap_game_detail.xlsx"))
