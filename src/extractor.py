import re
from src.parser import LatexParser

class InformationExtractor:
    def __init__(self):
        self.parser = LatexParser()
        # クラス名とメソッドの対応表
        # 基本となる抽出メソッドの定義
        self.dispatch_map = {
            # --- amsart ---
            "amsart": self.extract_amsart,
            "amsproc": self.extract_amsart,

            # --- REVTeX系 ---
            "revtex4": self.extract_revtex,
            "revtex4-1": self.extract_revtex,
            "revtex4-2": self.extract_revtex,
            "apsrev4-1": self.extract_revtex,
            "apsrev4-2": self.extract_revtex,
            "aastex631": self.extract_revtex, 
            "aastex7": self.extract_revtex,
            "aa": self.extract_revtex,

            # --- acmart系 ---
            "acmart": self.extract_acmart,
            "acmsmall": self.extract_acmart,
            "aamas": self.extract_acmart,

            # --- エルゼビア系 ---
            "elsarticle": self.extract_elsarticle,
            "cas-dc": self.extract_elsarticle, # 同じロジックでいける

            # --- Springer流派 ---
            "sn-jnl": self.extract_sn_jnl,
            #"llncs": self.extract_llncs, # 後で作成
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
        [amsart 最終進化版]
        .cls の挙動に基づき、\address, \curraddr, \author[] の相関を完璧に処理します。
        """
        # 1. 抽出対象：author, address, curraddr (email等は除外して純度を上げる)
        # オプション引数 [...] と 必須引数 {...} を両方キャッチ
        pattern = re.compile(r'\\(author|address|curraddr)(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)

        results = []
        pending_queue = [] # 所属待ちの著者
        
        # 著者名での直接紐付け用辞書 ( \address[Name]{Affil} 対応 )
        name_to_author_obj = {}

        for cmd, opt, val in matches:
            opt = self.parser.clean_text(opt)
            val = self.parser.clean_text(val)
            if not val and cmd != "author": continue

            if cmd == "author":
                # 新しい著者が来たら、前のグループの所属割当フェーズは終了
                # (cls内の \g@addto@macro\addresses{\author{}} の動き)
                pending_queue = []
                
                author_obj = {"name": val, "affiliations": []}
                results.append(author_obj)
                pending_queue.append(author_obj)
                
                # 名前（フルネームと姓の両方）で逆引きできるようにしておく
                name_to_author_obj[val] = author_obj
                last_name = val.split()[-1]
                if last_name not in name_to_author_obj:
                    name_to_author_obj[last_name] = author_obj

            elif cmd in ["address", "curraddr"]:
                # --- 所属の割当ロジック ---
                
                # A. オプション引数に名前が書いてある場合 ( \address[Taro]{Univ} )
                if opt and opt in name_to_author_obj:
                    target = name_to_author_obj[opt]
                    if val not in target["affiliations"]:
                        target["affiliations"].append(val)
                
                # B. 通常のケース ( 待機リスト全員に配る )
                else:
                    for author in pending_queue:
                        if val not in author["affiliations"]:
                            author["affiliations"].append(val)
                
                # address が出た後は、次の著者が来るまで pending_queue を維持
                # (連続する \address や \curraddr を全て拾うため)

        # 完璧なデータのみ：所属が1つ以上ある著者のみ採用
        return [a for a in results if a["affiliations"]]

    def extract_revtex(self, content):
        """
        [REVTeX 4.2 高精度版]
        \address を無視し、標準的な \affiliation のみを採用することで、
        変則的な手動番号付け論文を自動的に除外します。
        """
        # 抽出コマンドから address を削除
        pattern = re.compile(
            r'\\(author|affiliation|altaffiliation|collaboration)(?:\[.*?\])?\{(.*?)\}', 
            re.DOTALL
        )
        matches = pattern.findall(content)

        results = []
        pending_queue = []       # 所属確定待ちの著者リスト
        last_assigned_group = [] # 連続する所属に対応するための記憶用バッファ
        last_action = None

        for cmd, val in matches:
            val = self.parser.clean_text(val)
            if not val: continue

            if cmd == "author":
                # 新しい著者が現れたら、直前の所属割当フェーズが完了したとみなす
                if last_action in ["affiliation", "collaboration"]:
                    pending_queue = []
                
                author_obj = {
                    "name": val, 
                    "affiliations": [], 
                    "altaffiliations": [], 
                    "collaboration": None
                }
                results.append(author_obj)
                pending_queue.append(author_obj)
                last_action = "author"

            elif cmd == "affiliation":
                # 待機リストにいる全員に所属を付与
                targets = pending_queue if pending_queue else last_assigned_group
                for author in targets:
                    if val not in author["affiliations"]:
                        author["affiliations"].append(val)
                
                # 割当が終わった著者を記憶しつつ、待機リストをリセット
                if pending_queue:
                    last_assigned_group = pending_queue[:]
                    pending_queue = []
                last_action = "affiliation"

            elif cmd == "altaffiliation":
                # 現所属（直近の1人のみに付与）
                if results:
                    results[-1]["altaffiliations"].append(val)
                last_action = "altaffiliation"

            elif cmd == "collaboration":
                # 待機中の著者全員をこの共同研究グループに紐付ける
                for author in pending_queue:
                    author["collaboration"] = val
                last_action = "collaboration"

        # 所属が取れた著者のみをベンチマークとして採用
        # (address しかない論文はこの時点で空リストとして返されます)
        return [a for a in results if a["affiliations"]]
    
    def extract_acmart(self, content):
        """
        [acmart専用] 
        タグ階層を平坦化し、直前の著者に属性を紐付ける。
        """
        # 1. まず author, affiliation, email を順番通りに拾う
        pattern = re.compile(r'\\(author|affiliation|email)(?:\[.*?\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)

        results = []
        
        for cmd, val in matches:
            if cmd == "author":
                # 新しい著者が来たら「現在の箱」を作成
                name = self.parser.clean_text(val)
                results.append({"name": name, "affiliations": []})

            elif cmd == "affiliation":
                if results:
                    # affiliation内部の \institution{X} などを X に変換
                    # 複数のタグがある場合は、カンマ区切りで連結する
                    tags = re.findall(r'\\(?:institution|city|country|state|postcode|streetaddress)\{(.*?)\}', val, re.DOTALL)
                    if tags:
                        clean_affil = ", ".join([self.parser.clean_text(t) for t in tags if t.strip()])
                    else:
                        # タグがない（古い書き方など）場合は中身を掃除してそのまま採用
                        clean_affil = self.parser.clean_text(re.sub(r'\\[a-z]+', '', val))
                    
                    if clean_affil:
                        results[-1]["affiliations"].append(clean_affil)

            elif cmd == "email":
                if results:
                    results[-1]["email"] = self.parser.clean_text(val)

        # 所属が1つも取れなかった著者は除外
        return [a for a in results if a["affiliations"]]
    
    def extract_elsarticle(self, content):
        """
        [elsarticle専用：ハイブリッド方式]
        ラベルがあればID紐付けを優先し、なければ直近の著者に付与します。
        """
        # 抽出対象: author, address, affiliation
        pattern = re.compile(r'\\(author|address|affiliation)(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)

        results = []
        id_map = {} # { "1": "Doshisha Univ" }
        author_with_labels = [] # 後でID紐付けするための一次保存

        for cmd, label, val in matches:
            val = self.parser.clean_text(val)
            label = self.parser.clean_text(label)
            if not val: continue

            if cmd == "author":
                author_obj = {"name": val, "affiliations": [], "labels": label.split(',') if label else []}
                results.append(author_obj)
                author_with_labels.append(author_obj)

            elif cmd in ["address", "affiliation"]:
                if label:
                    # ラベルがある場合は辞書に登録
                    for l in label.split(','):
                        id_map[l.strip()] = val
                else:
                    # ラベルがない場合は、直近の著者に即時付与 (changelogに記載の挙動)
                    if results:
                        results[-1]["affiliations"].append(val)

        # --- 最後にラベルの答え合わせ ---
        for author in results:
            if author["labels"]:
                for l in author["labels"]:
                    l = l.strip()
                    if l in id_map and id_map[l] not in author["affiliations"]:
                        author["affiliations"].append(id_map[l])

        return [a for a in results if a["affiliations"]]
    
    def extract_sn_jnl(self, content):
        """
        [sn-jnl 専用：タグ＆IDマッピング方式]
        fnm/sur タグと orgname タグを狙い撃ちし、IDで紐付けます。
        """
        # 1. 所属の辞書を作成 ( \affil[ID]{...} )
        affil_pattern = re.compile(r'\\affil(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        affils = affil_pattern.findall(content)
        
        id_to_org = {}
        for aid, text in affils:
            # \orgname{...} と \orgdiv{...} を抽出して結合
            org_name = re.search(r'\\orgname\{(.*?)\}', text)
            org_div = re.search(r'\\orgdiv\{(.*?)\}', text)
            
            parts = [p.group(1) for p in [org_div, org_name] if p]
            clean_org = ", ".join([self.parser.clean_text(p) for p in parts])
            
            if aid:
                for a in aid.split(','):
                    id_to_org[a.strip()] = clean_org

        # 2. 著者を抽出して ID で紐付け
        author_pattern = re.compile(r'\\author\*?(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        authors = author_pattern.findall(content)
        
        results = []
        for aid, body in authors:
            # 姓名をタグから合成 ( \fnm{Taro} \sur{Yamada} )
            fnm = re.search(r'\\fnm\{(.*?)\}', body)
            sur = re.search(r'\\sur\{(.*?)\}', body)
            full_name = " ".join([p.group(1) for p in [fnm, sur] if p])
            
            if not full_name: # タグがない場合は中身をそのまま掃除
                full_name = self.parser.clean_text(body)

            author_affils = []
            if aid:
                for a in aid.split(','):
                    a = a.strip()
                    if a in id_to_org:
                        author_affils.append(id_to_org[a])
            
            results.append({"name": full_name, "affiliations": author_affils})

        return [a for a in results if a["affiliations"]]