import arxiv
import os
import tarfile
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

if __name__ == "__main__":
    test_id = "2412.13151"
    paper = get_paper_metadata(test_id)
    
    if paper:
        download_and_extract_source(paper)