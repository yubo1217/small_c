"""
lexer.py — Small-C 詞法分析器（Lexer）
======================================
本模組負責將 Small-C 原始碼字串轉換為一系列 Token（詞法單元），
供後續的語法分析器（Parser）使用。整體流程如下：

  原始碼字串
      │
      ▼
  preprocess()        ── 展開 #define 巨集
      │
      ▼
  Lexer.tokenize()    ── 逐字元掃描，產生 Token 串流
      │
      ▼
  Token 串流（供 Parser 消費）
"""


# ─────────────────────────────────────────────
# Token：詞法單元的資料容器
# ─────────────────────────────────────────────

class Token:
    """
    代表一個詞法單元（Token）。

    Attributes:
        kind  (str): Token 的類型，例如 'INT'、'IDENT'、'NUMBER'、'EOF'。
        value      : Token 的值。數字為 int，字元/字串為 str，關鍵字與運算子通常也是 str。
        line  (int): 該 Token 出現的原始碼行號（從 1 開始），用於錯誤回報。
    """

    def __init__(self, kind, value, line):
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.kind}, {self.value}, {self.line})"


# ─────────────────────────────────────────────
# 前處理：展開 #define 巨集
# ─────────────────────────────────────────────

def preprocess(source: str, defines: dict = None) -> str:
    """
    對原始碼進行簡易的前處理，支援無參數的 #define 巨集展開。

    處理步驟：
      1. 逐行掃描，找出所有 `#define NAME VALUE` 定義並記錄在字典中。
      2. 移除含有 #define 的行。
      3. 以手工分詞的方式逐字元掃描剩餘原始碼，將完整匹配的識別字
         替換為對應的巨集值，避免誤觸其他識別字中的子字串。

    Args:
        source  (str):        完整的原始碼字串。
        defines (dict | None): 跨呼叫共享的巨集字典（互動模式用）；
                               傳入 None 時建立本地字典（批次模式）。

    Returns:
        str: 展開巨集後的原始碼字串。

    Note:
        不支援帶參數的函式型巨集（例如 `#define MAX(a,b) ...`）。
        替換採用識別字邊界比對：只有獨立出現的完整識別字才會被替換，
        不會誤觸包含在其他識別字中的子字串（例如 #define N 8 不會
        影響 count、int 等含有字母 n 的識別字）。
    """
    if defines is None:
        defines = {}
    lines = []

    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#define'):
            # 移除行尾的單行註解（// ...），避免 len(parts) > 3 而被靜默忽略
            comment_idx = stripped.find('//')
            if comment_idx != -1:
                stripped = stripped[:comment_idx].strip()
            parts = stripped.split()
            if len(parts) == 3:
                defines[parts[1]] = parts[2]   # 記錄巨集名稱 → 取代值
            lines.append('')   # 保留空行，維持後續 Token 的行號與 buffer 一致
        else:
            lines.append(line)

    result = '\n'.join(lines)

    if not defines:
        return result

    # 逐字元掃描，以手工分詞方式展開巨集。重複最多 10 次直到結果穩定，
    # 以支援 #define A B / #define B 100 這類鏈式巨集展開。
    for _ in range(10):
        out = []
        i = 0
        in_str = False    # 是否在雙引號字串內
        in_char = False   # 是否在單引號字元字面量內
        while i < len(result):
            c = result[i]
            if c == '\\' and (in_str or in_char):
                # 跳脫序列：原樣輸出兩個字元，不改變引號狀態
                out.append(c)
                i += 1
                if i < len(result):
                    out.append(result[i])
                    i += 1
            elif c == '"' and not in_char:
                in_str = not in_str
                out.append(c)
                i += 1
            elif c == "'" and not in_str:
                in_char = not in_char
                out.append(c)
                i += 1
            elif (c.isalpha() or c == '_') and not in_str and not in_char:
                # 識別字：僅在字串／字元字面量外才做巨集替換
                j = i
                while j < len(result) and (result[j].isalnum() or result[j] == '_'):
                    j += 1
                word = result[i:j]
                out.append(defines.get(word, word))  # 有對應巨集則替換，否則原樣保留
                i = j
            else:
                out.append(c)
                i += 1
        new_result = ''.join(out)
        if new_result == result:
            break
        result = new_result

    return result


