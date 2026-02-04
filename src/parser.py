import re

class LatexParser:
    @staticmethod
    def strip_comments(text):
        # 現状のロジックで概ねOKですが、改行の扱いに注意
        text = text.replace(r'\%', '___ESCAPED_PERCENT___')
        # 改行を消さずにコメントだけ消す（構造維持）
        text = re.sub(r'%.*', '', text)
        text = text.replace('___ESCAPED_PERCENT___', '%')
        return text

    @staticmethod
    def clean_text(text):
        if not text: return ""

        # 1. 徹底的なコマンド除去 (再帰的なネストに対応)
        # 非常にシンプルな戦略：コマンド \cmd{...} や \cmd を消すのではなく、
        # 「中身」を救出しながら外側を剥ぐ
        for _ in range(3): # 3階層までのネストを許容
            text = re.sub(r'\\[a-zA-Z]+\{(.*?)\}', r'\1', text)
            text = re.sub(r'\{(.*?)\}', r'\1', text)

        # 2. 数学モードの除去（ベンチマークの天敵：肩番号など）
        # $...$ または \(...\) を完全に消去するか、中身だけにするか
        # 著者所属の場合、これらはIDなので「消去」が正解
        text = re.sub(r'\$.*?\$', '', text)
        text = re.sub(r'\\\(.*?\\\)', '', text)

        # 3. 特殊記号の置換
        text = text.replace('~', ' ')      # 改行不可スペース
        text = text.replace('--', '-')     # エアダッシュ
        text = text.replace('---', '-')    # エムダッシュ
        text = text.replace('``', '"').replace("''", '"') # 引用符

        # 4. エスケープ文字の復元（範囲を拡大）
        escapes = {
            r'\&': '&', r'\_': '_', r'\$': '$', r'\%': '%', 
            r'\#': '#', r'\{': '{', r'\}': '}', r'\dag': '', r'\ddag': ''
        }
        for tex, plain in escapes.items():
            text = text.replace(tex, plain)

        # 5. アクセント記号（以前のロジックを維持しつつ拡張）
        # 実際にはもっと多いですが、主要なものをカバー
        text = re.sub(r"\\'[AaEeIiOoUu]", lambda m: m.group(0)[-1], text) # 簡易化

        # 6. 最終的な空白掃除
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()