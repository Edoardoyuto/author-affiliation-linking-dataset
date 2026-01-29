import os
import json
import csv

"""
- 抽出したファイルを保存(manifesit.json)
- 抽出結果(results.jsonl)の保存
- 資料の探索
"""

def load_manifest(path):
    """
    manifest.jsonを読み込む。
    ファイルが存在しない、または中身が空の場合は、
    作成はせずに「空の辞書 {}」として扱う。
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        # 壊れていたり読み込めない場合も安全に空の辞書を返す
        print(f"  [Info] Manifest {path} is empty or invalid. Starting fresh.")
        return {}

def save_manifest(path, manifest):
    """
    manifest.jsonを保存する 
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)

def append_to_jsonl(path, data):
    """
    論文1件分の結果を JSONL 形式で1行として追記
    data は辞書型 {"arxiv_id": "...", "authors": [...]} を想定。
    """
    with open(path, 'a', encoding='utf-8') as f:
        # 1行のJSON文字列にして、最後に改行を足して追記
        line = json.dumps(data, ensure_ascii=False)
        f.write(line + '\n')

def get_tex_paths(folder_path):
    """
    ドキュメントクラス判定用(root)と著者抽出用(author)のTeXパスを特定する。
    1. metadata.json の指定を確認
    """
    metadata_path = os.path.join(folder_path, "metadata.json")
    root_path = None
    author_path = None

    # --- 1. メタデータからの取得試行 ---
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                r_file = meta.get("root_file")
                a_file = meta.get("author_file")
                
                if r_file:
                    root_path = os.path.join(folder_path, r_file)
                if a_file:
                    author_path = os.path.join(folder_path, a_file)
        except Exception as e:
            print(f"  [Warning] metadata.json の読み込み失敗 ({folder_path}): {e}")

        return root_path, author_path