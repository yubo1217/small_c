"""
memory.py — Small-C 直譯器的線性記憶體模型
==========================================
本模組以一個固定大小的整數陣列模擬 Small-C 的記憶體空間，
並提供配置、讀寫、字串存取與重置等操作。

記憶體配置策略採用線性堆疊（bump allocator）：
  - heap_top 指向目前已配置空間的結尾。
  - allocate() 每次從 heap_top 往高位址方向延伸。
  - free_to()  將 heap_top 回退到指定位址，用於函式返回時釋放區域變數。

資料型別範圍：
  - int  → 32 位元有號整數（−2,147,483,648 ～ 2,147,483,647）
  - char →  8 位元有號整數（−128 ～ 127）
  - 字串 → 以 null 字元（0）結尾的連續 char 序列

Usage:
    mem = Memory()
    addr = mem.allocate(4)   # 配置 4 個單元
    mem.write(addr, 42)
    print(mem.read(addr))    # 42
"""


class Memory:
    """
    Small-C 直譯器的線性記憶體空間。

    以 Python list 模擬一塊連續的整數陣列，每個元素代表一個記憶體單元。
    所有變數、陣列、字串字面量均配置在此空間中。

    Attributes:
        data     (list[int]): 記憶體陣列，初始值全為 0。
        heap_top (int):       目前已配置空間的頂端位址（下一次 allocate 的起點）。
    """

    def __init__(self, size: int = 65536):
        """
        初始化記憶體空間。

        Args:
            size (int): 記憶體總大小（單元數），預設為 65536。
        """
        self.data = [0] * size
        self.heap_top = 0

    # ── 配置與釋放 ────────────────────────────────

    def allocate(self, size: int) -> int:
        """
        從 heap_top 往上配置連續的記憶體單元。

        Args:
            size (int): 需要配置的單元數。

        Returns:
            int: 配置區段的起始位址。

        Raises:
            RuntimeError: 剩餘空間不足時。
        """
        if self.heap_top + size > len(self.data):
            raise RuntimeError("Out of memory")
        addr = self.heap_top
        self.heap_top += size
        return addr

    def free_to(self, addr: int):
        """
        將 heap_top 回退到指定位址，釋放其上方的所有空間。
        用於函式返回時批次釋放區域變數。

        Args:
            addr (int): 要回退到的位址（通常是呼叫函式前記錄的 heap_top）。
        """
        self.heap_top = addr

    # ── 整數讀寫 ──────────────────────────────────

    def read(self, addr: int) -> int:
        """
        從指定位址讀取一個整數值。

        Args:
            addr (int): 要讀取的記憶體位址。

        Returns:
            int: 該位址儲存的整數值。

        Raises:
            RuntimeError: 位址超出已配置範圍時。
        """
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        return self.data[addr]

    def write(self, addr: int, value: int):
        """
        將整數值寫入指定位址，並截斷為 32 位元有號整數範圍。

        Args:
            addr  (int): 目標記憶體位址。
            value (int): 要寫入的整數值。

        Raises:
            RuntimeError: 位址超出已配置範圍時。
        """
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        value = int(value)
        value = ((value + 2**31) % 2**32) - 2**31  # 截斷為 32 位元有號整數
        self.data[addr] = value

    def write_char(self, addr: int, value: int):
        """
        將字元值寫入指定位址，並截斷為 8 位元有號整數範圍（-128 ～ 127）。

        Args:
            addr  (int): 目標記憶體位址。
            value (int): 要寫入的字元值（通常為 ASCII 碼）。

        Raises:
            RuntimeError: 位址超出已配置範圍時。
        """
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        value = int(value)
        value = ((value + 128) % 256) - 128  # 截斷為 8 位元有號整數
        self.data[addr] = value

    # ── 字串讀寫 ──────────────────────────────────

    def read_string(self, addr: int) -> str:
        """
        從指定位址讀取以 null 結尾的字串（C 字串格式）。

        Args:
            addr (int): 字串的起始位址。

        Returns:
            str: 讀取到的 Python 字串（不含結尾的 null 字元）。

        Raises:
            RuntimeError: 讀取過程中位址超出已配置範圍時。
        """
        result = ""
        while True:
            if addr < 0 or addr >= self.heap_top:
                raise RuntimeError(f"Memory access out of bounds: address {addr}")
            ch = self.data[addr]
            if ch == 0:
                break
            result += chr(ch & 0xFF)  # 負值字元（有號 8-bit）轉換為合法 Unicode 碼位
            addr += 1
        return result

    def write_string(self, addr: int, s: str):
        """
        將 Python 字串寫入指定位址，並在結尾自動附加 null 字元（0）。

        Args:
            addr (int): 目標起始位址，需確保有足夠空間（len(s) + 1 個單元）。
            s    (str): 要寫入的 Python 字串。
        """
        for ch in s:
            self.write_char(addr, ord(ch))
            addr += 1
        self.write_char(addr, 0)  # 寫入 null 終止字元

    # ── 重置 ──────────────────────────────────────

    def reset(self):
        """
        清除所有記憶體內容並將 heap_top 歸零。
        在 NEW 指令清空緩衝區或 RUN 指令重新執行程式前呼叫，
        確保每次執行都從乾淨的狀態開始。
        """
        self.data = [0] * len(self.data)
        self.heap_top = 0