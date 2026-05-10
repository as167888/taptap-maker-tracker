import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def scrape_taptap(output_file=None):
    # 基础 URL
    base_url = "https://www.taptap.cn/tag/TapTap%E5%88%B6%E9%80%A0"
    
    # 设置请求头，伪装成普通浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.taptap.cn/"
    }

    all_games = []
    total_pages = 50

    print("=" * 50)
    print(f"🚀 开始抓取，共计 {total_pages} 页...")
    print("=" * 50)

    for page in range(1, total_pages + 1):
        # 构造对应页码的链接
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}?page={page}"

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏳ 正在抓取第 {page}/{total_pages} 页...")

        try:
            # 发起 GET 请求
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            title_divs = soup.find_all('div', class_='app-title')

            if not title_divs:
                print(f"  ⚠️ 第 {page} 页没有解析到数据，可能是此页无数据或触发了验证。")
                continue

            # 用于临时存储当前页抓取到的游戏，方便打印输出
            current_page_games = []

            for title_div in title_divs:
                # 1. 提取链接
                parent_a = title_div.parent
                link = ""
                if parent_a and parent_a.name == 'a' and parent_a.get('href'):
                    link = f"https://www.taptap.cn{parent_a.get('href')}"

                # 2. 提取名称
                name = ""
                meta_name = title_div.find('meta', itemprop='name')
                if meta_name and meta_name.get('content'):
                    name = meta_name.get('content')

                # 如果两者都获取成功
                if name and link:
                    game_info = {
                        "游戏名称": name,
                        "详情页链接": link
                    }
                    all_games.append(game_info)
                    current_page_games.append(game_info)
            
            # 实时输出当前页的详细抓取结果
            print(f"  ✅ 第 {page} 页解析完毕，共获取到 {len(current_page_games)} 款游戏。明细如下：")
            for idx, game in enumerate(current_page_games, 1):
                print(f"    {idx}. {game['游戏名称']} -> {game['详情页链接']}")

            # 礼貌抓取：每次请求后休眠 1.5 秒
            time.sleep(1.5)

        except requests.exceptions.RequestException as e:
            print(f"  ❌ 抓取第 {page} 页时发生网络请求错误: {e}")
        except Exception as e:
            print(f"  ❌ 抓取第 {page} 页时发生未知异常: {e}")

    # 汇总并输出到 Excel
    print("\n" + "=" * 50)
    if all_games:
        df = pd.DataFrame(all_games)
        # 去重
        df = df.drop_duplicates(subset=['详情页链接'])

        if output_file:
            filename = output_file
        else:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{current_time}_TapTap游戏列表.xlsx"

        df.to_excel(filename, index=False)
        print(f"🎉 抓取任务圆满完成！共获取到 {len(df)} 款不重复的游戏。")
        print(f"📁 数据已成功保存至：{filename}")
    else:
        print("💔 抓取结束，未能获取到有效数据。")

if __name__ == "__main__":
    scrape_taptap("taptap_game_list.xlsx")