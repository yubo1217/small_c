"""
parser.py — Small-C 語法分析器（Parser）與抽象語法樹（AST）
=============================================================
本模組負責兩項工作：

  1. 定義 AST 節點類別
     將 Small-C 的各種語法結構（運算式、陳述式、宣告、函式定義）
     表示為 Python 物件的樹狀結構，供後續直譯器（Interpreter）走訪執行。

  2. 實作遞迴下降語法分析器（Recursive Descent Parser）
     從 Lexer 產生的 Token 串流，依據 Small-C 文法規則，
     建構並回傳代表整份程式的 AST。

整體流程：

  Token 串流（來自 Lexer）
      │
      ▼
  Parser.parse()
      │
      ▼
  Program（AST 根節點）
      │
      ├── FuncDef / VarDecl / ArrayDecl ...
      │       └── Block → [Stmt, ...]
      │                       └── Expr → BinOp / Call / Assignment ...
      ▼
  完整 AST（供 Interpreter 使用）

支援的 Small-C 語法概要：
  - 型別：int、char、void（含指標 *）
  - 變數與陣列宣告（含初始化）
  - 函式定義與呼叫
  - 運算式：算術、位元、邏輯、比較、賦值（含複合賦值）、前置 ++/--
  - 控制流程：if/else、while、do-while、for、break、continue、return
"""

from lexer import Lexer


# ═══════════════════════════════════════════════════════════
# AST 節點基底類別
# ═══════════════════════════════════════════════════════════

class AST:
    """所有 AST 節點的抽象基底類別。"""


# ─────────────────────────────────────────────
# 運算式節點（Expressions）
# ─────────────────────────────────────────────

class Expr(AST):
    """所有運算式節點的基底類別。"""


class Number(Expr):
    """
    整數字面量，例如 42 或 0xFF。

    Attributes:
        value (int): 字面量的整數值。
    """
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Number({self.value})"


class Char(Expr):
    """
    字元字面量，例如 'a' 或 '\\n'。

    Attributes:
        value (str): 單一字元（Python str）。
    """
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Char('{self.value}')"


class StringLiteral(Expr):
    """
    字串字面量，例如 "hello"。

    Attributes:
        value (str): 字串內容。
    """
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"StringLiteral({self.value!r})"


