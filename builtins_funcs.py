"""
builtins_funcs.py — Small-C 直譯器的內建函式庫
================================================
本模組實作所有 Small-C 程式可直接呼叫的內建函式，
涵蓋四大類別：

  I/O 輸入輸出：  printf、putchar、getchar、puts、scanf
  字串操作：      strlen、strcpy、strcmp、strcat
  數學運算：      abs、max、min、pow、sqrt、mod、rand、srand
  記憶體與工具：  memset、sizeof_int、sizeof_char、atoi、itoa、exit

設計方式：
  - Builtins.call()       統一呼叫入口，以函式名稱字串查表分派。
  - Builtins.is_builtin() 供直譯器判斷某函式名稱是否為內建函式。
  - 每個內建函式接收 args（已求值的整數引數列表）並回傳整數結果。
  - 字串引數以 Memory 位址形式傳入，透過 Memory.read_string() 讀取內容。

Usage:
    mem      = Memory()
    builtins = Builtins(mem)
    if builtins.is_builtin('printf'):
        builtins.call('printf', [fmt_addr, arg1, arg2])
"""

import sys
import math
import random


class Builtins:
    """
    Small-C 內建函式的實作集合。

    所有內建函式以私有方法（_xxx）實作，統一透過 call() 分派呼叫。
    字串資料的讀寫均透過 Memory 物件進行，不直接操作 Python 字串記憶體。

    Attributes:
        memory (Memory): 直譯器共用的記憶體物件，供字串與記憶體操作使用。
    """

    def __init__(self, memory):
        """
        初始化內建函式庫。

        Args:
            memory (Memory): 直譯器共用的記憶體物件。
        """
        self.memory = memory

    # ── 統一呼叫介面 ──────────────────────────────

    def call(self, name: str, args: list):
        """
        依函式名稱分派並執行對應的內建函式。

        Args:
            name (str):   內建函式名稱，例如 'printf'、'strlen'。
            args (list):  已求值的引數列表（整數或記憶體位址）。

        Returns:
            int: 函式的回傳值（無回傳值的函式回傳 0）。

        Raises:
            RuntimeError: 函式名稱不在內建清單中時。
        """
        dispatch = {
            'printf':      self._printf,
            'putchar':     self._putchar,
            'getchar':     self._getchar,
            'puts':        self._puts,
            'scanf':       self._scanf,
            'strlen':      self._strlen,
            'strcpy':      self._strcpy,
            'strcmp':      self._strcmp,
            'strcat':      self._strcat,
            'abs':         self._abs,
            'max':         self._max,
            'min':         self._min,
            'pow':         self._pow,
            'sqrt':        self._sqrt,
            'mod':         self._mod,
            'rand':        self._rand,
            'srand':       self._srand,
            'memset':      self._memset,
            'sizeof_int':  self._sizeof_int,
            'sizeof_char': self._sizeof_char,
            'atoi':        self._atoi,
            'itoa':        self._itoa,
            'exit':        self._exit,
        }
        if name not in dispatch:
            raise RuntimeError(f"Unknown builtin function '{name}'")
        return dispatch[name](args)

    def is_builtin(self, name: str) -> bool:
        """
        判斷指定名稱是否為內建函式。
        供直譯器在解析函式呼叫時優先判斷，避免誤當使用者定義函式處理。

        Args:
            name (str): 函式名稱。

        Returns:
            bool: 是內建函式則為 True。
        """
        return name in {
            'printf', 'putchar', 'getchar', 'puts', 'scanf',
            'strlen', 'strcpy', 'strcmp', 'strcat',
            'abs', 'max', 'min', 'pow', 'sqrt', 'mod',
            'rand', 'srand', 'memset', 'sizeof_int', 'sizeof_char',
            'atoi', 'itoa', 'exit',
        }

    # ── I/O 輸入輸出 ──────────────────────────────

    def _printf(self, args):
        """
        格式化輸出，對應 C 標準函式 printf()。

        args[0]: 格式字串的 Memory 位址。
        args[1+]: 依格式符號依序對應的引數。

        支援的格式符號：
          %d → 十進位整數
          %c → 字元（取低 8 位元）
          %s → 字串（從 Memory 讀取）
          %x → 十六進位整數（不帶 0x 前綴）
          %% → 輸出 % 字元本身

        Returns:
            int: 固定回傳 0。
        """
        if not args:
            raise RuntimeError("printf: missing format string")
        fmt = self.memory.read_string(args[0])
        arg_idx = 1
        result = ""
        i = 0
        while i < len(fmt):
            if fmt[i] == '%' and i + 1 < len(fmt):
                spec = fmt[i + 1]
                if spec == 'd':
                    if arg_idx >= len(args):
                        raise RuntimeError("printf: not enough arguments")
                    result += str(int(args[arg_idx]))
                    arg_idx += 1
                elif spec == 'c':
                    if arg_idx >= len(args):
                        raise RuntimeError("printf: not enough arguments")
                    result += chr(int(args[arg_idx]) & 0xFF)
                    arg_idx += 1
                elif spec == 's':
                    if arg_idx >= len(args):
                        raise RuntimeError("printf: not enough arguments")
                    result += self.memory.read_string(int(args[arg_idx]))
                    arg_idx += 1
                elif spec == 'x':
                    if arg_idx >= len(args):
                        raise RuntimeError("printf: not enough arguments")
                    result += hex(int(args[arg_idx]) & 0xFFFFFFFF)[2:]
                    arg_idx += 1
                elif spec == '%':
                    result += '%'
                else:
                    result += '%' + spec
                i += 2
            else:
                result += fmt[i]
                i += 1
        sys.stdout.write(result)
        sys.stdout.flush()
        return 0

    def _putchar(self, args):
        """
        輸出單一字元，對應 C 標準函式 putchar()。

        args[0]: 要輸出的字元值（取低 8 位元作為 ASCII 碼）。

        Returns:
            int: 輸出的字元值。
        """
        if not args:
            raise RuntimeError("putchar: missing argument")
        ch = int(args[0]) & 0xFF
        sys.stdout.write(chr(ch))
        sys.stdout.flush()
        return ch

    def _getchar(self, args):
        """
        從標準輸入讀取單一字元，對應 C 標準函式 getchar()。

        Returns:
            int: 讀取字元的 ASCII 碼；若已到 EOF 則回傳 -1。
        """
        ch = sys.stdin.read(1)
        if not ch:
            return -1
        return ord(ch)

    def _puts(self, args):
        """
        輸出字串並自動換行，對應 C 標準函式 puts()。

        args[0]: 字串的 Memory 位址。

        Returns:
            int: 固定回傳 0。
        """
        if not args:
            raise RuntimeError("puts: missing argument")
        s = self.memory.read_string(int(args[0]))
        sys.stdout.write(s + '\n')
        sys.stdout.flush()
        return 0

    def _scanf(self, args):
        """
        從標準輸入讀取格式化資料，對應 C 標準函式 scanf()。

        args[0]: 格式字串的 Memory 位址。
        args[1+]: 各變數的 Memory 位址（用於寫回讀取到的值）。

        支援的格式符號：
          %d → 讀取整數，寫入對應位址
          %c → 讀取單一字元，以 write_char 寫入對應位址

        Returns:
            int: 成功讀取的項目數量。
        """
        if not args:
            raise RuntimeError("scanf: missing format string")
        fmt = self.memory.read_string(args[0])
        arg_idx = 1
        count = 0
        i = 0
        while i < len(fmt):
            if fmt[i] == '%' and i + 1 < len(fmt):
                spec = fmt[i + 1]
                if spec == 'd':
                    if arg_idx >= len(args):
                        raise RuntimeError("scanf: not enough arguments")
                    try:
                        val = int(input() if i == 0 else sys.stdin.readline().strip())
                    except ValueError:
                        return count
                    self.memory.write(int(args[arg_idx]), val)
                    arg_idx += 1
                    count += 1
                elif spec == 'c':
                    if arg_idx >= len(args):
                        raise RuntimeError("scanf: not enough arguments")
                    ch = sys.stdin.read(1)
                    if not ch:
                        return count
                    self.memory.write_char(int(args[arg_idx]), ord(ch))
                    arg_idx += 1
                    count += 1
                i += 2
            else:
                i += 1
        return count

    # ── 字串操作 ──────────────────────────────────

    def _strlen(self, args):
        """
        回傳字串長度（不含結尾 null），對應 C 標準函式 strlen()。

        args[0]: 字串的 Memory 位址。

        Returns:
            int: 字串的字元數。
        """
        if not args:
            raise RuntimeError("strlen: missing argument")
        return len(self.memory.read_string(int(args[0])))

    def _strcpy(self, args):
        """
        將來源字串複製到目的地，對應 C 標準函式 strcpy()。

        args[0]: 目的地的 Memory 位址。
        args[1]: 來源字串的 Memory 位址。

        Returns:
            int: 目的地的 Memory 位址（args[0]）。
        """
        if len(args) < 2:
            raise RuntimeError("strcpy: missing arguments")
        src = self.memory.read_string(int(args[1]))
        self.memory.write_string(int(args[0]), src)
        return int(args[0])

    def _strcmp(self, args):
        """
        比較兩個字串的字典序，對應 C 標準函式 strcmp()。

        args[0]: 第一個字串的 Memory 位址。
        args[1]: 第二個字串的 Memory 位址。

        Returns:
            int: s1 < s2 回傳 -1，s1 > s2 回傳 1，相等回傳 0。
        """
        if len(args) < 2:
            raise RuntimeError("strcmp: missing arguments")
        s1 = self.memory.read_string(int(args[0]))
        s2 = self.memory.read_string(int(args[1]))
        if s1 < s2:
            return -1
        if s1 > s2:
            return 1
        return 0

    def _strcat(self, args):
        """
        將來源字串接續在目的地字串後方，對應 C 標準函式 strcat()。

        args[0]: 目的地字串的 Memory 位址（需有足夠空間）。
        args[1]: 來源字串的 Memory 位址。

        Returns:
            int: 目的地的 Memory 位址（args[0]）。
        """
        if len(args) < 2:
            raise RuntimeError("strcat: missing arguments")
        s1 = self.memory.read_string(int(args[0]))
        s2 = self.memory.read_string(int(args[1]))
        self.memory.write_string(int(args[0]), s1 + s2)
        return int(args[0])

    # ── 數學運算 ──────────────────────────────────

    def _abs(self, args):
        """
        回傳整數的絕對值。

        args[0]: 輸入整數。

        Returns:
            int: 絕對值。
        """
        if not args:
            raise RuntimeError("abs: missing argument")
        return abs(int(args[0]))

    def _max(self, args):
        """
        回傳兩整數中較大的值。

        args[0], args[1]: 要比較的兩個整數。

        Returns:
            int: 較大的整數。
        """
        if len(args) < 2:
            raise RuntimeError("max: missing arguments")
        return max(int(args[0]), int(args[1]))

    def _min(self, args):
        """
        回傳兩整數中較小的值。

        args[0], args[1]: 要比較的兩個整數。

        Returns:
            int: 較小的整數。
        """
        if len(args) < 2:
            raise RuntimeError("min: missing arguments")
        return min(int(args[0]), int(args[1]))

    def _pow(self, args):
        """
        計算整數次方（base ** exp），結果截斷為整數。
        指數為負數時回傳 0（與 C 整數語意一致）。

        args[0]: 底數（base）。
        args[1]: 指數（exp）。

        Returns:
            int: 次方結果；exp < 0 時回傳 0。
        """
        if len(args) < 2:
            raise RuntimeError("pow: missing arguments")
        base, exp = int(args[0]), int(args[1])
        if exp < 0:
            return 0
        return int(base ** exp)

    def _sqrt(self, args):
        """
        計算整數平方根（無條件捨去），對應 C 的 sqrt() 整數版。

        args[0]: 非負整數輸入值。

        Returns:
            int: 平方根（向下取整）。

        Raises:
            RuntimeError: 輸入值為負數時。
        """
        if not args:
            raise RuntimeError("sqrt: missing argument")
        x = int(args[0])
        if x < 0:
            raise RuntimeError("sqrt: argument must be non-negative")
        return int(math.isqrt(x))

    def _mod(self, args):
        """
        計算兩整數的餘數（a % b）。

        args[0]: 被除數。
        args[1]: 除數。

        Returns:
            int: 餘數。

        Raises:
            RuntimeError: 除數為 0 時。
        """
        if len(args) < 2:
            raise RuntimeError("mod: missing arguments")
        a, b = int(args[0]), int(args[1])
        if b == 0:
            raise RuntimeError("mod: division by zero")
        return a % b

    def _rand(self, args):
        """
        回傳 0 ～ 32767 之間的隨機整數，對應 C 標準函式 rand()。

        Returns:
            int: 隨機整數。
        """
        return random.randint(0, 32767)

    def _srand(self, args):
        """
        設定隨機數種子，對應 C 標準函式 srand()。

        args[0]: 種子值（整數）。

        Returns:
            int: 固定回傳 0。
        """
        if not args:
            raise RuntimeError("srand: missing argument")
        random.seed(int(args[0]))
        return 0

    # ── 記憶體與工具 ──────────────────────────────

    def _memset(self, args):
        """
        將一段連續記憶體填入指定的字元值，對應 C 標準函式 memset()。

        args[0]: 起始 Memory 位址。
        args[1]: 填入的值（以 write_char 寫入，截斷為 8 位元有號整數）。
        args[2]: 填入的單元數量。

        Returns:
            int: 固定回傳 0。
        """
        if len(args) < 3:
            raise RuntimeError("memset: missing arguments")
        ptr, value, size = int(args[0]), int(args[1]), int(args[2])
        for i in range(size):
            self.memory.write_char(ptr + i, value)
        return 0

    def _sizeof_int(self, args):
        """
        回傳 int 型別的大小（位元組數），固定為 4。

        Returns:
            int: 4
        """
        return 4

    def _sizeof_char(self, args):
        """
        回傳 char 型別的大小（位元組數），固定為 1。

        Returns:
            int: 1
        """
        return 1

    def _atoi(self, args):
        """
        將字串轉換為整數，對應 C 標準函式 atoi()。
        若字串無法解析為整數則回傳 0（與 C 行為一致）。

        args[0]: 字串的 Memory 位址。

        Returns:
            int: 解析結果；解析失敗時回傳 0。
        """
        if not args:
            raise RuntimeError("atoi: missing argument")
        s = self.memory.read_string(int(args[0]))
        try:
            return int(s)
        except ValueError:
            return 0

    def _itoa(self, args):
        """
        將整數轉換為字串並寫入 Memory，為 C 常見的 itoa() 簡化實作。

        args[0]: 要轉換的整數值。
        args[1]: 目標字串的 Memory 起始位址（需有足夠空間）。

        Returns:
            int: 固定回傳 0。
        """
        if len(args) < 2:
            raise RuntimeError("itoa: missing arguments")
        value, addr = int(args[0]), int(args[1])
        self.memory.write_string(addr, str(value))
        return 0

    def _exit(self, args):
        """
        終止程式執行，對應 C 標準函式 exit()。
        透過 Python 的 SystemExit 例外將控制權交回直譯器的最外層。

        args[0]: 結束碼（省略時預設為 0）。
        """
        code = int(args[0]) if args else 0
        raise SystemExit(code)