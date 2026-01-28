import re
from src.parser import LatexParser

class InformationExtractor:
    def __init__(self):
        self.parser = LatexParser()
    
    def detect_class(self, content):
        """
        【クラス判定】
        \documentclass{...} からクラス名を特定します。
        """
        match = re.search(r'\\documentclass(?:\[.*?\])?\{([a-zA-Z0-9_-]+)\}', content)
        return match.group(1) if match else "Unknown"
    
    def extract_amsart(self, content):
        """
        1人の著者に複数の \address があっても、リスト形式で全て保持します。
        共同所属の場合は、リストごと引き継ぎます。
        """
        segments = re.split(r'(\\author)', content)
        author_blocks = []
        for i in range(1, len(segments), 2):
            author_blocks.append(segments[i] + segments[i+1])

        temp_results = []
        
        # --- ブロックごとの解析 ---
        for block in author_blocks:
            name_match = re.search(r'\\author(?:\[.*?\])?\{([^{}]+)\}', block)
            if not name_match: continue
            
            # \address をリストとして全取得
            affils = [self.parser.clean_text(a) for a in re.findall(r'\\address\{([^{}]+)\}', block)]
            
            temp_results.append({
                "name": self.parser.clean_text(name_match.group(1)),
                "affiliations": affils  # ここはリスト
            })

        # --- 共同所属の補完ロジック ---
        final_results = []
        for i in range(len(temp_results)):
            current = temp_results[i]
            
            # 自分のブロックに所属がない場合、以降の著者から「所属リスト」を借りてくる
            if not current["affiliations"]:
                for j in range(i + 1, len(temp_results)):
                    if temp_results[j]["affiliations"]:
                        current["affiliations"] = temp_results[j]["affiliations"]
                        break
            
            # 最終的に所属が見つかった著者のみ採用（確実に抽出可能なもののみ）
            if current["affiliations"]:
                final_results.append(current)

        return final_results