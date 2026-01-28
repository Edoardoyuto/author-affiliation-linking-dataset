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
    manifest.jsonを読み込む
    """
    with open(path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    return manifest

def save_manifest(manifest, path):
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

def get_main_tex_path(folder_path):
    """
    metadata.json を開き、"author_file" に指定されたファイルパスを返す。
    """
    metadata_path = os.path.join(folder_path, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            # metadata.json 内の "author_file" キーを取得
            tex_filename = meta.get("author_file")
            
            if tex_filename:
                return os.path.join(folder_path, tex_filename)
    except Exception as e:
        print(f"  [Warning] Failed to read metadata.json in {folder_path}: {e}")
    
    return None