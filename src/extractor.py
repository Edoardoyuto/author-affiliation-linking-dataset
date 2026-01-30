import re
from src.parser import LatexParser

class InformationExtractor:
    def __init__(self):
        self.parser = LatexParser()
        # クラス名とメソッドの対応表
        self.dispatch_map = {
            "amsart": self.extract_amsart,
            #"article": self.extract_article,    # これから作る
            "revtex4-1": self.extract_revtex,  
            "revtex4-2": self.extract_revtex,  
            "revtex4": self.extract_revtex,  
            "apsrev4-1": self.extract_revtex,  
            "apsrev4-2": self.extract_revtex
            #"ieeeconf": self.extract_ieee      # これから作る
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
        pattern = re.compile(r'\\(author|address)(?:\[.*?\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)
        results, pending_queue, last_action = [], [], None

        for cmd, val in matches:
            val = self.parser.clean_text(val)
            if cmd == "author":
                if last_action == "address": pending_queue = [] # 次の著者が来たらリセット
                obj = {"name": val, "affiliations": []}
                results.append(obj)
                pending_queue.append(obj)
                last_action = "author"
            elif cmd == "address":
                for author in pending_queue:
                    if val not in author["affiliations"]: author["affiliations"].append(val)
                last_action = "address"
        return [a for a in results if a["affiliations"]]

    def extract_revtex(self, content):
        pattern = re.compile(r'\\(author|affiliation|altaffiliation)(?:\[.*?\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)
        results, pending_queue, last_action = [], [], None

        for cmd, val in matches:
            val = self.parser.clean_text(val)
            if cmd == "author":
                if last_action in ["affiliation", "altaffiliation"]: pending_queue = []
                obj = {"name": val, "affiliations": []}
                results.append(obj)
                pending_queue.append(obj)
                last_action = "author"
            elif cmd in ["affiliation", "altaffiliation"]: # 現所属も所属リストに加える
                for author in pending_queue:
                    if val not in author["affiliations"]: author["affiliations"].append(val)
                last_action = cmd
        return [a for a in results if a["affiliations"]]