import os
import json
from src.utils import load_manifest, save_manifest, append_to_jsonl, get_tex_paths
from src.extractor import InformationExtractor

# パス設定
BASE_DIR = "/home/edoardoyuto/arxiv-author-benchmark"
SOURCE_DIR = os.path.join(BASE_DIR, "data/raw")
MANIFEST_PATH = os.path.join(BASE_DIR, "data/processed_manifest.json")
RESULTS_PATH = os.path.join(BASE_DIR, "data/author_benchmarks.jsonl")
LOG_PATH = os.path.join(BASE_DIR, "data/execution_log.jsonl")

def run_pipeline():
    extractor = InformationExtractor()
    manifest = load_manifest(MANIFEST_PATH)
    arxiv_ids = [d for d in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, d))]
    
    print(f"--- 🚀 抽出フェーズ開始: {len(arxiv_ids)} フォルダ ---")
    counts = {"success": 0, "skipped": 0, "error": 0}

    for aid in arxiv_ids:
        if aid in manifest: continue

        folder_path = os.path.join(SOURCE_DIR, aid)
        root_path, author_path = get_tex_paths(folder_path)
        
        if not root_path or not os.path.exists(root_path):
            record_log(aid, "ERROR", "判定用TeXファイルが見つかりません")
            manifest[aid] = {"status": "error", "reason": "root_not_found"}
            counts["error"] += 1
            continue

        try:
            # --- フェーズA: ドキュメントクラスの判定 ---
            with open(root_path, 'r', encoding='utf-8', errors='ignore') as f:
                root_content = extractor.parser.strip_comments(f.read())
            doc_class = extractor.detect_class(root_content)

            # --- フェーズB: 著者情報の読み込み ---
            # クラス判定用と著者情報用が別ファイルなら開き直す
            if root_path != author_path and os.path.exists(author_path):
                with open(author_path, 'r', encoding='utf-8', errors='ignore') as f:
                    author_content = extractor.parser.strip_comments(f.read())
            else:
                author_content = root_content

            # --- フェーズC: クラスに応じた抽出処理 (自動振り分け) ---
            # extractor.extract() が dispatch_map を見て適切なメソッドを呼び出す
            authors_data = extractor.extract(doc_class, author_content)

            if authors_data:
                # 【成功】
                output = {"arxiv_id": aid, "doc_class": doc_class, "authors": authors_data}
                append_to_jsonl(RESULTS_PATH, output)
                record_log(aid, "SUCCESS", "抽出成功", doc_class, len(authors_data))
                manifest[aid] = {"status": "success", "class": doc_class}
                counts["success"] += 1
                print(f"✅ [{doc_class}] {aid}: {len(authors_data)} authors.")
            
            elif doc_class in extractor.dispatch_map:
                # 【失敗】対応クラスなのに抽出できなかった（正規表現の不一致など）
                msg = f"{doc_class}形式ですが、著者を特定できませんでした"
                record_log(aid, "FAILED", msg, doc_class)
                manifest[aid] = {"status": "failed", "reason": "pattern_mismatch"}
                counts["error"] += 1
            
            else:
                # 【スキップ】そもそもまだ対応していないクラス
                msg = f"未対応のクラスです: {doc_class}"
                record_log(aid, "SKIPPED", msg, doc_class)
                manifest[aid] = {"status": "skipped", "class": doc_class or "unknown"}
                counts["skipped"] += 1

        except Exception as e:
            record_log(aid, "ERROR", f"システムエラー: {str(e)}")
            manifest[aid] = {"status": "error"}
            counts["error"] += 1

    save_manifest(MANIFEST_PATH, manifest)
    print(f"\n--- 🏁 完了レポート ---")
    print(f" 成功 : {counts['success']} 件 / スキップ : {counts['skipped']} 件 / 失敗 : {counts['error']} 件")

def record_log(aid, status, message, doc_class=None, count=0):
    """
    【統合ログ作成】
    status: "SUCCESS", "ERROR", "SKIPPED"
    message: 成功時のメッセージ、または失敗・スキップの理由
    """
    log_entry = {
        "arxiv_id": aid,
        "status": status,
        "message": message,
        "doc_class": doc_class,
        "author_count": count
    }
    # 事務局(utils)の append_to_jsonl を使って保存
    append_to_jsonl(LOG_PATH, log_entry)

if __name__ == "__main__":
    run_pipeline()