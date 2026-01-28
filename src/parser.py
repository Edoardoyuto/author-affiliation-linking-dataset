import re

class LatexParser:

    @staticmethod
    def strip_comments(text):
        """
        LaTeXのコメント（% ...）を削除する。
        エスケープされたパーセント記号（\%）は保護して、本物のコメントだけを消す。
        """
        # 1. \% を一時的に特殊な文字列に退避
        text = text.replace(r'\%', '___ESCAPED_PERCENT___')
        
        # 2. % から行末までを削除。改行文字 (\n) は構文維持のため残す。
        text = re.sub(r'%.*', '', text)
        
        # 3. 退避させていた \% を元に戻す
        text = text.replace('___ESCAPED_PERCENT___', '%')
        
        return text

    @staticmethod
    def clean_text(text):
        """
        LaTeX特有の装飾や記法を掃除し、純粋なテキストにする。
        """
        if not text: return ""

        # 1. 装飾系コマンドの除去: \textbf{...} -> ...
        # {}の中身だけを残す処理
        text = re.sub(r'\\[a-z]+\{([^{}]+)\}', r'\1', text)
        
        # 2. 独立したフォント指定などの除去: {\rm ...} -> ...
        text = re.sub(r'\{(?:\\[a-z]+\s+)?([^{}]+)\}', r'\1', text)

        # 3. アクセント記号の簡易置換 (代表的なもの)
        accents = {
            r"\\'a": "á", r"\\'e": "é", r"\\'i": "í", r"\\'o": "ó", r"\\'u": "ú",
            r'\\"a': "ä", r'\\"e': "ë", r'\\"i': "ï", r'\\"o': "ö", r'\\"u': "ü",
            r"\\`a": "à", r"\\`e": "è",
            r"\\^a": "â", r"\\^e": "ê",
            r"\\~n": "ñ",
        }
        for tex, uni in accents.items():
            text = text.replace(tex, uni)

        # 4. エスケープ文字の復元: \& -> &, \_ -> _
        text = text.replace(r'\&', '&').replace(r'\_', '_').replace(r'\$', '$').replace(r'\%', '%')

        # 5. 改行と余計な空白の掃除
        text = text.replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()