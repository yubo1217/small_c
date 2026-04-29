"""
interpreter.py — Small-C 樹狀走訪直譯器（Tree-Walking Interpreter）
====================================================================
本模組負責走訪 Parser 產生的 AST，逐節點執行 Small-C 程式。

執行流程：
  1. execute()           掃描頂層宣告，收集函式定義與全域變數，再呼叫 main()。
  2. execute_interactive() 互動模式，直接執行單行或片段程式碼，不需要 main()。
  3. exec_stmt()         遞迴執行各種陳述式節點。
  4. eval_expr()         遞迴求值各種運算式節點，回傳整數結果。

控制流程實作：
  break、continue、return 均以 Python 例外（BreakException、ContinueException、
  ReturnException）傳遞，由對應的迴圈或函式呼叫點捕捉處理。

與其他模組的關係：
  - Parser    → 提供 AST 節點定義
  - Memory    → 所有數值的實際儲存與讀寫
  - SymbolTable → 管理變數名稱與記憶體位址的對映
  - Builtins  → 處理內建函式呼叫

Usage:
    interp = Interpreter()
    interp.execute(parser.parse())   # 執行完整程式
"""

from parser import (
    Program, FuncDef, VarDecl, ArrayDecl, Block,
    IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    BreakStmt, ContinueStmt, Return, SwitchStmt, ExprStmt,
    BinOp, UnaryOp, Assignment, Call,
    Identifier, Number, Char, StringLiteral,
    AddressOf, Deref, ArrayAccess,
)
from symtable import SymbolTable
from memory import Memory, int32

# 載入本目錄下的 builtins.py。由於 Python 標準函式庫已存在同名的內建模組，
# 一般 import 會優先取得 stdlib 版本；此處改用 importlib.util 直接以檔案路徑載入，
# 確保引用的是 Small-C 解譯器專屬的 Builtins 類別。
import importlib.util as _ilu
import os as _os

_builtins_path = _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), 'builtins.py'
)
_spec = _ilu.spec_from_file_location('smallc_builtins', _builtins_path)
_module = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_module)
Builtins = _module.Builtins
del _ilu, _os, _builtins_path, _spec, _module


# ─────────────────────────────────────────────
# 控制流程例外
# ─────────────────────────────────────────────

class BreakException(Exception):
    """
    用於實作 break 陳述式。
    由 exec_stmt() 在遇到 BreakStmt 節點時拋出，
    由最近的迴圈執行點（while / do-while / for）捕捉並跳出迴圈。
    """


class ContinueException(Exception):
    """
    用於實作 continue 陳述式。
    由 exec_stmt() 在遇到 ContinueStmt 節點時拋出，
    由最近的迴圈執行點捕捉並跳至下一次迭代。
    """


class ReturnException(Exception):
    """
    用於實作 return 陳述式。
    由 exec_stmt() 在遇到 Return 節點時拋出，
    由 call_function() 捕捉並取得函式的回傳值。

    Attributes:
        value (int): 函式的回傳值。
    """
    def __init__(self, value):
        self.value = value


# ─────────────────────────────────────────────
# 直譯器主體
# ─────────────────────────────────────────────

