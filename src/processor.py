import os
import json
from src.utils import load_manifest, save_manifest, append_to_jsonl, get_main_tex_path
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
    
    # スキャン対象のID一覧
    arxiv_ids = [d for d in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, d))]
    
    print(f"--- 🚀 抽出フェーズ開始: {len(arxiv_ids)} フォルダ ---")
    
    counts = {"success": 0, "skipped": 0, "error": 0}

    for aid in arxiv_ids:
        if aid in manifest: continue

        folder_path = os.path.join(SOURCE_DIR, aid)
        tex_path = get_main_tex_path(folder_path)
        
        # 1. そもそもファイルがない場合
        if not tex_path:
            record_log(aid, "NOT_FOUND", "Main TeX file not specified in metadata.json")
            manifest[aid] = {"status": "error", "reason": "no_tex"}
            counts["error"] += 1
            continue

        try:
            with open(tex_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = extractor.parser.strip_comments(f.read())
            
            doc_class = extractor.detect_class(content)

            # 2. amsart の場合
            # 2. amsart の場合
            if doc_class == "amsart":
                authors_data = extractor.extract_amsart(content)
                
                if authors_data:
                    # 【成功】
                    output = {"arxiv_id": aid, "doc_class": doc_class, "authors": authors_data}
                    append_to_jsonl(RESULTS_PATH, output)
                    record_log(aid, "SUCCESS", "抽出成功", doc_class, len(authors_data))
                    manifest[aid] = {"status": "success", "class": doc_class}
                    counts["success"] += 1
                    print(f"✅ [amsart] {aid}: {len(authors_data)} authors extracted.")
                else:
                    # 【失敗】amsart なのに著者が一人も取れなかった場合
                    reason = "抽出パターンにマッチしませんでした（要確認）"
                    record_log(aid, "FAILED", reason, doc_class) # ERROR または FAILED
                    manifest[aid] = {"status": "failed", "reason": "no_match"}
                    counts["error"] += 1
            
            # 3. ターゲット外のクラスの場合
            else:
                # 【スキップ】ここでもログを残すと「全件ログ」になります
                msg = f"未対応のクラスです: {doc_class}"
                record_log(aid, "SKIPPED", msg, doc_class)
                manifest[aid] = {"status": "skipped", "class": doc_class or "unknown"}
                counts["skipped"] += 1

        except Exception as e:
            record_log(aid, "SYSTEM_ERROR", str(e))
            manifest[aid] = {"status": "error", "message": str(e)}
            counts["error"] += 1

    # 保存
    save_manifest(MANIFEST_PATH, manifest)
    print(f"\n--- 🏁 完了レポート ---")
    print(f"成功(amsart): {counts['success']} 件")
    print(f"ターゲット外: {counts['skipped']} 件")
    print(f"エラー/失敗: {counts['error']} 件 (詳細は extraction_error.jsonl へ)")

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