# ─────────────────────────────────────────────
# Lexer：詞法分析器主體
# ─────────────────────────────────────────────

class Lexer:
    """
    Small-C 詞法分析器。

    逐字元讀取原始碼，識別並產生以下類別的 Token：
      - 關鍵字：int、char、void、if、else、while、for、do、break、continue、return、switch、case、default
      - 識別字（IDENT）：變數名、函式名等
      - 數字字面量（NUMBER）：十進位整數或 0x 開頭的十六進位整數
      - 字元字面量（CHAR）：單引號包圍的單一字元，支援跳脫序列
      - 字串字面量（STRING）：雙引號包圍的字串，支援跳脫序列
      - 運算子：單字元與雙字元運算子（含複合賦值、位元運算等）
      - 符號：分號、逗號、括號、大括號、中括號
      - EOF：原始碼結束
      - ERROR：無法識別的字元或格式錯誤的字面量

    Usage:
        lexer = Lexer(source_code)
        for token in lexer.tokenize():
            print(token)
    """

    # 保留字（關鍵字）對應表：原始碼文字 → Token 類型
    KEYWORDS = {
        'int': "INT", 'char': "CHAR", 'void': "VOID",
        'if': 'IF', 'else': 'ELSE',
        'while': "WHILE", 'for': 'FOR', 'do': 'DO',
        'break': "BREAK", 'continue': 'CONTINUE',
        'return': 'RETURN',
        'switch': 'SWITCH', 'case': 'CASE', 'default': 'DEFAULT',
    }

    # 單字元運算子對應表
    SINGLE_OPS = {
        '!': 'NOT',   '&': 'BIT_AND', '~': 'BIT_NOT',
        '^': 'BIT_XOR', '|': 'BIT_OR',
        '+': 'PLUS',  '-': 'MINUS',   '*': 'MUL',
        '/': 'DIV',   '%': 'MOD',     '=': 'ASSIGN',
        '>': 'GT',    '<': 'LT',
        ':': 'COLON',
    }

    # 雙字元運算子對應表（優先於單字元運算子進行匹配）
    DOUBLE_OPS = {
        '++': 'INC',    '--': 'DEC',
        '<<': 'LSHIFT', '>>': 'RSHIFT',
        '&&': 'AND',    '||': 'OR',
        '==': 'EQ',     '!=': 'NEQ',
        '>=': 'GTE',    '<=': 'LTE',
        '+=': 'ADD_ASSIGN', '-=': 'SUB_ASSIGN',
        '*=': 'MUL_ASSIGN', '/=': 'DIV_ASSIGN',
        '%=': 'MOD_ASSIGN',
    }

    # 分隔符號對應表
    SYMBOLS = {
        ';': 'SEMI',    ',': 'COMMA',
        '(': 'LPAREN',  ')': 'RPAREN',
        '{': 'LBRACE',  '}': 'RBRACE',
        '[': 'LBRACKET', ']': 'RBRACKET',
    }

    def __init__(self, text: str):
        """
        初始化詞法分析器。

        Args:
            text (str): 要分析的原始碼字串（建議先經過 preprocess() 處理）。
        """
        self.text = text
        self.pos = 0                                        # 目前讀取位置（字元索引）
        self.line = 1                                       # 目前行號
        self.current_char = self.text[0] if text else None  # 目前字元

    # ── 基礎游標操作 ─────────────────────────────

    def _advance(self):
        """
        將游標向前移動一個字元。
        若遇到換行符，行號加一；到達字串結尾後 current_char 設為 None。
        """
        if self.current_char == '\n':
            self.line += 1
        self.pos += 1
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None

    def _peek(self):
        """
        預覽下一個字元（不移動游標）。

        Returns:
            str | None: 下一個字元，若已到達結尾則回傳 None。
        """
        peek_pos = self.pos + 1
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]

    # ── 空白與註解跳過 ────────────────────────────

    def _skip_whitespace_and_comments(self):
        """
        跳過空白字元（空格、Tab、換行）以及 C 風格的單行與多行註解。

          - 單行註解：從 // 到行尾。
          - 多行註解：從 /* 到 */，支援跨行，未閉合時回傳 ERROR Token。

        Returns:
            Token | None: 若多行註解未正確閉合，回傳 ERROR Token；否則回傳 None。
        """
        while self.current_char is not None:
            if self.current_char in ' \t\n':
                self._advance()

            elif self.current_char == '/' and self._peek() == '/':
                # 單行註解：跳至行尾
                while self.current_char is not None and self.current_char != '\n':
                    self._advance()

            elif self.current_char == '/' and self._peek() == '*':
                # 多行註解：跳過 /* ... */
                self._advance()  # 跳過 '/'
                self._advance()  # 跳過 '*'
                while self.current_char is not None:
                    if self.current_char == '*' and self._peek() == '/':
                        self._advance()  # 跳過 '*'
                        self._advance()  # 跳過 '/'
                        break
                    self._advance()
                else:
                    # 掃描到結尾都未找到 */，屬於語法錯誤
                    return Token("ERROR", "Unterminated comment", self.line)
            else:
                break  # 遇到非空白、非註解的有效字元，停止跳過

        return None

    # ── 字面量解析 ────────────────────────────────

    def _character(self):
        """
        解析單引號包圍的字元字面量，例如 'a'、'\\n'。

        支援跳脫序列：\\n \\t \\0 \\' \\" \\\\

        Returns:
            Token: kind='CHAR'，value 為對應的 Python 字元；
                   格式錯誤時回傳 kind='ERROR' 的 Token。
        """
        start_line = self.line
        self._advance()  # 跳過開頭的 '

        if self.current_char is None:
            return Token("ERROR", "Unterminated char", start_line)

        if self.current_char == '\\':
            # 處理跳脫序列
            self._advance()
            if self.current_char is None:
                return Token("ERROR", "Unterminated char escape", start_line)
            escapes = {"n": "\n", "t": "\t", "0": "\0", "'": "'", '"': '"', "\\": "\\"}
            if self.current_char in escapes:
                value = escapes[self.current_char]
            else:
                return Token("ERROR", f"Invalid escape '\\{self.current_char}'", start_line)
        else:
            value = self.current_char

        self._advance()

        if self.current_char != "'":
            return Token("ERROR", "Unterminated char literal", start_line)

        self._advance()  # 跳過結尾的 '
        return Token("CHAR", value, start_line)

    def _string_literal(self):
        """
        解析雙引號包圍的字串字面量，例如 "hello\\n"。

        支援跳脫序列：\\n \\t \\0 \\' \\" \\\\
        字串中不允許換行符（需使用 \\n 表示）。

        Returns:
            Token: kind='STRING'，value 為解析後的 Python 字串；
                   格式錯誤時回傳 kind='ERROR' 的 Token。
        """
        value = ""
        start_line = self.line
        self._advance()  # 跳過開頭的 "

        while self.current_char is not None:
            if self.current_char == '"':
                self._advance()  # 跳過結尾的 "
                return Token("STRING", value, start_line)

            if self.current_char == '\n':
                return Token("ERROR", "Newline in char/string", start_line)

            if self.current_char == '\\':
                # 處理跳脫序列
                self._advance()
                if self.current_char is None:
                    return Token("ERROR", "Unterminated string escape", start_line)
                escapes = {"n": "\n", "t": "\t", "0": "\0", "'": "'", '"': '"', "\\": "\\"}
                if self.current_char in escapes:
                    value += escapes[self.current_char]
                else:
                    return Token("ERROR", f"Invalid escape '\\{self.current_char}'", start_line)
            else:
                value += self.current_char

            self._advance()

        return Token("ERROR", "Unterminated string literal", start_line)

    def _number(self):
        """
        解析整數字面量，支援十進位與十六進位（0x / 0X 前綴）。

        Examples:
            42     → Token('NUMBER', 42, ...)
            0xFF   → Token('NUMBER', 255, ...)

        Returns:
            Token: kind='NUMBER'，value 為 Python int；
                   格式錯誤（如 0x 後無合法數字）時回傳 kind='ERROR' 的 Token。
        """
        num_str = ''
        start_line = self.line

        # 十六進位整數
        if self.current_char == '0' and (self._peek() in ['x', 'X']):
            num_str += self.current_char
            self._advance()  # 跳過 '0'
            num_str += self.current_char
            self._advance()  # 跳過 'x'/'X'

            if self.current_char is None or not (
                self.current_char.isdigit() or 'a' <= self.current_char.lower() <= 'f'
            ):
                return Token("ERROR", "Invalid hex literal", start_line)

            while self.current_char is not None and (
                self.current_char.isdigit() or 'a' <= self.current_char.lower() <= 'f'
            ):
                num_str += self.current_char
                self._advance()

            return Token('NUMBER', int(num_str, 16), start_line)

        # 十進位整數
        while self.current_char is not None and self.current_char.isdigit():
            num_str += self.current_char
            self._advance()

        if not num_str:
            return Token("ERROR", "Expected number", start_line)

        return Token('NUMBER', int(num_str), start_line)

    def _identifier(self):
        """
        解析識別字或關鍵字。

        識別字由字母、底線開頭，後續可接字母、數字、底線。
        若識別到的字串屬於保留字（KEYWORDS），則回傳對應的關鍵字 Token；
        否則回傳 IDENT Token。

        Returns:
            Token: kind 為關鍵字類型（如 'INT'、'IF'）或 'IDENT'，
                   value 為識別字字串。
        """
        start_line = self.line
        id_str = ''

        while self.current_char is not None and (
            self.current_char.isalnum() or self.current_char == '_'
        ):
            id_str += self.current_char
            self._advance()

        kind = self.KEYWORDS.get(id_str, 'IDENT')
        return Token(kind, id_str, start_line)

    # ── 主要 Token 取得介面 ───────────────────────

    def _get_next_token(self) -> Token:
        """
        從目前游標位置取得下一個 Token。

        Token 識別優先順序：
          1. 跳過空白與註解
          2. 字元字面量（' ... '）
          3. 字串字面量（" ... "）
          4. 雙字元運算子（== != <= >= ++ -- 等）
          5. 單字元運算子（+ - * / 等）
          6. 分隔符號（; , ( ) { } [ ]）
          7. 數字字面量（十進位 / 十六進位）
          8. 識別字或關鍵字
          9. 無法識別的字元 → ERROR Token

        Returns:
            Token: 下一個詞法單元；到達原始碼結尾回傳 EOF Token。
        """
        while self.current_char is not None:
            # 跳過空白與註解；若多行註解未閉合，直接回傳錯誤
            error_token = self._skip_whitespace_and_comments()
            if error_token is not None:
                return error_token

            if self.current_char is None:
                return Token('EOF', None, self.line)

            if self.current_char == '\'':
                return self._character()

            if self.current_char == '\"':
                return self._string_literal()

            # 嘗試匹配雙字元運算子（優先於單字元運算子）
            next_char = self._peek()
            two_char = self.current_char + (next_char if next_char is not None else '')
            if two_char in self.DOUBLE_OPS:
                token = Token(self.DOUBLE_OPS[two_char], two_char, self.line)
                self._advance()
                self._advance()
                return token

            if self.current_char in self.SINGLE_OPS:
                token = Token(self.SINGLE_OPS[self.current_char], self.current_char, self.line)
                self._advance()
                return token

            if self.current_char in self.SYMBOLS:
                token = Token(self.SYMBOLS[self.current_char], self.current_char, self.line)
                self._advance()
                return token

            if '0' <= self.current_char <= '9':
                return self._number()

            if self.current_char.isalpha() or self.current_char == '_':
                return self._identifier()

            # 其他無法識別的字元
            err_line = self.line
            err_char = self.current_char
            self._advance()
            return Token("ERROR", f"Unknown character '{err_char}'", err_line)

        return Token('EOF', None, self.line)

    def tokenize(self):
        """
        將整份原始碼轉換為 Token 串流的產生器（Generator）。

        持續呼叫 get_next_token() 並 yield 每個 Token，
        直到取得 EOF Token 為止（EOF 本身也會被 yield）。

        Yields:
            Token: 依序產生的詞法單元，最後一個必定是 EOF Token。

        Usage:
            for token in lexer.tokenize():
                print(token)
        """
        while True:
            token = self._get_next_token()
            yield token
            if token.kind == 'EOF':
                break