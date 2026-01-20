import arxiv
import os
import tarfile
import time
from pathlib import Path
import json

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

def find_author_file(directory):
    """
    ディレクトリ内の全 .tex ファイルをスキャンし、
    \author{ が記述されているファイルを特定する
    複数あった場合、とりあえず最初に見つかったものを返す
    何も見つからなかった場合は None を返して警告を出す
    """
    author_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".tex"):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # \author{ というタグが含まれているかチェック
                        if "\\author" in content:
                            author_files.append(file_path)
                except Exception as e:
                    print(f"Error reading {file}: {e}")

    if not author_files:
        print(f"Warning: Could not find author file in {directory}")
        return None
    return author_files[0]

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

        author_tex = find_author_file(paper_dir)
        if author_tex:
            # ファイル名だけを保存（ディレクトリ移動に強くするため）
            metadata = {
                "title": paper.title,
                "author_file": author_tex.name,
                "arxiv_id": paper.get_short_id()
            }
            save_metadata(paper_dir, metadata)         
        

    except Exception as e:
        print(f"Failed to process {arxiv_id}: {e}")

def save_metadata(paper_dir, paper_info):
    with open(paper_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(paper_info, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    from searcher import search_papers

    arxiv_categories = [
    # Computer Science
    "cs.AI", "cs.AR", "cs.CC", "cs.CE", "cs.CG", "cs.CL", "cs.CR", "cs.CV", "cs.CY", "cs.DB",
    "cs.DC", "cs.DL", "cs.DM", "cs.DS", "cs.ET", "cs.FL", "cs.GL", "cs.GR", "cs.GT", "cs.HC",
    "cs.IR", "cs.IT", "cs.LG", "cs.LO", "cs.MA", "cs.MM", "cs.MS", "cs.NA", "cs.NE", "cs.NI",
    "cs.OH", "cs.OS", "cs.PF", "cs.PL", "cs.RO", "cs.SC", "cs.SD", "cs.SE", "cs.SI", "cs.SY",
    # Economics
    "econ.EM", "econ.GN", "econ.TH",
    # Electrical Engineering and Systems Science
    "eess.AS", "eess.IV", "eess.SP", "eess.SY",
    # Mathematics
    "math.AG", "math.AT", "math.AP", "math.CA", "math.CO", "math.CT", "math.CV", "math.DG",
    "math.DS", "math.FA", "math.GM", "math.GN", "math.GR", "math.GT", "math.HO", "math.IT",
    "math.KT", "math.LO", "math.MG", "math.MP", "math.NA", "math.NT", "math.OA", "math.OC",
    "math.PR", "math.QA", "math.RA", "math.RT", "math.SG", "math.SP", "math.ST",
    # Physics
    "astro-ph.CO", "astro-ph.EP", "astro-ph.GA", "astro-ph.HE", "astro-ph.IM", "astro-ph.SR",
    "cond-mat.dis-nn", "cond-mat.mtrl-sci", "cond-mat.mes-hall", "cond-mat.other",
    "cond-mat.quant-gas", "cond-mat.soft", "cond-mat.stat-mech", "cond-mat.str-el", "cond-mat.supr-con",
    "gr-qc", "hep-ex", "hep-lat", "hep-ph", "hep-th", "math-ph", "quant-ph",
    "nlin.AO", "nlin.CD", "nlin.CG", "nlin.PS", "nlin.SI",
    "nucl-ex", "nucl-th",
    "physics.acc-ph", "physics.ao-ph", "physics.app-ph", "physics.atm-clus", "physics.atom-ph",
    "physics.bio-ph", "physics.chem-ph", "physics.class-ph", "physics.comp-ph", "physics.data-an",
    "physics.ed-ph", "physics.flu-dyn", "physics.gen-ph", "physics.geo-ph", "physics.hist-ph",
    "physics.ins-det", "physics.med-ph", "physics.optics", "physics.soc-ph", "physics.space-ph",
    # Quantitative Biology
    "q-bio.BM", "q-bio.CB", "q-bio.GN", "q-bio.MN", "q-bio.NC", "q-bio.OT", "q-bio.PE", "q-bio.QM", "q-bio.SC", "q-bio.TO",
    # Quantitative Finance
    "q-fin.CP", "q-fin.EC", "q-fin.GN", "q-fin.MF", "q-fin.PM", "q-fin.PR", "q-fin.RM", "q-fin.ST", "q-fin.TR",
    # Statistics
    "stat.AP", "stat.CO", "stat.ME", "stat.ML", "stat.OT", "stat.TH"
]

    for target_category in arxiv_categories:
        papers = search_papers(category=target_category, max_results=3)
        id_list = [paper.get_short_id() for paper in papers]
        collect_multiple_papers(id_list)
        print(f"Metadata saved for {arxiv_id}")