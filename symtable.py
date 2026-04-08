"""
symtable.py — Small-C 直譯器的符號表（Symbol Table）
=====================================================
本模組管理 Small-C 程式執行期間所有變數的名稱、型別與記憶體位址對應關係。

核心設計：
  - Symbol      記錄單一變數的完整後設資料（型別、位址、是否為指標/陣列）。
  - SymbolTable 以「作用域堆疊」管理巢狀作用域的生命週期：
      scopes[0]  → 全域作用域（程式整個執行期間有效）
      scopes[1+] → 每次函式呼叫時 push，返回時 pop

查詢規則：從最內層作用域往外搜尋，符合 C 語言的變數遮蔽（shadowing）行為。

與 Memory 的關係：
  SymbolTable 僅儲存「名稱 → 位址」的對映，
  實際的數值讀寫仍委派給 Memory 模組執行。

Usage:
    mem   = Memory()
    table = SymbolTable(mem)
    table.declare('x', 'int')
    table.set_value('x', 42)
    print(table.get_value('x'))   # 42
"""


class Symbol:
    """
    代表符號表中的一個變數記錄。

    每個 Symbol 對應一個在 Small-C 程式中宣告的變數、指標或陣列，
    並儲存執行期間所需的所有後設資料。

    Attributes:
        name       (str):  變數名稱。
        var_type   (str):  型別名稱，可為 'int'、'char' 或 'void'。
        addr       (int):  該變數在 Memory 中的起始位址。
        is_pointer (bool): 是否為指標型別（宣告時帶有 *）。
        is_array   (bool): 是否為陣列型別（宣告時帶有 []）。
        array_size (int):  陣列元素數量；非陣列時為 0。
    """

    def __init__(self, name, var_type, addr,
                 is_pointer=False, is_array=False, array_size=0):
        self.name = name
        self.var_type = var_type
        self.addr = addr
        self.is_pointer = is_pointer
        self.is_array = is_array
        self.array_size = array_size

    def __repr__(self):
        if self.is_array:
            return f"Symbol({self.var_type} {self.name}[{self.array_size}] @ {self.addr})"
        if self.is_pointer:
            return f"Symbol({self.var_type} *{self.name} @ {self.addr})"
        return f"Symbol({self.var_type} {self.name} @ {self.addr})"


class SymbolTable:
    """
    以作用域堆疊實作的符號表，管理所有變數的名稱與記憶體位址對映。

    Attributes:
        memory (Memory):       直譯器共用的記憶體物件，用於實際的數值讀寫。
        scopes (list[dict]):   作用域堆疊，每層為 {name: Symbol} 字典。
                               scopes[0] 為全域作用域，之後每次函式呼叫新增一層。
    """

    def __init__(self, memory):
        """
        初始化符號表，建立空的全域作用域。

        Args:
            memory (Memory): 直譯器共用的記憶體物件。
        """
        self.memory = memory
        self.scopes = [{}]

    # ── 作用域管理 ────────────────────────────────

    def push_scope(self):
        """
        新增一層作用域，在函式呼叫開始時使用。
        """
        self.scopes.append({})

    def pop_scope(self):
        """
        移除最內層作用域，在函式返回時使用。
        全域作用域（scopes[0]）不會被移除。
        """
        if len(self.scopes) > 1:
            self.scopes.pop()

    def is_global(self) -> bool:
        """
        判斷目前是否處於全域作用域。

        Returns:
            bool: 若目前只有全域作用域（未在任何函式內）則為 True。
        """
        return len(self.scopes) == 1

    # ── 變數宣告 ──────────────────────────────────

    def declare(self, name: str, var_type: str, is_pointer: bool = False) -> Symbol:
        """
        在目前作用域宣告一個變數，並在 Memory 中配置一個單元，初始化為 0。

        Args:
            name       (str):  變數名稱。
            var_type   (str):  型別名稱（'int'、'char' 或 'void'）。
            is_pointer (bool): 是否為指標型別，預設為 False。

        Returns:
            Symbol: 新建立的符號記錄。

        Raises:
            RuntimeError: 同一作用域內已有同名變數時。
        """
        scope = self.scopes[-1]
        if name in scope:
            raise RuntimeError(f"Variable '{name}' already declared in this scope")
        addr = self.memory.allocate(1)
        self.memory.write(addr, 0)
        symbol = Symbol(name, var_type, addr, is_pointer=is_pointer)
        scope[name] = symbol
        return symbol

    def declare_array(self, name: str, var_type: str, size: int) -> Symbol:
        """
        在目前作用域宣告一個陣列，並在 Memory 中配置連續的空間，全部初始化為 0。

        Args:
            name     (str): 陣列名稱。
            var_type (str): 元素型別名稱（'int' 或 'char'）。
            size     (int): 陣列元素數量。

        Returns:
            Symbol: 新建立的符號記錄（is_array=True）。

        Raises:
            RuntimeError: 同一作用域內已有同名變數時。
        """
        scope = self.scopes[-1]
        if name in scope:
            raise RuntimeError(f"Variable '{name}' already declared in this scope")
        addr = self.memory.allocate(size)
        for i in range(size):
            self.memory.write(addr + i, 0)
        symbol = Symbol(name, var_type, addr, is_array=True, array_size=size)
        scope[name] = symbol
        return symbol

    # ── 變數查詢 ──────────────────────────────────

    def lookup(self, name: str) -> Symbol:
        """
        由內而外搜尋所有作用域，回傳指定名稱的符號記錄。

        Args:
            name (str): 要查詢的變數名稱。

        Returns:
            Symbol: 找到的符號記錄。

        Raises:
            RuntimeError: 所有作用域中均找不到該名稱時。
        """
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise RuntimeError(f"Undefined variable '{name}'")

    def lookup_or_none(self, name: str):
        """
        由內而外搜尋所有作用域，找不到時回傳 None 而非拋出例外。
        適合用於「先檢查是否存在再決定行為」的場景。

        Args:
            name (str): 要查詢的變數名稱。

        Returns:
            Symbol | None: 找到的符號記錄，或 None。
        """
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # ── 數值讀寫（透過 Memory）────────────────────

    def get_value(self, name: str) -> int:
        """
        讀取指定變數在 Memory 中儲存的數值。

        Args:
            name (str): 變數名稱。

        Returns:
            int: 該變數目前的數值。
        """
        symbol = self.lookup(name)
        return self.memory.read(symbol.addr)

    def set_value(self, name: str, value: int):
        """
        將數值寫入指定變數在 Memory 中的位址。
        char 型別（非指標）使用 write_char() 以確保 8 位元截斷；
        其餘型別使用 write() 進行 32 位元截斷。

        Args:
            name  (str): 變數名稱。
            value (int): 要寫入的數值。
        """
        symbol = self.lookup(name)
        if symbol.var_type == 'char' and not symbol.is_pointer:
            self.memory.write_char(symbol.addr, value)
        else:
            self.memory.write(symbol.addr, value)

    # ── REPL 指令支援 ─────────────────────────────

    def get_all_globals(self) -> dict:
        """
        回傳全域作用域中所有符號的字典副本，供 VARS 指令顯示使用。

        Returns:
            dict: {name: Symbol} 格式的全域符號字典。
        """
        return dict(self.scopes[0])

    # ── 重置 ──────────────────────────────────────

    def reset(self):
        """
        清空符號表並重建空的全域作用域。
        在 NEW 指令清空緩衝區或 RUN 指令重新執行程式前呼叫，
        確保每次執行都從乾淨的狀態開始。
        """
        self.scopes = [{}]