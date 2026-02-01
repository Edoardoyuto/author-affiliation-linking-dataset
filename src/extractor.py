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
            "cas-dc": self.extract_elsarticle, 

            # --- Springer流派 ---
            "sn-jnl": self.extract_sn_jnl,
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
        [amsart 最終進化版 - リンキング・ベンチマーク特化]
        .cls の挙動に基づき、名前とあらゆる所属（現所属含む）を確実に紐付け、
        ベンチマークを汚す LaTeX コマンドを徹底除去します。
        """
        # 1. 抽出対象：author, address, curraddr
        # \author[shortname]{fullname} の [shortname] も正確にキャッチする
        pattern = re.compile(r'\\(author|address|curraddr)(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)

        results = []
        pending_queue = [] 
        
        # 紐付け用辞書 (正規化された名前 -> オブジェクト)
        name_map = {}

        for cmd, opt, val in matches:
            # 必須：紐付け前に parser.clean_text で徹底的に「研磨」する
            # $^*$ や \orcidlink などのノイズを除去した状態が正解データの「鍵」になる
            opt_clean = self.parser.clean_text(opt)
            val_clean = self.parser.clean_text(val)
            
            if not val_clean and cmd != "author": continue

            if cmd == "author":
                # a. 著者が出現 = 前の所属割当ブロックの完全終了 (cls内の挙動)
                # 既に所属が1つでも入っている著者がキューにいたら、キューを空にする
                if any(a["affiliations"] for a in pending_queue):
                    pending_queue = []
                
                # ベンチマーク形式：名前と所属リストのみ
                author_obj = {"name": val_clean, "affiliations": []}
                results.append(author_obj)
                pending_queue.append(author_obj)
                
                # b. 紐付けの「鍵」を増やす
                # 鍵1: フルネーム (Yamada Taro)
                name_map[val_clean] = author_obj
                # 鍵2: オプションの短縮名 (T. Yamada)
                if opt_clean:
                    name_map[opt_clean] = author_obj
                # 鍵3: 姓のみ (Yamada) - address[Yamada] という書き方に対応
                last_name = val_clean.split()[-1]
                if last_name not in name_map:
                    name_map[last_name] = author_obj

            elif cmd in ["address", "curraddr"]:
                # --- 所属の統合割当 ---
                # curraddr (現所属) も所属の一つとしてフラットに扱う
                
                # A. オプション引数による名指し紐付け (\address[T. Yamada]{Univ})
                if opt_clean and opt_clean in name_map:
                    target = name_map[opt_clean]
                    if val_clean not in target["affiliations"]:
                        target["affiliations"].append(val_clean)
                
                # B. キュー方式（待機リスト全員に配る）
                else:
                    for author in pending_queue:
                        if val_clean not in author["affiliations"]:
                            author["affiliations"].append(val_clean)
                
        # 最終フィルタリング：所属が1つも取れなかった著者はベンチマークから除外（純度維持）
        return [a for a in results if a["affiliations"]]

    def extract_revtex(self, content):
        """
        [REVTeX 4.2 最終進化版 - リンキング・ベンチマーク特化]
        名前とあらゆる所属情報を単一のリストに集約し、
        物理学論文特有の複雑なグループ紐付けを完璧に処理します。
        """
        # 1. 抽出対象：author, affiliation, altaffiliation
        # (collaborationは状態遷移のトリガーとして残すが、出力には含めない)
        pattern = re.compile(
            r'\\(author|affiliation|altaffiliation|collaboration)(?:\[.*?\])?\{(.*?)\}', 
            re.DOTALL
        )
        matches = pattern.findall(content)

        results = []
        pending_queue = []       # 所属確定待ちの著者リスト
        last_assigned_group = [] # 「同じ著者に連続して所属がつく」ケースの対応用
        last_action = None

        for cmd, val in matches:
            # parser.clean_text を通して $^*$ や \orcidlink などのノイズを即時除去
            val_clean = self.parser.clean_text(val)
            if not val_clean: continue

            if cmd == "author":
                # a. 新しい著者が出現したら、前の所属割当ブロックをリセット
                # (所属コマンドが出た後に著者が来たらキューを空にする)
                if last_action in ["affiliation", "collaboration"]:
                    pending_queue = []
                
                # ベンチマーク用オブジェクト：所属は一つにまとめる
                author_obj = {
                    "name": val_clean, 
                    "affiliations": []
                }
                results.append(author_obj)
                pending_queue.append(author_obj)
                last_action = "author"

            elif cmd == "affiliation":
                # b. グループ割当：待機中の著者全員にこの所属を付与
                # 待機中がいなければ、直前のグループに「第2所属」として付与
                targets = pending_queue if pending_queue else last_assigned_group
                for author in targets:
                    if val_clean not in author["affiliations"]:
                        author["affiliations"].append(val_clean)
                
                if pending_queue:
                    last_assigned_group = pending_queue[:]
                    pending_queue = []
                last_action = "affiliation"

            elif cmd == "altaffiliation":
                # c. 個別割当：直近の「1人」に現所属や旧所属として追加
                # これはグループ全体ではなく、特定の人物にのみ付随する情報
                if results:
                    if val_clean not in results[-1]["affiliations"]:
                        results[-1]["affiliations"].append(val_clean)
                last_action = "altaffiliation"

            elif cmd == "collaboration":
                # 共同研究名は状態のリセットのみに使用し、データには含めない
                pending_queue = []
                last_action = "collaboration"

        # 最終フィルタリング：所属が1つ以上取れた著者のみを採用
        return [
            {"name": a["name"], "affiliations": a["affiliations"]}
            for a in results if a["affiliations"]
        ]
    
    def extract_acmart(self, content):
        """
        [acmart専用 - リンキング・ベンチマーク特化]
        直前の \author に所属を紐付ける「個人属性集約」ロジック。
        emailを除去し、\additionalaffiliation（追加所属）も統合します。
        """
        # 1. 抽出対象：author, affiliation, additionalaffiliation
        # (email はベンチマークのノイズになるため抽出対象から除外)
        pattern = re.compile(
            r'\\(author|affiliation|additionalaffiliation)(?:\[.*?\])?\{(.*?)\}', 
            re.DOTALL
        )
        matches = pattern.findall(content)

        results = []
        
        for cmd, val in matches:
            # 常に parser.clean_text で LaTeX の装飾（肩番号や特殊コマンド）を剥ぐ
            if cmd == "author":
                # 新しい著者が来たら「現在の箱」を作成
                name_clean = self.parser.clean_text(val)
                results.append({"name": name_clean, "affiliations": []})

            elif cmd in ["affiliation", "additionalaffiliation"]:
                # 直近の著者に所属を追加する
                if not results: continue
                
                # a. affiliation内部の構造化タグ (\institution{...}等) を抽出
                tags = re.findall(
                    r'\\(?:institution|department|city|country|state|postcode|streetaddress)\{(.*?)\}', 
                    val, 
                    re.DOTALL
                )
                
                if tags:
                    # 各タグの中身を掃除してカンマ区切りで連結
                    clean_affil = ", ".join([self.parser.clean_text(t) for t in tags if t.strip()])
                else:
                    # タグがない（古い、または変則的な書き方）場合は全体を掃除
                    # \textbf 等のコマンド名だけを消して中身を残す処理
                    clean_affil = self.parser.clean_text(val)
                
                if clean_affil:
                    results[-1]["affiliations"].append(clean_affil)

        # 最終フィルタリング：所属が1つ以上取れた著者のみを採用（正解データとしての品質保証）
        return [
            {"name": a["name"], "affiliations": a["affiliations"]}
            for a in results if a["affiliations"]
        ]
    
    def extract_elsarticle(self, content):
        """
        [elsarticle専用 - リンキング・ベンチマーク特化]
        IDラベル方式と直後付与方式を統合。
        organization={...} 等のタグをパースし、純粋な所属文字列を作成します。
        """
        # 1. 抽出対象：author, address, affiliation
        pattern = re.compile(r'\\(author|address|affiliation)(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
        matches = pattern.findall(content)

        results = []
        id_map = {} 
        
        for cmd, label, val in matches:
            # a. 所属情報のクレンジング (Key-Value形式の解消)
            if cmd in ["address", "affiliation"]:
                # organization={...} や city={...} の中身だけを抽出して結合
                kv_matches = re.findall(r'[a-z]+=\{(.*?)\}', val, re.DOTALL)
                if kv_matches:
                    clean_val = ", ".join([self.parser.clean_text(v) for v in kv_matches if v.strip()])
                else:
                    # タグがない場合は全体を掃除
                    clean_val = self.parser.clean_text(val)
            else:
                # 著者の場合は名前を掃除
                clean_val = self.parser.clean_text(val)

            clean_label = self.parser.clean_text(label)

            if cmd == "author":
                # 著者オブジェクトの作成 (labelsは一時的に保持)
                author_obj = {
                    "name": clean_val, 
                    "affiliations": [], 
                    "temp_labels": [l.strip() for l in clean_label.split(',')] if clean_label else []
                }
                results.append(author_obj)

            elif cmd in ["address", "affiliation"]:
                if clean_label:
                    # ラベルがある場合は辞書に登録
                    for l in clean_label.split(','):
                        id_map[l.strip()] = clean_val
                else:
                    # ラベルがない場合は直近の著者に即時付与
                    if results:
                        results[-1]["affiliations"].append(clean_val)

        # 2. IDラベルに基づく所属の「答え合わせ（リンキング）」
        for author in results:
            if author["temp_labels"]:
                for l in author["temp_labels"]:
                    if l in id_map and id_map[l] not in author["affiliations"]:
                        author["affiliations"].append(id_map[l])
        
        # 最終出力形式：名前と所属リストのみ（不要なtemp_labelsを除去）
        return [
            {"name": a["name"], "affiliations": a["affiliations"]}
            for a in results if a["affiliations"]
        ]
    
    import re

def extract_sn_jnl(self, content):
    
    # 1. 所属辞書の作成
    id_to_org = {}
    affil_pattern = re.compile(r'\\affil(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
    affil_matches = affil_pattern.findall(content)
    
    for aid, text in affil_matches:
        org_div = re.search(r'\\orgdiv\{(.*?)\}', text, re.DOTALL)
        org_name = re.search(r'\\orgname\{(.*?)\}', text, re.DOTALL)
        
        parts = []
        if org_div: parts.append(self.parser.clean_text(org_div.group(1)))
        if org_name: parts.append(self.parser.clean_text(org_name.group(1)))
        
        clean_org = ", ".join(parts) if parts else self.parser.clean_text(text)
        
        # 所属にタグが残っていたら、その論文は処理不能として即終了
        if "\\" in clean_org or "{" in clean_org:
            return [] # または raise ExtractionError("Affiliation parse failed")

        if aid:
            for a in aid.split(','):
                id_to_org[a.strip()] = clean_org

    # 2. 著者の抽出と紐付け
    results = []
    author_pattern = re.compile(r'\\author\*?(?:\[(.*?)\])?\{(.*?)\}', re.DOTALL)
    author_matches = author_pattern.findall(content)
    
    for aid, body in author_matches:
        fnm_match = re.search(r'\\fnm\{(.*?)\}', body, re.DOTALL)
        sur_match = re.search(r'\\sur\{(.*?)\}', body, re.DOTALL)
        
        if fnm_match and sur_match:
            f_name = self.parser.clean_text(fnm_match.group(1))
            l_name = self.parser.clean_text(sur_match.group(1))
            full_name = f"{f_name} {l_name}".strip()
        else:
            full_name = self.parser.clean_text(body)

        # 【厳格なバリデーション】
        # 名前の一部にでもタグが残っていたら、この論文データ全体をボツにする
        if "\\" in full_name or "{" in full_name or "}" in full_name:
            # print(f"Validation failed for: {full_name}") # デバッグ用
            return [] # 1人でも失敗したら論文ごとスキップ

        author_affils = []
        if aid:
            for a in aid.split(','):
                a_id = a.strip()
                if a_id in id_to_org:
                    author_affils.append(id_to_org[a_id])
                else:
                    # IDが辞書にない＝紐付け失敗なので、これもエラー対象
                    return []
        
        # 所属が一つも見つからない著者がいた場合も、不完全なデータなのでスキップ
        if not author_affils:
            return []

        results.append({
            "name": full_name,
            "affiliations": author_affils
        })

    # 3. 現所属の処理
    present_match = re.search(r'\\presentaddress\{(.*?)\}', content, re.DOTALL)
    if present_match and results:
        clean_present = self.parser.clean_text(present_match.group(1))
        if "\\" in clean_present or "{" in clean_present:
            return [] # 現所属のパース失敗も許容しない
        if clean_present not in results[-1]["affiliations"]:
            results[-1]["affiliations"].append(clean_present)

    # 全ての著者が完璧に抽出できた場合のみ、結果を返す
    return results