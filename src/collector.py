import arxiv
import os
import tarfile
import time
from pathlib import Path

# 共通の設定
DATA_RAW_DIR = Path("data/raw")

def get_paper_metadata(arxiv_id):
    """
    arXiv IDから論文のメタデータを取得する
    """
    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])
    
    try:
        results = list(client.results(search))
        if not results:
            print(f"Error: 論文ID {arxiv_id} が見つかりませんでした。")
            return None
        
        paper = results[0]
        print(f"取得成功: {paper.title}")
        return paper
    except Exception as e:
        print(f"メタデータ取得中にエラーが発生しました: {e}")
        return None

def collect_multiple_papers(id_list):
    """
    リスト内のすべての論文を順番にダウンロード・展開する
    """
    for arxiv_id in id_list:
        paper = get_paper_metadata(arxiv_id)
        if paper:
            download_and_extract_source(paper)
            # arXivサーバーへの負荷軽減のために2秒待機
            time.sleep(2)

def find_main_tex(directory):
    """
    ディレクトリ内を探索し、\documentclass を含むメインの .tex ファイルを特定する
    """
    # ディレクトリ内の全ファイルを再帰的に探索
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".tex"):
                file_path = Path(root) / file
                try:
                    # UTF-8で読み込みを試行し、エラーは無視（バイナリ混入対策）
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # \documentclass があればそれがメインファイル
                        if "\\documentclass" in content:
                            return file_path
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    return None

def download_and_extract_source(paper):
    arxiv_id = paper.get_short_id()
    paper_dir = DATA_RAW_DIR / arxiv_id
    paper_dir.mkdir(parents=True, exist_ok=True)

    tar_path = paper_dir / f"{arxiv_id}.tar.gz"
    if not tar_path.exists():
        print(f"\n--- Downloading {arxiv_id} ---")
        paper.download_source(dirpath=str(paper_dir), filename=tar_path.name)
    
    try:
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=paper_dir)
        
        # 【追加】メインファイルの特定
        main_tex = find_main_tex(paper_dir)
        if main_tex:
            print(f"Identified Main TeX: {main_tex.relative_to(DATA_RAW_DIR)}")
        else:
            print(f"Warning: Could not find main .tex in {arxiv_id}")
            
    except Exception as e:
        print(f"Failed to process {arxiv_id}: {e}")


if __name__ == "__main__":
    target_ids = ["2601.11505v1", "2412.13151", "1912.13318"]
    for arxiv_id in target_ids:
        paper = get_paper_metadata(arxiv_id)
        if paper:
            download_and_extract_source(paper)
            time.sleep(1)

