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

def download_and_extract_source(paper):
    """
    ソースファイルをダウンロードして展開する
    """
    arxiv_id = paper.get_short_id()
    # 保存先のディレクトリ（data/raw/ID）を作成
    paper_dir = DATA_RAW_DIR / arxiv_id
    paper_dir.mkdir(parents=True, exist_ok=True)

    # 1. ダウンロード
    tar_path = paper_dir / f"{arxiv_id}.tar.gz"
    if not tar_path.exists():
        print(f"ダウンロード開始: {arxiv_id}...")
        paper.download_source(dirpath=str(paper_dir), filename=tar_path.name)
    
    # 2. 展開（解凍）
    try:
        print(f"展開中: {tar_path.name}...")
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=paper_dir)
        print(f"展開完了: {paper_dir}")
    except Exception as e:
        # 一部の古い論文などはtar形式でない場合があるためのハンドリング
        print(f"展開に失敗しました（単一のTeXファイルの可能性があります）: {e}")

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

if __name__ == "__main__":
   
    papr_list = ["2101.00001", "2101.00002", "2101.00003"]
    collect_multiple_papers(papr_list)