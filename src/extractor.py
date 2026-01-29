import re
from src.parser import LatexParser

class InformationExtractor:
    def __init__(self):
        self.parser = LatexParser()
        # クラス名とメソッドの対応表
        self.dispatch_map = {
            "amsart": self.extract_amsart,
            "article": self.extract_article,    # これから作る
            "revtex4-1": self.extract_revtex,  # これから作る
            "revtex4-2": self.extract_revtex,  # これから作る
            "ieeeconf": self.extract_ieee      # これから作る
        }
    
    def detect_class(self, content):
        """
        【クラス判定】
        \documentclass{...} からクラス名を特定します。
        """
        match = re.search(r'\\documentclass(?:\[.*?\])?\{([a-zA-Z0-9_-]+)\}', content)
        return match.group(1) if match else "Unknown"

    def extract(self, doc_class, content):
        """判定されたクラスに応じて抽出を実行するエントリポイント"""
        extract_method = self.dispatch_map.get(doc_class)
        if extract_method:
            return extract_method(content)
        return None  # 未対応の場合は None
    
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
            # 著者の抽出（[...]を許容）
            name_match = re.search(r'\\author(?:\[.*?\])?\{([^{}]+)\}', block)
            if not name_match: continue
            
            # --- ここを修正：\address の直後に [...] があっても無視して { } を探す ---
            # re.DOTALL を入れることで、{}内での改行にも対応できます
            affils = [self.parser.clean_text(a) for a in re.findall(r'\\address(?:\[.*?\])?\{(.*?)\}', block, re.DOTALL)]
            
            temp_results.append({
                "name": self.parser.clean_text(name_match.group(1)),
                "affiliations": affils
            })

        # --- 引き継ぎロジックを「前後」対応にするとさらに盤石 ---
        final_results = []
        for i in range(len(temp_results)):
            current = temp_results[i]
            
            if not current["affiliations"]:
                # 1. まず後ろ(j > i)を探す
                for j in range(i + 1, len(temp_results)):
                    if temp_results[j]["affiliations"]:
                        current["affiliations"] = temp_results[j]["affiliations"]
                        break
                # 2. それでもなければ前(j < i)を探す
                if not current["affiliations"]:
                    for j in range(i - 1, -1, -1):
                        if temp_results[j]["affiliations"]:
                            current["affiliations"] = temp_results[j]["affiliations"]
                            break
            
            # 最終的に所属が見つかった著者のみ採用（確実に抽出可能なもののみ）
            if current["affiliations"]:
                final_results.append(current)

        return final_results