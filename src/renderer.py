import os
import json
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from src.utils import get_tex_paths

'''
抽出された情報の確認と、元ファイル、PDFを開く
START_ID に任意のIDを入力すると、そのID以降のファイルのみ開く
'''

# パス設定
BASE_DIR = "/home/edoardoyuto/arxiv-author-benchmark"
RESULTS_PATH = os.path.join(BASE_DIR, "data/author_benchmarks.jsonl")
SOURCE_DIR = os.path.join(BASE_DIR, "data/raw")
START_ID = "2601.20549v1"
# ...（パス設定までは同じ）
START_ID = "2601.20549v1"

def render_with_selenium():
    if not os.path.exists(RESULTS_PATH):
        print(f"Error: {RESULTS_PATH} が見つかりません。")
        return

    # Selenium設定
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)

    # --- 修正ポイント1: フラグの初期値をループの外に置く ---
    # START_ID が指定されていない(None)なら最初から表示、指定があればスキップから開始
    is_skipping = True if START_ID else False

    print("\n" + "="*80)
    print(f" 🔍 検品開始 (START_ID: {START_ID or '最初から'})")
    print("="*80)

    try:
        with open(RESULTS_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                aid = data.get("arxiv_id")
                
                # --- 修正ポイント2: START_ID に到達したか判定 ---
                if is_skipping:
                    if aid == START_ID:
                        is_skipping = False # 到達したので、これ以降はスキップしない
                    else:
                        continue # まだ到達していないので、この行の処理を飛ばして次へ

                # --- 以降、表示処理 ---
                doc_class = data.get("doc_class")
                authors = data.get("authors", [])

                print(f"\n📄 [ArXiv ID]: {aid} ({doc_class})")
                print("-" * 40)
                print(json.dumps(authors, indent=4, ensure_ascii=False))
                print("-" * 40)

                driver.get(f"https://arxiv.org/pdf/{aid}.pdf")
                
                folder_path = os.path.join(SOURCE_DIR, aid)
                _, author_path = get_tex_paths(folder_path)
                
                if author_path and os.path.exists(author_path):
                    file_p = Path(author_path).resolve()
                    subprocess.run(["code", str(file_p)])

                cmd = input("\n[Enter]: 次へ / [q]: 終了 > ").lower()
                if cmd == 'q':
                    break
    finally:
        driver.quit()

if __name__ == "__main__":
    render_with_selenium()