class Identifier(Expr):
    """
    識別字（變數名或函式名），例如 x、count。

    Attributes:
        name (str): 識別字名稱。
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


class UnaryOp(Expr):
    """
    一元運算式，例如 -x、!flag、++i。

    Attributes:
        op      (str): 運算子類型，如 'MINUS'、'NOT'、'INC'。
        operand (Expr): 運算元。
    """
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.op}, {self.operand})"


class BinOp(Expr):
    """
    二元運算式，例如 a + b、x == y、p & q。

    Attributes:
        left  (Expr): 左側運算元。
        op    (str):  運算子類型，如 'PLUS'、'EQ'、'AND'。
        right (Expr): 右側運算元。
    """
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinOp({self.left}, {self.op}, {self.right})"


class AddressOf(Expr):
    """
    取址運算式，例如 &x。

    Attributes:
        target (Expr): 被取址的運算元（通常為識別字）。
    """
    def __init__(self, target):
        self.target = target

    def __repr__(self):
        return f"AddressOf({self.target})"


class Deref(Expr):
    """
    指標解參考運算式，例如 *ptr。

    Attributes:
        pointer (Expr): 被解參考的指標運算元。
    """
    def __init__(self, pointer):
        self.pointer = pointer

    def __repr__(self):
        return f"Deref({self.pointer})"


class Call(Expr):
    """
    函式呼叫運算式，例如 printf("hi", x)。

    Attributes:
        name (Expr): 被呼叫的函式（通常為 Identifier 節點）。
        args (list[Expr]): 傳入的引數列表（可為空）。
    """
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"Call({self.name}, {self.args})"


class ArrayAccess(Expr):
    """
    陣列索引存取運算式，例如 arr[i]。

    Attributes:
        array (Expr): 被存取的陣列（通常為 Identifier 節點）。
        index (Expr): 索引運算式。
    """
    def __init__(self, array, index):
        self.array = array
        self.index = index

    def __repr__(self):
        return f"ArrayAccess({self.array}, {self.index})"


class Assignment(Expr):
    """
    賦值運算式，支援一般賦值與複合賦值。
    例如 x = 5、x += 3、arr[i] *= 2。

    Attributes:
        target (Expr): 賦值目標（左值）。
        op     (str):  賦值運算子類型，如 'ASSIGN'、'ADD_ASSIGN'。
        value  (Expr): 賦值來源（右值）。
    """
    def __init__(self, target, op, value):
        self.target = target
        self.op = op
        self.value = value

    def __repr__(self):
        return f"Assignment({self.target}, {self.op}, {self.value})"


# ─────────────────────────────────────────────
# 陳述式節點（Statements）
# ─────────────────────────────────────────────

class Stmt(AST):
    """所有陳述式節點的基底類別。"""
    line = 0  # 節點在原始碼中的行號，由 Parser 在解析時設定


class VarDecl(Stmt):
    """
    變數宣告陳述式，例如 int x = 0; 或 char *p;。

    Attributes:
        var_type   (str):        型別名稱，如 'int'、'char'。
        name       (str):        變數名稱。
        value      (Expr|None):  初始化運算式；若未初始化則為 None。
        is_pointer (bool):       是否為指標型別（帶有 *）。
    """
    def __init__(self, var_type, name, value=None, is_pointer=False):
        self.var_type = var_type
        self.name = name
        self.value = value
        self.is_pointer = is_pointer

    def __repr__(self):
        return f"VarDecl({self.var_type}, {self.name}, {self.value}, pointer={self.is_pointer})"


class ArrayDecl(Stmt):
    """
    陣列宣告陳述式，例如 int arr[5]; 或 int arr[3] = {1, 2, 3};。

    Attributes:
        var_type (str):             元素型別名稱。
        name     (str):             陣列名稱。
        size     (Expr):            陣列大小運算式。
        value    (list[Expr]|None): 初始化元素列表；若未初始化則為 None。
    """
    def __init__(self, var_type, name, size, value=None):
        self.var_type = var_type
        self.name = name
        self.size = size
        self.value = value

    def __repr__(self):
        return f"ArrayDecl({self.var_type}, {self.name}, size={self.size}, value={self.value})"


class Block(Stmt):
    """
    由大括號包圍的複合陳述式，例如 { int x = 0; x++; }。
    也作為函式主體與控制流程分支的容器。

    Attributes:
        statements (list[Stmt]): 區塊內的陳述式列表（可為空）。
    """
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({self.statements})"


class Return(Stmt):
    """
    return 陳述式，例如 return x; 或 return;。

    Attributes:
        value (Expr|None): 回傳的運算式；void 函式的 return 為 None。
    """
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Return({self.value})"


class IfStmt(Stmt):
    """
    if / if-else 條件陳述式。

    Attributes:
        condition   (Expr):       條件運算式。
        then_branch (Block):      條件成立時執行的區塊。
        else_branch (Block|None): else 分支區塊；若無 else 則為 None。
    """
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def __repr__(self):
        return f"IfStmt({self.condition}, {self.then_branch}, {self.else_branch})"


class WhileStmt(Stmt):
    """
    while 迴圈陳述式，例如 while (x > 0) { ... }。

    Attributes:
        condition (Expr):  迴圈繼續條件。
        body      (Block): 迴圈主體。
    """
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"WhileStmt({self.condition}, {self.body})"


class DoWhileStmt(Stmt):
    """
    do-while 迴圈陳述式，例如 do { ... } while (x > 0);。
    與 while 的差別在於主體至少會執行一次。

    Attributes:
        body      (Block): 迴圈主體。
        condition (Expr):  迴圈繼續條件（在主體之後求值）。
    """
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition

    def __repr__(self):
        return f"DoWhileStmt({self.body}, {self.condition})"


class ForStmt(Stmt):
    """
    for 迴圈陳述式，例如 for (i = 0; i < n; i++) { ... }。
    三個子句皆可省略（省略 condition 視同永真）。

    Attributes:
        init      (Expr|None): 初始化運算式。
        condition (Expr|None): 繼續條件運算式。
        update    (Expr|None): 每輪結束後的更新運算式。
        body      (Block):     迴圈主體。
    """
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return f"ForStmt({self.init}, {self.condition}, {self.update}, {self.body})"


class BreakStmt(Stmt):
    """break 陳述式，跳出最近的迴圈。"""

    def __repr__(self):
        return "BreakStmt()"


class ContinueStmt(Stmt):
    """continue 陳述式，跳至最近迴圈的下一次迭代。"""

    def __repr__(self):
        return "ContinueStmt()"


class SwitchStmt(Stmt):
    """
    switch/case 條件分支陳述式。

    依據運算式的值，跳轉至對應的 case 標籤執行，
    若無匹配的 case 則執行 default 分支（若存在）。
    各分支依原始碼順序儲存，完整支援 fall-through（含 fall-through 至 default）。
    遇到 break 時跳出整個 switch。

    Attributes:
        expr  (Expr):        switch 的判斷運算式。
        items (list[tuple]): 依原始碼順序排列的分支列表，每個元素為
                             (value, stmts)，其中 value 為整數（case 值）
                             或 None（代表 default 分支），
                             stmts 為 list[Stmt]。
    """
    def __init__(self, expr, items):
        self.expr = expr
        self.items = items  # [(val_or_None, list[Stmt]), ...]

    def __repr__(self):
        return f"SwitchStmt({self.expr}, items={self.items})"


class FuncDef(Stmt):
    """
    函式定義，例如 int add(int a, int b) { return a + b; }。

    Attributes:
        ret_type   (str):         回傳型別名稱，如 'int'、'void'。
        name       (str):         函式名稱。
        params     (list[VarDecl]): 參數列表（每個參數以 VarDecl 表示）。
        body       (Block):       函式主體。
        is_pointer (bool):        回傳值是否為指標型別（帶有 *）。
    """
    def __init__(self, ret_type, name, params, body, is_pointer=False, line=0):
        self.ret_type = ret_type
        self.name = name
        self.params = params
        self.body = body
        self.is_pointer = is_pointer
        self.line = line  # 函式定義起始行號，供 FUNCS 指令顯示

    def __repr__(self):
        star = '*' if self.is_pointer else ''
        return f"FuncDef({self.ret_type}, {star}{self.name}, {self.params}, {self.body})"


# ─────────────────────────────────────────────
# 程式根節點（Program）
# ─────────────────────────────────────────────

class Program(AST):
    """
    整份程式的 AST 根節點，包含所有頂層宣告與定義。

    Attributes:
        decls (list[AST]): 頂層的函式定義、變數宣告、陣列宣告列表。
    """
    def __init__(self, decls):
        self.decls = decls

    def __repr__(self):
        return f"Program({self.decls})"


# ═══════════════════════════════════════════════════════════
# Parser：遞迴下降語法分析器
# ═══════════════════════════════════════════════════════════

class Parser:
    """
    Small-C 遞迴下降語法分析器（Recursive Descent Parser）。

    從 Lexer 產生的 Token 串流，依照 Small-C 的優先序文法規則，
    遞迴建構並回傳代表整份程式的 AST。

    運算式優先序（由低到高）：
      assignment > logic_or > logic_and > bit_or > bit_xor > bit_and
      > equality > rel > shift > add > mul > unary > primary

    Usage:
        parser = Parser(source_code)
        ast = parser.parse()
    """

    def __init__(self, text: str):
        """
        初始化語法分析器，將原始碼全部 tokenize 後存入列表備用。

        Args:
            text (str): 要分析的 Small-C 原始碼字串。
        """
        self.lexer = Lexer(text)
        self.tokens = list(self.lexer.tokenize())  # 一次性取得所有 Token，方便前瞻
        self.pos = 0
        self.current_token = self.tokens[self.pos]

    # ── 基礎游標操作與工具 ────────────────────────

    def eat(self, kind: str):
        """
        消耗目前 Token 並前進到下一個，若類型不符則拋出例外。

        同時處理 ERROR Token：只要遇到詞法錯誤，立即停止並回報。

        Args:
            kind (str): 預期的 Token 類型。

        Raises:
            Exception: Token 類型不符或遇到 ERROR Token 時。
        """
        if self.current_token.kind == "ERROR":
            raise Exception(
                f"Lexical error at line {self.current_token.line}: "
                f"{self.current_token.value}."
            )
        if self.current_token.kind == kind:
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
        else:
            raise Exception(
                f"Syntax error at line {self.current_token.line}: "
                f"unexpected token '{self.current_token.value}', "
                f"expected '{kind}'."
            )

    def peek(self):
        """
        預覽目前位置的下一個 Token（pos+1），不移動游標。

        Returns:
            Token | None: 下一個 Token，若已到結尾則回傳 None。
        """
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def peek2(self):
        """
        預覽目前位置往後第二個 Token（pos+2），用於判斷是否為函式定義。

        Returns:
            Token | None: pos+2 位置的 Token，若超出範圍則回傳 None。
        """
        if self.pos + 2 < len(self.tokens):
            return self.tokens[self.pos + 2]
        return None

    def is_type_token(self) -> bool:
        """
        判斷目前 Token 是否為型別關鍵字（int / char / void）。

        Returns:
            bool: 是型別關鍵字則為 True。
        """
        return self.current_token.kind in ("INT", "CHAR", "VOID")

    # ── 頂層入口 ─────────────────────────────────

    def parse(self) -> Program:
        """
        分析整份程式，回傳 AST 根節點。

        頂層結構只允許函式定義與全域變數宣告。

        Returns:
            Program: 包含所有頂層宣告的根節點。
        """
        decls = []
        while self.current_token.kind != "EOF":
            decls.append(self.declaration())
        return Program(decls)

    # ── 宣告（Declaration）────────────────────────

    def is_func_def(self) -> bool:
        """
        前瞻判斷目前位置是否為函式定義（而非變數宣告）。

        判斷邏輯：
          - 一般函式：TYPE IDENT LPAREN → int foo(
          - 指標回傳：TYPE MUL IDENT LPAREN → int *foo(

        Returns:
            bool: 若接下來是函式定義則為 True。
        """
        p1 = self.peek()
        p2 = self.peek2()
        if p1 and p1.kind == "MUL":
            # 指標回傳型別的函式定義：int *func(...)
            p3 = self.tokens[self.pos + 3] if self.pos + 3 < len(self.tokens) else None
            return p2 and p2.kind == "IDENT" and p3 and p3.kind == "LPAREN"
        # 一般函式定義：int func(...)
        return p1 and p1.kind == "IDENT" and p2 and p2.kind == "LPAREN"

    def declaration(self) -> AST:
        """
        解析一個頂層宣告：函式定義、變數宣告或陳述式。

        Returns:
            AST: FuncDef、VarDecl、ArrayDecl 或 Stmt 節點。
        """
        if self.is_type_token():
            if self.is_func_def():
                return self.func_def()
            else:
                return self.var_decl()
        return self.statement()

    # ── 陳述式（Statement）────────────────────────

    def statement(self) -> Stmt:
        """
        解析單一陳述式，根據目前 Token 分派到對應的解析方法。

        支援：if、while、for、do-while、return、break、continue、
              區塊（{ }）以及一般運算式陳述式（expr;）。

        Returns:
            Stmt: 對應的陳述式節點。
        """
        tok = self.current_token
        if tok.kind == "SWITCH":
            return self.switch_stmt()
        if tok.kind == "IF":
            return self.if_stmt()
        if tok.kind == "WHILE":
            return self.while_stmt()
        if tok.kind == "FOR":
            return self.for_stmt()
        if tok.kind == "DO":
            return self.do_while_stmt()
        if tok.kind == "RETURN":
            return self.return_stmt()
        if tok.kind == "BREAK":
            self.eat("BREAK")
            self.eat("SEMI")
            node = BreakStmt()
            node.line = tok.line
            return node
        if tok.kind == "CONTINUE":
            self.eat("CONTINUE")
            self.eat("SEMI")
            node = ContinueStmt()
            node.line = tok.line
            return node
        if tok.kind == "LBRACE":
            return self.block()
        # 一般運算式陳述式（以分號結尾）
        line = tok.line
        expr = self.expr()
        expr.line = line  # 動態設定行號供 TRACE 使用
        self.eat("SEMI")
        return expr

    # ── 區塊（Block）─────────────────────────────

    def block(self) -> Block:
        """
        解析由 { } 包圍的複合陳述式區塊。
        區塊內允許區域變數宣告與一般陳述式混合出現。

        Returns:
            Block: 包含區塊內所有陳述式的節點。
        """
        line = self.current_token.line
        self.eat("LBRACE")
        stmts = []
        while self.current_token.kind not in ("RBRACE", "EOF"):
            if self.is_type_token():
                stmts.append(self.var_decl())
            else:
                stmts.append(self.statement())
        self.eat("RBRACE")
        node = Block(stmts)
        node.line = line
        return node

    def block_or_stmt(self) -> Block:
        """
        解析控制流程的主體，允許帶大括號的區塊或單一陳述式。
        單一陳述式會被包裝成只含一個元素的 Block，方便直譯器統一處理。

        Returns:
            Block: 主體區塊節點。
        """
        if self.current_token.kind == "LBRACE":
            return self.block()
        return Block([self.statement()])

    # ── 宣告解析細節 ──────────────────────────────

    def var_decl(self) -> Stmt:
        """
        解析變數或陣列宣告陳述式。

        當識別字後緊跟 [ 時，轉交 array_decl() 處理；
        否則解析一般變數宣告（可帶初始值）。

        Returns:
            VarDecl | ArrayDecl: 對應的宣告節點。
        """
        line = self.current_token.line  # 記錄型別關鍵字的行號
        var_type = self.current_token.value
        self.eat(self.current_token.kind)  # 消耗型別關鍵字（INT / CHAR / VOID）

        is_pointer = False
        if self.current_token.kind == "MUL":
            is_pointer = True
            self.eat("MUL")

        name = self.current_token.value
        self.eat("IDENT")

        if self.current_token.kind == "LBRACKET":
            return self.array_decl(var_type, name, line)

        value = None
        if self.current_token.kind == "ASSIGN":
            self.eat("ASSIGN")
            value = self.expr()

        self.eat("SEMI")
        node = VarDecl(var_type, name, value, is_pointer)
        node.line = line
        return node

    def array_decl(self, var_type: str, name: str, line: int = 0) -> ArrayDecl:
        """
        解析陣列宣告，包含可選的大括號初始化列表。
        呼叫前提：已解析完型別與名稱，目前 Token 為 [。

        Args:
            var_type (str): 陣列元素的型別名稱。
            name     (str): 陣列名稱。
            line     (int): 宣告起始行號（由 var_decl 傳入）。

        Returns:
            ArrayDecl: 陣列宣告節點。
        """
        self.eat("LBRACKET")
        size = self.expr()
        self.eat("RBRACKET")

        value = None
        if self.current_token.kind == "ASSIGN":
            self.eat("ASSIGN")
            self.eat("LBRACE")
            value = []
            if self.current_token.kind != "RBRACE":
                value.append(self.expr())
                while self.current_token.kind == "COMMA":
                    self.eat("COMMA")
                    value.append(self.expr())
            self.eat("RBRACE")

        self.eat("SEMI")
        node = ArrayDecl(var_type, name, size, value)
        node.line = line
        return node

    def func_def(self) -> FuncDef:
        """
        解析函式定義，包含回傳型別、名稱、參數列表與主體區塊。

        Returns:
            FuncDef: 函式定義節點（含行號，供 FUNCS 指令顯示）。
        """
        line = self.current_token.line  # 記錄函式定義起始行號
        ret_type = self.current_token.value
        self.eat(self.current_token.kind)  # 消耗回傳型別關鍵字

        is_pointer = False
        if self.current_token.kind == "MUL":
            is_pointer = True
            self.eat("MUL")

        name = self.current_token.value
        self.eat("IDENT")
        self.eat("LPAREN")

        params = []
        if self.current_token.kind != "RPAREN":
            params.append(self.param())
            while self.current_token.kind == "COMMA":
                self.eat("COMMA")
                params.append(self.param())

        self.eat("RPAREN")
        body = self.block()
        return FuncDef(ret_type, name, params, body, is_pointer, line)

    def param(self) -> VarDecl:
        """
        解析函式定義中的單一參數，以 VarDecl 節點表示。

        Returns:
            VarDecl: 參數宣告節點（value 固定為 None）。
        """
        var_type = self.current_token.value
        self.eat(self.current_token.kind)  # 消耗型別關鍵字

        is_pointer = False
        if self.current_token.kind == "MUL":
            is_pointer = True
            self.eat("MUL")

        name = self.current_token.value
        self.eat("IDENT")
        return VarDecl(var_type, name, None, is_pointer)

    # ── 控制流程陳述式 ────────────────────────────
    def switch_stmt(self) -> SwitchStmt:
        """
        解析 switch/case 條件分支陳述式。

        語法：
          switch ( expr ) {
              case <整數或字元常數> : <陳述式>*
              ...
              default : <陳述式>*   （可省略，可出現在任意位置）
          }

        各分支依原始碼順序儲存於 items 列表，完整支援 fall-through
        （含 fall-through 至 default）。case 值可為整數字面量（NUMBER）
        或字元字面量（CHAR）。遇到 break 時由直譯器負責跳出整個 switch。
        """
        line = self.current_token.line
        self.eat("SWITCH")
        self.eat("LPAREN")
        expr = self.expr()
        self.eat("RPAREN")
        self.eat("LBRACE")

        items = []  # [(val_or_None, [stmts]), ...] 依原始碼順序排列

        while self.current_token.kind not in ("RBRACE", "EOF"):
            if self.current_token.kind == "CASE":
                self.eat("CASE")
                # case 值：支援整數字面量與字元字面量
                if self.current_token.kind == "NUMBER":
                    val = self.current_token.value
                    self.eat("NUMBER")
                elif self.current_token.kind == "CHAR":
                    val = ord(self.current_token.value)
                    self.eat("CHAR")
                else:
                    raise Exception(
                        f"Syntax error at line {self.current_token.line}: "
                        f"case value must be an integer or character constant."
                    )
                self.eat("COLON")
                stmts = []
                while self.current_token.kind not in ("CASE", "DEFAULT", "RBRACE", "EOF"):
                    if self.is_type_token():
                        stmts.append(self.var_decl())
                    else:
                        stmts.append(self.statement())
                items.append((val, stmts))

            elif self.current_token.kind == "DEFAULT":
                self.eat("DEFAULT")
                self.eat("COLON")
                stmts = []
                while self.current_token.kind not in ("CASE", "DEFAULT", "RBRACE", "EOF"):
                    if self.is_type_token():
                        stmts.append(self.var_decl())
                    else:
                        stmts.append(self.statement())
                items.append((None, stmts))  # None 代表 default 分支

            else:
                raise Exception(
                    f"Syntax error at line {self.current_token.line}: "
                    f"expected 'case' or 'default' in switch statement."
                )

        self.eat("RBRACE")
        node = SwitchStmt(expr, items)
        node.line = line
        return node

    def if_stmt(self) -> IfStmt:
        """解析 if / if-else 條件陳述式。"""
        line = self.current_token.line
        self.eat("IF")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        then_branch = self.block_or_stmt()
        else_branch = None
        if self.current_token.kind == "ELSE":
            self.eat("ELSE")
            else_branch = self.block_or_stmt()
        node = IfStmt(cond, then_branch, else_branch)
        node.line = line
        return node

    def while_stmt(self) -> WhileStmt:
        """解析 while 迴圈陳述式。"""
        line = self.current_token.line
        self.eat("WHILE")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        body = self.block_or_stmt()
        node = WhileStmt(cond, body)
        node.line = line
        return node

    def do_while_stmt(self) -> DoWhileStmt:
        """解析 do-while 迴圈陳述式。"""
        line = self.current_token.line
        self.eat("DO")
        body = self.block_or_stmt()
        self.eat("WHILE")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        self.eat("SEMI")
        node = DoWhileStmt(body, cond)
        node.line = line
        return node

    def for_stmt(self) -> ForStmt:
        """
        解析 for 迴圈陳述式。
        三個子句（init ; condition ; update）皆可省略。
        """
        line = self.current_token.line
        self.eat("FOR")
        self.eat("LPAREN")

        init = None
        if self.current_token.kind != "SEMI":
            init = self.expr()
        self.eat("SEMI")

        condition = None
        if self.current_token.kind != "SEMI":
            condition = self.expr()
        self.eat("SEMI")

        update = None
        if self.current_token.kind != "RPAREN":
            update = self.expr()
        self.eat("RPAREN")

        body = self.block_or_stmt()
        node = ForStmt(init, condition, update, body)
        node.line = line
        return node

    def return_stmt(self) -> Return:
        """解析 return 陳述式，回傳值可省略（void 函式）。"""
        line = self.current_token.line
        self.eat("RETURN")
        val = None
        if self.current_token.kind != "SEMI":
            val = self.expr()
        self.eat("SEMI")
        node = Return(val)
        node.line = line
        return node

    # ── 運算式（Expressions）── 遞迴下降，由低到高優先序 ──

    def expr(self) -> Expr:
        """運算式入口，委派給最低優先序的 assignment()。"""
        return self.assignment()

    def assignment(self) -> Expr:
        """
        解析賦值運算式（右結合）。

        文法：logic_or (ASSIGN | ADD_ASSIGN | ...) assignment
              | logic_or

        支援：= += -= *= /= %=
        """
        node = self.logic_or()
        if self.current_token.kind in (
            "ASSIGN", "ADD_ASSIGN", "SUB_ASSIGN",
            "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN"
        ):
            op = self.current_token.kind
            self.eat(op)
            value = self.assignment()   # 右結合：遞迴呼叫自身
            return Assignment(node, op, value)
        return node

    def logic_or(self) -> Expr:
        """解析邏輯 OR 運算式（||），左結合。"""
        node = self.logic_and()
        while self.current_token.kind == "OR":
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.logic_and())
        return node

    def logic_and(self) -> Expr:
        """解析邏輯 AND 運算式（&&），左結合。"""
        node = self.bit_or()
        while self.current_token.kind == "AND":
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_or())
        return node

    def bit_or(self) -> Expr:
        """解析位元 OR 運算式（|），左結合。"""
        node = self.bit_xor()
        while self.current_token.kind == "BIT_OR":
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_xor())
        return node

    def bit_xor(self) -> Expr:
        """解析位元 XOR 運算式（^），左結合。"""
        node = self.bit_and()
        while self.current_token.kind == "BIT_XOR":
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_and())
        return node

    def bit_and(self) -> Expr:
        """解析位元 AND 運算式（&），左結合。"""
        node = self.equality()
        while self.current_token.kind == "BIT_AND":
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.equality())
        return node

    def equality(self) -> Expr:
        """解析相等比較運算式（== !=），左結合。"""
        node = self.rel()
        while self.current_token.kind in ("EQ", "NEQ"):
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.rel())
        return node

    def rel(self) -> Expr:
        """解析關係比較運算式（< > <= >=），左結合。"""
        node = self.shift()
        while self.current_token.kind in ("LT", "GT", "LTE", "GTE"):
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.shift())
        return node

    def shift(self) -> Expr:
        """解析位元位移運算式（<< >>），左結合。"""
        node = self.add()
        while self.current_token.kind in ("LSHIFT", "RSHIFT"):
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.add())
        return node

    def add(self) -> Expr:
        """解析加減法運算式（+ -），左結合。"""
        node = self.mul()
        while self.current_token.kind in ("PLUS", "MINUS"):
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.mul())
        return node

    def mul(self) -> Expr:
        """解析乘除餘數運算式（* / %），左結合。"""
        node = self.unary()
        while self.current_token.kind in ("MUL", "DIV", "MOD"):
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.unary())
        return node

    def unary(self) -> Expr:
        """
        解析一元前置運算式（右結合）。

        支援：
          + - ! ~           → UnaryOp
          * （解參考）       → Deref
          & （取址）         → AddressOf
          ++ -- （前置遞增減）→ UnaryOp
        """
        tok = self.current_token
        if tok.kind in ("PLUS", "MINUS", "NOT", "BIT_NOT"):
            self.eat(tok.kind)
            return UnaryOp(tok.kind, self.unary())
        if tok.kind == "MUL":
            self.eat("MUL")
            return Deref(self.unary())
        if tok.kind == "BIT_AND":
            self.eat("BIT_AND")
            return AddressOf(self.unary())
        if tok.kind in ("INC", "DEC"):
            self.eat(tok.kind)
            return UnaryOp(tok.kind, self.unary())
        return self.primary()

    def primary(self) -> Expr:
        """
        解析最高優先序的基本運算式（primary expression）。

        處理：
          NUMBER            → Number 節點
          CHAR              → Char 節點
          STRING            → StringLiteral 節點
          IDENT             → Identifier 節點
          IDENT ( args )    → Call 節點（函式呼叫）
          IDENT [ index ]   → ArrayAccess 節點（陣列存取）
          ( expr )          → 括號運算式（回傳內部節點）

        Raises:
            Exception: 遇到無法識別的 Token 時。
        """
        tok = self.current_token

        if tok.kind == "NUMBER":
            self.eat("NUMBER")
            return Number(tok.value)

        if tok.kind == "CHAR":
            self.eat("CHAR")
            return Char(tok.value)

        if tok.kind == "STRING":
            self.eat("STRING")
            return StringLiteral(tok.value)

        if tok.kind == "IDENT":
            name = tok.value
            self.eat("IDENT")
            node = Identifier(name)

            if self.current_token.kind == "LPAREN":
                # 函式呼叫：IDENT ( arg, ... )
                self.eat("LPAREN")
                args = []
                if self.current_token.kind != "RPAREN":
                    args.append(self.expr())
                    while self.current_token.kind == "COMMA":
                        self.eat("COMMA")
                        args.append(self.expr())
                self.eat("RPAREN")
                node = Call(node, args)

            if self.current_token.kind == "LBRACKET":
                # 陣列索引存取：IDENT [ index ]
                self.eat("LBRACKET")
                index = self.expr()
                self.eat("RBRACKET")
                node = ArrayAccess(node, index)

            return node

        if tok.kind == "LPAREN":
            # 括號運算式：( expr )
            self.eat("LPAREN")
            node = self.expr()
            self.eat("RPAREN")
            return node

        raise Exception(
            f"Syntax error at line {tok.line}: unexpected token '{tok.value}'."
        )