class Interpreter:
    """
    Small-C 樹狀走訪直譯器。

    持有執行期間所需的所有共用資源（Memory、SymbolTable、Builtins），
    並提供兩種執行入口：完整程式模式（execute）與互動片段模式（execute_interactive）。

    Attributes:
        memory    (Memory):      直譯器共用的記憶體空間。
        symtable  (SymbolTable): 管理所有作用域中的變數符號。
        builtins  (Builtins):    內建函式的實作集合。
        functions (dict):        使用者定義的函式表，格式為 {name: FuncDef}。
        trace     (bool):        是否啟用 TRACE 模式，啟用時每執行一個節點會印出追蹤資訊。
    """

    def __init__(self):
        """初始化直譯器，建立空的執行環境。"""
        self.memory = Memory()
        self.symtable = SymbolTable(self.memory)
        self.builtins = Builtins(self.memory)
        self.functions = {}
        self.trace = False

    def reset(self):
        """
        清除所有執行狀態，回到初始環境。
        在 NEW 指令清空緩衝區或 RUN 指令重新執行程式前呼叫。
        """
        self.memory.reset()
        self.symtable.reset()
        self.functions = {}
        self.trace = False

    # ── 執行入口 ──────────────────────────────────

    def execute(self, program: Program):
        """
        執行完整的 Small-C 程式（對應 RUN 指令或載入檔案後執行）。

        執行分為兩遍：
          第一遍：掃描所有頂層宣告，將函式定義存入 functions，
                 並對全域變數宣告進行配置與初始化。
          第二遍：呼叫 main() 函式開始實際執行。

        Args:
            program (Program): Parser 產生的 AST 根節點。

        Returns:
            int: main() 函式的回傳值。

        Raises:
            RuntimeError: 程式中未定義 main() 函式時。
        """
        for decl in program.decls:
            if isinstance(decl, FuncDef):
                self.functions[decl.name] = decl
            elif isinstance(decl, (VarDecl, ArrayDecl)):
                self._exec_decl(decl)

        if 'main' not in self.functions:
            raise RuntimeError("No main() function defined")
        return self._call_function('main', [])

    def execute_interactive(self, program: Program):
        """
        在互動模式下執行 AST 片段（對應 REPL 中直接輸入的運算式或陳述式）。

        與 execute() 的差別在於不需要 main()：
          - 遇到 FuncDef → 存入 functions 供後續呼叫
          - 遇到 VarDecl / ArrayDecl → 宣告為全域變數
          - 其他陳述式 / 運算式 → 直接執行

        Args:
            program (Program): Parser 產生的 AST 根節點。
        """
        for decl in program.decls:
            if isinstance(decl, FuncDef):
                self.functions[decl.name] = decl
            elif isinstance(decl, (VarDecl, ArrayDecl)):
                self._exec_decl(decl)
            else:
                self._exec_stmt(decl)

    # ── 宣告執行 ──────────────────────────────────

    def _exec_decl(self, node):
        """
        執行變數或陣列宣告，在符號表中建立符號並完成初始化。

        VarDecl：配置 1 個單元，若有初始化運算式則求值後寫入。
        ArrayDecl：配置連續空間，若有初始化列表則依序求值後寫入。

        Args:
            node (VarDecl | ArrayDecl): 宣告節點。
        """
        if isinstance(node, VarDecl):
            symbol = self.symtable.declare(node.name, node.var_type, node.is_pointer)
            if node.value is not None:
                val = self._eval_expr(node.value)
                self.symtable.set_value(node.name, val)

        elif isinstance(node, ArrayDecl):
            size = self._eval_expr(node.size)
            symbol = self.symtable.declare_array(node.name, node.var_type, size)
            if node.value is not None:
                for i, v in enumerate(node.value):
                    if i >= size:
                        break  # 初始值數量超過陣列大小，忽略多餘的部分
                    val = self._eval_expr(v)
                    if node.var_type == 'char':
                        self.memory.write_char(symbol.addr + i, val)
                    else:
                        self.memory.write(symbol.addr + i, val)

    # ── 陳述式執行 ────────────────────────────────

    def _exec_stmt(self, node):
        """
        遞迴執行單一陳述式節點。

        若 TRACE 模式啟用，每次執行前會先印出節點的字串表示。

        支援的節點類型：
          VarDecl / ArrayDecl → 轉交 exec_decl()
          Block               → 依序執行所有子陳述式
          IfStmt              → 求值條件後執行對應分支
          WhileStmt           → 條件迴圈，捕捉 Break / Continue 例外
          DoWhileStmt         → 先執行主體再判斷條件，捕捉 Break / Continue 例外
          ForStmt             → 含 init / condition / update 的完整 for 迴圈
          Return              → 求值後拋出 ReturnException
          SwitchStmt          → 依運算式值跳轉對應 case，支援 fall-through 與 break
          BreakStmt           → 拋出 BreakException
          ContinueStmt        → 拋出 ContinueException
          其他（運算式節點）   → 轉交 eval_expr() 求值（忽略回傳值）

        Args:
            node (Stmt): 要執行的陳述式節點。
        """
        if self.trace and not isinstance(node, (Block, WhileStmt)):
            line = getattr(node, 'line', '?')
            print(f"[line {line}] {node.trace_repr()}")

        if isinstance(node, (VarDecl, ArrayDecl)):
            self._exec_decl(node)

        elif isinstance(node, Block):
            save_top = self.memory.heap_top   # 記錄進入區塊前的堆頂，以便離開時釋放區域變數
            self.symtable.push_scope()
            try:
                for stmt in node.statements:
                    self._exec_stmt(stmt)
            finally:
                self.symtable.pop_scope()
                self.memory.free_to(save_top)  # 釋放本區塊內分配的所有記憶體（含字串字面量）

        elif isinstance(node, IfStmt):
            cond = self._eval_expr(node.condition)
            if cond:
                self._exec_stmt(node.then_branch)
            elif node.else_branch:
                self._exec_stmt(node.else_branch)

        elif isinstance(node, WhileStmt):
            while True:
                if self.trace:
                    line = getattr(node, 'line', '?')
                    print(f"[line {line}] {node.trace_repr()}")
                cond_top = self.memory.heap_top
                cond = self._eval_expr(node.condition)
                self.memory.free_to(cond_top)
                if not cond:
                    break
                try:
                    self._exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    continue

        elif isinstance(node, DoWhileStmt):
            while True:
                try:
                    self._exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                cond_top = self.memory.heap_top
                cond = self._eval_expr(node.condition)
                self.memory.free_to(cond_top)
                if not cond:
                    break

        elif isinstance(node, ForStmt):
            if node.init:
                self._eval_expr(node.init)
            while True:
                if node.condition:
                    cond_top = self.memory.heap_top
                    cond = self._eval_expr(node.condition)
                    self.memory.free_to(cond_top)
                    if not cond:
                        break
                try:
                    self._exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                if node.update:
                    upd_top = self.memory.heap_top
                    self._eval_expr(node.update)
                    self.memory.free_to(upd_top)

        elif isinstance(node, Return):
            val = self._eval_expr(node.value) if node.value else 0
            raise ReturnException(val)

        elif isinstance(node, BreakStmt):
            raise BreakException()
        
        elif isinstance(node, SwitchStmt):
            val = self._eval_expr(node.expr)

            # 第一遍：找出第一個匹配 case 的索引，並記錄 default 的索引
            start_idx = None
            default_idx = None
            for i, (item_val, _) in enumerate(node.items):
                if item_val is None:
                    default_idx = i          # 記錄 default 在列表中的位置
                elif item_val == val and start_idx is None:
                    start_idx = i            # 記錄第一個匹配 case 的位置

            # 若無匹配 case，從 default 位置開始（若存在）
            if start_idx is None:
                start_idx = default_idx
            if start_idx is None:
                return  # 無匹配且無 default，跳過整個 switch

            # 從匹配位置依序執行，支援完整 fall-through（含 fall-through 至 default）
            try:
                for _, case_stmts in node.items[start_idx:]:
                    for stmt in case_stmts:
                        self._exec_stmt(stmt)
            except BreakException:
                return

        elif isinstance(node, ContinueStmt):
            raise ContinueException()

        elif isinstance(node, ExprStmt):
            self._eval_expr(node.expr)

        else:
            self._eval_expr(node)

    # ── 運算式求值 ────────────────────────────────

    def _eval_expr(self, node) -> int:
        """
        遞迴求值單一運算式節點，回傳整數結果。

        各節點類型的求值行為：
          Number        → 直接回傳整數字面量
          Char          → 回傳字元的 ASCII 碼
          StringLiteral → 將字串寫入 Memory，回傳起始位址
          Identifier    → 從符號表查詢並讀取變數值
          BinOp         → 轉交 eval_binop()
          UnaryOp       → 轉交 eval_unaryop()
          Assignment    → 轉交 eval_assignment()
          Call          → 轉交 eval_call()
          AddressOf     → 轉交 eval_addressof()，回傳變數的 Memory 位址
          Deref         → 解參考指標，從指標所指位址讀取值
          ArrayAccess   → 計算元素位址並讀取，越界時拋出例外

        Args:
            node (Expr): 要求值的運算式節點。

        Returns:
            int: 運算式的求值結果。

        Raises:
            RuntimeError: 遇到未知的 AST 節點類型，或陣列存取越界時。
        """
        if isinstance(node, Number):
            return int32(node.value)

        elif isinstance(node, Char):
            return ord(node.value)

        elif isinstance(node, StringLiteral):
            addr = self.memory.allocate(len(node.value) + 1)
            self.memory.write_string(addr, node.value)
            return addr

        elif isinstance(node, Identifier):
            # lookup() 找不到時會拋出 RuntimeError，不會回傳 None
            symbol = self.symtable.lookup(node.name)
            # 陣列名稱作為右值時，退化為指向首元素的指標（array decay）
            if symbol.is_array:
                return symbol.addr
            return self.memory.read(symbol.addr)

        elif isinstance(node, BinOp):
            return self._eval_binop(node)

        elif isinstance(node, UnaryOp):
            return self._eval_unaryop(node)

        elif isinstance(node, Assignment):
            return self._eval_assignment(node)

        elif isinstance(node, Call):
            return self._eval_call(node)

        elif isinstance(node, AddressOf):
            return self._eval_addressof(node)

        elif isinstance(node, Deref):
            addr = self._eval_expr(node.pointer)
            if addr == 0:
                raise RuntimeError("Runtime error: null pointer dereference")
            return self.memory.read(addr)

        elif isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self._eval_expr(node.index)
            if symbol.is_array:
                # 真正的陣列：做 bounds check，直接用基底位址
                if index < 0 or index >= symbol.array_size:
                    raise RuntimeError(
                        f"Runtime error: array index out of bounds "
                        f"(index {index}, size {symbol.array_size})."
                    )
                return self.memory.read(symbol.addr + index)
            else:
                # 指標參數：讀取指標值作為基底位址，不做 bounds check
                base = self.memory.read(symbol.addr)
                return self.memory.read(base + index)

        raise RuntimeError(f"Unknown AST node: {type(node)}")

    # ── 二元運算式 ────────────────────────────────

    def _eval_binop(self, node: BinOp) -> int:
        """
        求值二元運算式。

        AND / OR 採用短路求值（short-circuit evaluation）：
          AND：左側為假時不求值右側，直接回傳 0。
          OR：左側為真時不求值右側，直接回傳 1。

        其餘運算子先求值左右兩側，再依運算子類型計算結果。
        算術與位元運算結果均截斷為 32 位元有號整數。
        DIV 與 MOD 在除數為 0 時拋出執行期例外。

        Args:
            node (BinOp): 二元運算式節點。

        Returns:
            int: 運算結果（比較運算子回傳 0 或 1）。

        Raises:
            RuntimeError: 除數為 0，或遇到未知運算子時。
        """
        if node.op == "AND":
            return 1 if (self._eval_expr(node.left) and self._eval_expr(node.right)) else 0
        if node.op == "OR":
            return 1 if (self._eval_expr(node.left) or self._eval_expr(node.right)) else 0

        left = self._eval_expr(node.left)
        right = self._eval_expr(node.right)
        op = node.op

        if op == "PLUS":    return int32(left + right)
        if op == "MINUS":   return int32(left - right)
        if op == "MUL":     return int32(left * right)
        if op == "DIV":
            if right == 0:
                raise RuntimeError("Runtime error: division by zero.")
            return int32(int(left / right))
        if op == "MOD":
            if right == 0:
                raise RuntimeError("Runtime error: division by zero.")
            # C 語意：截斷除法，餘數符號與被除數相同（不同於 Python 的 floor 除法）
            return int32(left - int(left / right) * right)
        if op == "EQ":      return 1 if left == right else 0
        if op == "NEQ":     return 1 if left != right else 0
        if op == "LT":      return 1 if left < right else 0
        if op == "GT":      return 1 if left > right else 0
        if op == "LTE":     return 1 if left <= right else 0
        if op == "GTE":     return 1 if left >= right else 0
        if op == "BIT_AND": return int32(left & right)
        if op == "BIT_OR":  return int32(left | right)
        if op == "BIT_XOR": return int32(left ^ right)
        if op == "LSHIFT":
            if right < 0:
                raise RuntimeError("Runtime error: left shift count is negative.")
            return int32(left << right)
        if op == "RSHIFT":
            if right < 0:
                raise RuntimeError("Runtime error: right shift count is negative.")
            return int32(left >> right)

        raise RuntimeError(f"Unknown binary operator: {op}")

    # ── 一元運算式 ────────────────────────────────

    def _eval_unaryop(self, node: UnaryOp) -> int:
        """
        求值一元前置運算式。

        支援的運算子：
          MINUS   → 取負值（截斷為 32 位元）
          PLUS    → 不改變值
          NOT     → 邏輯非（0 → 1，非 0 → 0）
          BIT_NOT → 位元反相（截斷為 32 位元）
          INC     → 前置遞增（++x），修改目標並回傳新值
          DEC     → 前置遞減（--x），修改目標並回傳新值

        Args:
            node (UnaryOp): 一元運算式節點。

        Returns:
            int: 運算結果。

        Raises:
            RuntimeError: 遇到未知運算子時。
        """
        op = node.op
        if op == "MINUS":
            return int32(-self._eval_expr(node.operand))
        if op == "PLUS":
            return self._eval_expr(node.operand)
        if op == "NOT":
            return 1 if not self._eval_expr(node.operand) else 0
        if op == "BIT_NOT":
            return int32(~self._eval_expr(node.operand))
        if op == "INC":
            return self._eval_inc_dec(node.operand, 1)
        if op == "DEC":
            return self._eval_inc_dec(node.operand, -1)

        raise RuntimeError(f"Unknown unary operator: {op}")

    def _eval_inc_dec(self, target, delta: int) -> int:
        """
        執行前置遞增（++）或遞減（--），修改目標並回傳修改後的新值。

        支援三種左值目標：
          Identifier  → 透過符號表讀寫
          Deref       → 透過指標位址讀寫 Memory
          ArrayAccess → 計算元素位址後讀寫 Memory

        Args:
            target (Expr): 要修改的左值節點。
            delta  (int):  遞增為 +1，遞減為 -1。

        Returns:
            int: 修改後的新值。

        Raises:
            RuntimeError: 目標不是合法的左值時。
        """
        if isinstance(target, Identifier):
            symbol = self.symtable.lookup(target.name)
            if symbol.is_array:
                raise RuntimeError("Runtime error: cannot apply ++/-- to array name.")
            val = self.symtable.get_value(target.name)
            new_val = int32(val + delta)
            self.symtable.set_value(target.name, new_val)
            return new_val
        if isinstance(target, Deref):
            addr = self._eval_expr(target.pointer)
            val = self.memory.read(addr)
            new_val = int32(val + delta)
            if (isinstance(target.pointer, Identifier) and
                    self.symtable.lookup(target.pointer.name).var_type == 'char'):
                self.memory.write_char(addr, new_val)
            else:
                self.memory.write(addr, new_val)
            return new_val
        if isinstance(target, ArrayAccess):
            symbol = self.symtable.lookup(target.array.name)
            index = self._eval_expr(target.index)
            if symbol.is_array:
                if index < 0 or index >= symbol.array_size:
                    raise RuntimeError(
                        f"Runtime error: array index out of bounds "
                        f"(index {index}, size {symbol.array_size})."
                    )
                addr = symbol.addr + index
            else:
                base = self.memory.read(symbol.addr)
                addr = base + index
            val = self.memory.read(addr)
            new_val = int32(val + delta)
            if symbol.var_type == 'char':
                self.memory.write_char(addr, new_val)
            else:
                self.memory.write(addr, new_val)
            return new_val
        raise RuntimeError("Runtime error: invalid increment/decrement target.")

    # ── 賦值運算式 ────────────────────────────────

    def _eval_assignment(self, node: Assignment) -> int:
        """
        執行賦值或複合賦值運算式，將結果寫入左值後回傳。

        一般賦值（ASSIGN）：直接將右值求值後寫入目標。
        複合賦值（ADD_ASSIGN 等）：先讀取目標舊值，與右值運算後再寫回。
        DIV_ASSIGN / MOD_ASSIGN 在除數為 0 時拋出例外。

        Args:
            node (Assignment): 賦值運算式節點。

        Returns:
            int: 賦值後的新值。

        Raises:
            RuntimeError: 複合賦值中除數為 0，或目標不是合法左值時。
        """
        val = self._eval_expr(node.value)

        if node.op != "ASSIGN":
            old = self._eval_lvalue_read(node.target)
            if node.op == "ADD_ASSIGN":
                val = int32(old + val)
            elif node.op == "SUB_ASSIGN":
                val = int32(old - val)
            elif node.op == "MUL_ASSIGN":
                val = int32(old * val)
            elif node.op == "DIV_ASSIGN":
                if val == 0:
                    raise RuntimeError("Runtime error: division by zero.")
                val = int32(int(old / val))
            elif node.op == "MOD_ASSIGN":
                if val == 0:
                    raise RuntimeError("Runtime error: division by zero.")
                # C 語意：截斷除法，餘數符號與被除數相同
                val = int32(old - int(old / val) * val)

        self._eval_lvalue_write(node.target, val)
        return val

    def _eval_lvalue_read(self, node) -> int:
        """
        從左值節點讀取目前的值（供複合賦值使用）。

        Args:
            node (Expr): 左值節點（Identifier / Deref / ArrayAccess）。

        Returns:
            int: 目前儲存的值。

        Raises:
            RuntimeError: 節點不是合法的左值時。
        """
        if isinstance(node, Identifier):
            return self.symtable.get_value(node.name)
        if isinstance(node, Deref):
            addr = self._eval_expr(node.pointer)
            return self.memory.read(addr)
        if isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self._eval_expr(node.index)
            if symbol.is_array:
                return self.memory.read(symbol.addr + index)
            else:
                base = self.memory.read(symbol.addr)
                return self.memory.read(base + index)
        raise RuntimeError("Invalid assignment target")

    def _eval_lvalue_write(self, node, val: int):
        """
        將值寫入左值節點對應的 Memory 位址。

        char 型別的陣列元素使用 write_char()（8 位元截斷），
        其餘使用 write()（32 位元截斷）。

        Args:
            node (Expr): 左值節點（Identifier / Deref / ArrayAccess）。
            val  (int):  要寫入的值。

        Raises:
            RuntimeError: 陣列存取越界，或節點不是合法的左值時。
        """
        if isinstance(node, Identifier):
            self.symtable.set_value(node.name, val)
        elif isinstance(node, Deref):
            addr = self._eval_expr(node.pointer)
            if addr == 0:
                raise RuntimeError("Runtime error: null pointer dereference")
            # char* 指標寫入需要 8 位元截斷
            if (isinstance(node.pointer, Identifier) and
                    self.symtable.lookup(node.pointer.name).var_type == 'char'):
                self.memory.write_char(addr, val)
            else:
                self.memory.write(addr, val)
        elif isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self._eval_expr(node.index)
            if symbol.is_array:
                if index < 0 or index >= symbol.array_size:
                    raise RuntimeError(
                        f"Runtime error: array index out of bounds "
                        f"(index {index}, size {symbol.array_size})."
                    )
                addr = symbol.addr + index
            else:
                # 指標參數：讀取指標值作為基底位址
                base = self.memory.read(symbol.addr)
                addr = base + index
            if symbol.var_type == 'char':
                self.memory.write_char(addr, val)
            else:
                self.memory.write(addr, val)
        else:
            raise RuntimeError("Invalid assignment target")

    # ── 函式呼叫 ──────────────────────────────────

    def _eval_call(self, node: Call) -> int:
        """
        求值函式呼叫運算式。

        先判斷是否為內建函式（交給 Builtins 處理），
        否則查詢 functions 字典並呼叫使用者定義函式。

        Args:
            node (Call): 函式呼叫節點。

        Returns:
            int: 函式的回傳值。
        """
        name = node.name.name
        args = [self._eval_expr(a) for a in node.args]

        if self.builtins.is_builtin(name):
            return self.builtins.call(name, args)

        return self._call_function(name, args)

    def _call_function(self, name: str, args: list) -> int:
        """
        呼叫使用者定義的函式。

        執行步驟：
          1. 記錄目前的 heap_top，用於函式返回後釋放區域變數。
          2. push 新的作用域並將引數綁定為參數變數。
          3. 執行函式主體，捕捉 ReturnException 取得回傳值。
          4. pop 作用域，並將 heap_top 回退到步驟 1 記錄的位址。

        Args:
            name (str):   函式名稱。
            args (list):  已求值的引數列表（整數）。

        Returns:
            int: 函式的回傳值；無 return 陳述式時回傳 0。

        Raises:
            RuntimeError: 函式名稱未定義時。
        """
        if name not in self.functions:
            raise RuntimeError(f"Undefined function '{name}'")
        func = self.functions[name]

        if len(args) != len(func.params):
            raise RuntimeError(
                f"Runtime error: function '{name}' expects "
                f"{len(func.params)} argument(s), got {len(args)}."
            )

        save_top = self.memory.heap_top
        self.symtable.push_scope()

        for param, arg in zip(func.params, args):
            symbol = self.symtable.declare(param.name, param.var_type, param.is_pointer)
            self.symtable.set_value(param.name, arg)

        ret_val = 0
        try:
            self._exec_stmt(func.body)
        except ReturnException as e:
            ret_val = e.value

        self.symtable.pop_scope()
        self.memory.free_to(save_top)
        return ret_val

    # ── 取址運算式 ────────────────────────────────

    def _eval_addressof(self, node: AddressOf) -> int:
        """
        求值取址運算式（&x 或 &arr[i]），回傳目標的 Memory 位址。

        Args:
            node (AddressOf): 取址運算式節點。

        Returns:
            int: 目標變數或陣列元素的 Memory 位址。

        Raises:
            RuntimeError: 目標不是合法的可取址對象時。
        """
        target = node.target
        if isinstance(target, Identifier):
            return self.symtable.lookup(target.name).addr
        if isinstance(target, ArrayAccess):
            symbol = self.symtable.lookup(target.array.name)
            index = self._eval_expr(target.index)
            if symbol.is_array:
                return symbol.addr + index
            else:
                base = self.memory.read(symbol.addr)
                return base + index
        raise RuntimeError("Invalid & target")

