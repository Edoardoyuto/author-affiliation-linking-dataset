import os
import re
from collections import Counter

# WSL内部の絶対パスを指定
SOURCE_DIR = "/home/edoardoyuto/arxiv-author-benchmark/data/raw" 

def strip_latex_comments(text):
    """LaTeXのコメント（% ...）を削除し、実質的なコードだけにする"""
    text = text.replace(r'\%', '___ESCAPED_PERCENT___')
    text = re.sub(r'%.*', '', text)
    text = text.replace('___ESCAPED_PERCENT___', '%')
    return text

def analyze_classes_recursive():
    class_counter = Counter()
    processed_folders = 0
    total_tex_files = 0
    
    # パスの存在確認
    if not os.path.exists(SOURCE_DIR):
        print(f"エラー: パスが見つかりません -> {SOURCE_DIR}")
        return

    print(f"--- スキャン開始: {SOURCE_DIR} ---")

    for root, dirs, files in os.walk(SOURCE_DIR):
        tex_files = [f for f in files if f.endswith(".tex")]
        if not tex_files:
            continue
            
        processed_folders += 1
        found_class_in_folder = False
        
        # アルファベット順に見て、メインっぽいファイルを優先的に探す
        for filename in sorted(tex_files):
            filepath = os.path.join(root, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    clean_content = strip_latex_comments(content)
                    
                    # \documentclass を検索
                    match = re.search(r'\\documentclass(?:\[.*?\])?\{([a-zA-Z0-9_-]+)\}', clean_content)
                    
                    if match:
                        doc_class = match.group(1)
                        class_counter[doc_class] += 1
                        found_class_in_folder = True
                        total_tex_files += 1
                        break 
                        
            except Exception:
                continue
        
        if not found_class_in_folder and tex_files:
            class_counter["(Unknown/No Class)"] += 1

    # 結果表示
    print("\n" + "="*45)
    print(f"{'Document Class':<25} | {'Count':<10}")
    print("-" * 45)
    
    for doc_class, count in class_counter.most_common():
        print(f"{doc_class:<25} | {count:<10}")
        
    print("="*45)
    print(f"スキャンしたフォルダ数: {processed_folders}")
    print(f"クラス特定数: {sum(class_counter.values()) - class_counter['(Unknown/No Class)']}")
    print(f"不明: {class_counter['(Unknown/No Class)']}")

if __name__ == "__main__":
    analyze_classes_recursive()