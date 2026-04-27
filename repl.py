"""
repl.py — Small-C 互動式直譯器的 REPL 環境
============================================
本模組實作 Small-C 直譯器的互動介面，提供兩大功能：

  1. ReplInputCollector（輸入收集器）
     逐行收集使用者輸入，追蹤大括號深度與註解/字串狀態，
     判斷目前輸入的程式碼片段是否已完整（可送交執行）。
     支援跨行的區塊（如函式定義、控制流程），不強制單行輸入。

  2. REPL（互動環境主體）
     維護程式緩衝區（buffer），提供完整的行編輯指令集，
     並在兩種模式下執行 Small-C 程式碼：
       - 互動模式：直接在提示符後輸入並即時執行。
       - 緩衝模式：透過 APPEND / LOAD 載入完整程式後，以 RUN 執行。

支援的環境指令：
  程式管理：LOAD、SAVE、LIST、EDIT、DELETE、INSERT、APPEND、NEW
  執行控制：RUN、CHECK、TRACE ON/OFF
  狀態查詢：VARS、FUNCS
  系統工具：HELP、ABOUT、CLEAR、QUIT / EXIT

Usage:
    repl = REPL()
    repl.run()   # 啟動互動迴圈
"""

import os
import sys
from lexer import Lexer, preprocess
from parser import Parser, IfStmt, ParseError
from interpreter import Interpreter


# ═══════════════════════════════════════════════════════════
# 多行輸入收集器
# ═══════════════════════════════════════════════════════════

class ReplInputCollector:
    """
    逐行收集互動模式的輸入，追蹤語法狀態以判斷輸入是否完整。

    判斷「完整」的條件：
      - 所有大括號已配對（depth == 0）
      - 不在未閉合的區塊註解（/* ... */）中
      - 字串與字元字面量狀態不影響完整性判斷（換行即視為結束）

    設計動機：
      若使用者輸入的是函式定義或含有 { } 的控制流程，
      需要跨越多行才能構成完整的輸入單元。
      本類別透過逐字元掃描，在不依賴完整 Parser 的情況下，
      輕量地判斷何時可以將累積的原始碼送交執行。

    Attributes:
        source          (str):  目前累積的原始碼字串。
        depth           (int):  目前未配對的左大括號數量。
        in_block_comment (bool): 是否正在區塊註解（/* ... */）內部。
        in_string       (bool): 是否正在字串字面量（" ... "）內部。
        in_char         (bool): 是否正在字元字面量（' ... '）內部。
    """

    def __init__(self):
        """初始化收集器，所有狀態歸零。"""
        self.source = ""
        self.depth = 0
        self.in_block_comment = False
        self.in_string = False
        self.in_char = False

    def feed(self, line: str):
        """
        將一行輸入加入累積的原始碼，並更新語法狀態。

        掃描規則（依狀態優先）：
          - 區塊註解中：尋找 */ 結束符號。
          - 字串中：處理跳脫字元，尋找 " 結束。
          - 字元中：處理跳脫字元，尋找 ' 結束。
          - 一般狀態：識別 //（跳過此行剩餘）、/*、"、'、{ 與 }。

        Args:
            line (str): 使用者輸入的一行原始碼。
        """
        self.source += line + '\n'
        i = 0
        while i < len(line):
            c = line[i]
            if self.in_block_comment:
                if c == '*' and i + 1 < len(line) and line[i + 1] == '/':
                    self.in_block_comment = False
                    i += 1
            elif self.in_string:
                if c == '\\':
                    i += 1  # 跳脫字元：跳過下一個字元
                elif c == '"':
                    self.in_string = False
            elif self.in_char:
                if c == '\\':
                    i += 1  # 跳脫字元：跳過下一個字元
                elif c == "'":
                    self.in_char = False
            else:
                if c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    break  # 單行註解，跳過此行剩餘字元
                elif c == '/' and i + 1 < len(line) and line[i + 1] == '*':
                    self.in_block_comment = True
                elif c == '"':
                    self.in_string = True
                elif c == "'":
                    self.in_char = True
                elif c == '{':
                    self.depth += 1
                elif c == '}':
                    self.depth -= 1
            i += 1

    def is_complete(self) -> bool:
        """
        判斷目前累積的輸入是否構成完整的程式碼片段。

        Returns:
            bool: 大括號已全部配對且不在區塊註解中時為 True。
        """
        return self.depth == 0 and not self.in_block_comment

    def reset(self):
        """清除所有累積的輸入與語法狀態，準備收集下一個輸入單元。"""
        self.source = ""
        self.depth = 0
        self.in_block_comment = False
        self.in_string = False
        self.in_char = False


# ═══════════════════════════════════════════════════════════
# REPL 互動環境主體
# ═══════════════════════════════════════════════════════════

class REPL:
    """
    Small-C 互動式直譯器的 REPL 環境。

    維護一個程式緩衝區（buffer），使用者可透過行編輯指令修改程式碼，
    也可在提示符後直接輸入 Small-C 程式碼並即時執行。

    Attributes:
        interpreter (Interpreter): Small-C 直譯器實例，共享於所有執行模式。
        buffer      (list[str]):   程式碼緩衝區，每個元素為一行字串。
        modified    (bool):        緩衝區是否有尚未儲存的修改。
        trace       (bool):        TRACE 模式是否啟用。
    """

    # 所有可識別的環境指令（小寫）
    COMMANDS = {
        'load', 'save', 'list', 'edit', 'delete', 'insert',
        'append', 'new', 'run', 'check', 'trace', 'vars',
        'funcs', 'help', 'about', 'clear', 'quit', 'exit',
    }

    def __init__(self):
        """初始化 REPL，建立空的緩衝區與直譯器。"""
        self.interpreter = Interpreter()
        self.buffer = []
        self.modified = False
        self.trace = False

    def _is_command(self, line: str) -> bool:
        """
        判斷輸入的第一個詞是否為環境指令。

        Args:
            line (str): 使用者輸入的一行文字。

        Returns:
            bool: 第一個詞屬於 COMMANDS 集合時為 True。
        """
        first = line.strip().split()[0].lower() if line.strip() else ''
        return first in self.COMMANDS

    # ── 主迴圈 ────────────────────────────────────

    def run(self):
        """
        啟動 REPL 互動迴圈，持續讀取輸入直到 EOF 或 QUIT 指令。

        輸入處理邏輯：
          1. 若輸入為空行且目前無累積輸入，直接忽略。
          2. 若為第一行且是環境指令，直接分派給 handle_command()。
          3. 其他情況交給 ReplInputCollector 累積。
          4. 一旦收集器判斷輸入完整，送交 execute_interactive() 執行。

        提示符：
          - 初始狀態顯示 "sc> "。
          - 輸入跨行時顯示 "  > " 表示等待續行。
        """
        print("=" * 44)
        print(" Small-C Interactive Interpreter v1.0")
        print(" System Software Final Project, Spring 2026")
        print("=" * 44)
        print("Type `HELP` for a list of commands.")
        print()

        collector = ReplInputCollector()
        # 延遲執行暫存區：if-stmt 完成後先暫存，
        # 等下一行確認是否為 else 再決定執行或合併。
        pending_source = None

        while True:
            prompt = "sc> " if not collector.source else "  > "
            try:
                line = input(prompt)
            except EOFError:
                print()
                # 離開前先執行暫存中的 if-stmt
                if pending_source:
                    self._execute_interactive(pending_source)
                break

            stripped = line.strip()

            # ── 暫存 if-stmt 的 else 銜接檢查 ──────────
            if pending_source is not None and not collector.source:
                if stripped.startswith('else'):
                    # 此行是 else：將暫存源碼合入 collector 再繼續收集
                    collector.source = pending_source + '\n'
                    pending_source = None
                    collector.feed(line)
                    if collector.is_complete():
                        source = collector.source.strip()
                        collector.reset()
                        if source:
                            pending_source = source  # 可能再跟 else
                    continue
                elif stripped:
                    # 非空且非 else：執行暫存的 if-stmt，再處理此行
                    self._execute_interactive(pending_source)
                    pending_source = None
                    # 不 continue，繼續往下處理此行
                else:
                    # 空行：繼續等待，不消費暫存
                    continue

            if not stripped:
                if collector.source:
                    collector.feed(line)
                continue

            if not collector.source and self._is_command(line):
                self._handle_command(line.strip())
                continue

            collector.feed(line)

            if collector.is_complete():
                source = collector.source.strip()
                collector.reset()
                if source:
                    # 僅 if-stmt（無 else）才延遲執行，等待可能的 else
                    try:
                        prog = Parser(preprocess(source)).parse()
                        last = prog.decls[-1] if prog.decls else None
                        if isinstance(last, IfStmt) and last.else_branch is None:
                            pending_source = source
                        else:
                            self._execute_interactive(source)
                    except Exception:
                        self._execute_interactive(source)

    # ── 互動執行 ──────────────────────────────────

    def _execute_interactive(self, source: str):
        """
        對單段原始碼進行前處理、解析並直接執行（互動模式）。
        執行期間的錯誤與程式終止均捕捉後印出訊息，不中斷 REPL 迴圈。

        錯誤訊息格式：
          - 詞法 / 語法錯誤：'Syntax error: <msg>'（不含行號，符合 spec 範例 16）
          - 執行期錯誤：訊息已自帶 'Runtime error: ' 前綴則原樣輸出，
                      否則加上前綴後輸出
          - 其他例外：以通用 'Error: <msg>' 顯示

        Args:
            source (str): 要執行的 Small-C 原始碼字串。
        """
        try:
            source = preprocess(source)
            parser = Parser(source)
            program = parser.parse()
            self.interpreter.execute_interactive(program)
        except SystemExit as e:
            print(f"Program exited with return value {e.code}.")
        except ParseError as e:
            print(f"Syntax error: {e.msg}")
        except RuntimeError as e:
            print(self._format_runtime(e))
        except Exception as e:
            print(f"Error: {e}")

    @staticmethod
    def _format_runtime(e: Exception) -> str:
        """
        將執行期錯誤訊息標準化為 'Runtime error: <msg>' 格式。
        若訊息已自帶相符前綴則原樣返回，避免重複加註。
        """
        msg = str(e)
        if msg.startswith("Runtime error:"):
            return msg
        return f"Runtime error: {msg}"

    # ── 環境指令分派 ──────────────────────────────

    def _handle_command(self, line: str):
        """
        解析並分派環境指令到對應的處理方法。

        Args:
            line (str): 去除前後空白的完整指令字串。
        """
        parts = line.split()
        cmd = parts[0].lower()

        dispatch = {
            'load':   lambda: self._cmd_load(parts),
            'save':   lambda: self._cmd_save(parts),
            'list':   lambda: self._cmd_list(parts),
            'edit':   lambda: self._cmd_edit(parts),
            'delete': lambda: self._cmd_delete(parts),
            'insert': lambda: self._cmd_insert(parts),
            'append': lambda: self._cmd_append(),
            'new':    lambda: self._cmd_new(),
            'run':    lambda: self._cmd_run(),
            'check':  lambda: self._cmd_check(),
            'trace':  lambda: self._cmd_trace(parts),
            'vars':   lambda: self._cmd_vars(),
            'funcs':  lambda: self._cmd_funcs(),
            'help':   lambda: self._cmd_help(parts),
            'about':  lambda: self._cmd_about(),
            'clear':  lambda: os.system('clear' if os.name != 'nt' else 'cls'),
            'quit':   lambda: self._cmd_quit(),
            'exit':   lambda: self._cmd_quit(),
        }
        if cmd in dispatch:
            dispatch[cmd]()

    # ── 程式管理指令 ──────────────────────────────

    def _cmd_load(self, parts):
        """
        從檔案載入 Small-C 原始碼到緩衝區。
        若緩衝區有未儲存的修改，會先詢問是否放棄。

        用法：LOAD <filename>
        """
        if len(parts) < 2:
            print("Usage: LOAD <filename>")
            return
        filename = parts[1]
        if self.modified:
            try:
                ans = input("Buffer has unsaved changes. Discard? (y/n): ").strip().lower()
            except EOFError:
                print()
                return
            if ans != 'y':
                return
        try:
            with open(filename, 'r') as f:
                lines = f.read().splitlines()
            self.buffer = lines
            self.modified = False
            self.interpreter.reset()
            print(f"Loaded {len(lines)} lines from '{filename}'.")
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except Exception as e:
            print(f"Error: {e}")

    def _cmd_save(self, parts):
        """
        將緩衝區內容儲存到指定檔案。

        用法：SAVE <filename>
        """
        if len(parts) < 2:
            print("Usage: SAVE <filename>")
            return
        filename = parts[1]
        try:
            with open(filename, 'w') as f:
                f.write('\n'.join(self.buffer) + '\n')
            self.modified = False
            print(f"Saved {len(self.buffer)} lines to '{filename}'.")
        except Exception as e:
            print(f"Error: {e}")

    def _cmd_list(self, parts):
        """
        列出緩衝區中的指定行或範圍，每行前顯示行號。

        用法：
          LIST          → 列出全部內容
          LIST <n>      → 列出第 n 行
          LIST <n1>-<n2> → 列出第 n1 到 n2 行
        """
        if not self.buffer:
            print("Buffer is empty.")
            return
        try:
            if len(parts) == 1:
                start, end = 1, len(self.buffer)
            elif len(parts) == 2:
                if '-' in parts[1]:
                    n1, n2 = parts[1].split('-')
                    start, end = int(n1), int(n2)
                else:
                    start = end = int(parts[1])
            else:
                print("Usage: LIST / LIST <n> / LIST <n1>-<n2>")
                return
        except ValueError:
            print("Invalid line number.")
            return

        for i in range(start, end + 1):
            if 1 <= i <= len(self.buffer):
                print(f"{i:4}: {self.buffer[i - 1]}")

    def _cmd_edit(self, parts):
        """
        顯示指定行的現有內容並等待使用者輸入新內容取代。
        若使用者直接按 Enter（輸入為空），則保留原始內容不修改。

        用法：EDIT <n>
        """
        if len(parts) < 2:
            print("Usage: EDIT <n>")
            return
        try:
            n = int(parts[1])
        except ValueError:
            print("Invalid line number.")
            return
        if n < 1 or n > len(self.buffer):
            print(f"Error: Line {n} out of range.")
            return
        print(f"{n:4}: {self.buffer[n - 1]}")
        try:
            new_line = input(f"{n:4}: ")
        except EOFError:
            print()
            return
        if new_line:
            self.buffer[n - 1] = new_line
            self.modified = True

    def _cmd_delete(self, parts):
        """
        從緩衝區刪除指定行或範圍的行，後續行號自動遞減。

        用法：
          DELETE <n>        → 刪除第 n 行
          DELETE <n1>-<n2>  → 刪除第 n1 到 n2 行
        """
        try:
            if len(parts) == 2:
                if '-' in parts[1]:
                    n1, n2 = parts[1].split('-')
                    start, end = int(n1), int(n2)
                else:
                    start = end = int(parts[1])
            else:
                print("Usage: DELETE <n> / DELETE <n1>-<n2>")
                return
        except ValueError:
            print("Invalid line number.")
            return

        if start < 1 or end > len(self.buffer) or start > end:
            print("Error: Line number out of range.")
            return

        del self.buffer[start - 1:end]
        self.modified = True

    def _cmd_insert(self, parts):
        """
        在指定行號前插入一或多行內容，以單獨一行的 '.' 結束輸入。
        插入後，原本該行號以後的所有行號依序遞增。

        用法：INSERT <n>
        """
        if len(parts) < 2:
            print("Usage: INSERT <n>")
            return
        try:
            n = int(parts[1])
        except ValueError:
            print("Invalid line number.")
            return
        if n < 1 or n > len(self.buffer) + 1:
            print("Error: Line number out of range.")
            return

        print("Enter lines (type '.' to finish):")
        insert_lines = []
        line_num = n
        while True:
            try:
                line = input(f"{line_num:4}> ")
            except EOFError:
                print()
                break
            if line.strip() == '.':
                break
            insert_lines.append(line)
            line_num += 1

        self.buffer[n - 1:n - 1] = insert_lines
        self.modified = True

    def _cmd_append(self):
        """
        在緩衝區末尾追加一或多行內容，以單獨一行的 '.' 結束輸入。

        用法：APPEND
        """
        print("Enter lines (type '.' to finish):")
        line_num = len(self.buffer) + 1
        while True:
            try:
                line = input(f"{line_num:4}> ")
            except EOFError:
                print()
                break
            if line.strip() == '.':
                break
            self.buffer.append(line)
            self.modified = True
            line_num += 1

    def _cmd_new(self):
        """
        清空緩衝區並重置直譯器狀態。
        若有未儲存的修改，會先詢問是否放棄。

        用法：NEW
        """
        if self.modified:
            try:
                ans = input("Buffer has unsaved changes. Discard? (y/n): ").strip().lower()
            except EOFError:
                print()
                return
            if ans != 'y':
                return
        self.buffer = []
        self.modified = False
        self.interpreter.reset()
        print("All cleared.")

    # ── 執行指令 ──────────────────────────────────

    def _cmd_run(self):
        """
        對緩衝區中的完整程式進行前處理、解析並執行。
        執行前會重置直譯器狀態，並套用目前的 TRACE 設定。
        執行結果與錯誤訊息均印出後回到提示符。

        錯誤訊息格式：
          - 詞法 / 語法錯誤：'Error at line <n>: <msg>'（緩衝區行號有意義）
          - 執行期錯誤：'Runtime error: <msg>'

        用法：RUN
        """
        if not self.buffer:
            print("Error: Buffer is empty.")
            return
        source = '\n'.join(self.buffer)
        try:
            source = preprocess(source)
            self.interpreter.reset()
            self.interpreter.trace = self.trace
            parser = Parser(source)
            program = parser.parse()
            ret = self.interpreter.execute(program)
            print(f"Program exited with return value {ret}.")
        except SystemExit as e:
            print(f"Program exited with return value {e.code}.")
        except ParseError as e:
            print(f"Error at line {e.line}: {e.msg}")
        except RuntimeError as e:
            print(self._format_runtime(e))
        except Exception as e:
            print(f"Error: {e}")

    def _cmd_check(self):
        """
        對緩衝區中的程式碼進行語法檢查，不實際執行。
        若有語法錯誤，依照 spec 範例 16 的格式輸出 'Error at line <n>: <msg>'。
        無錯誤時印出 'No errors found.'。

        用法：CHECK
        """
        if not self.buffer:
            print("Buffer is empty.")
            return
        source = '\n'.join(self.buffer)
        errors = []
        try:
            source = preprocess(source)
            parser = Parser(source)
            parser.parse()
        except ParseError as e:
            errors.append(f"Error at line {e.line}: {e.msg}")
        except Exception as e:
            errors.append(f"Error: {e}")

        if errors:
            for err in errors:
                print(err)
            print(f"{len(errors)} error(s) found.")
        else:
            print("No errors found.")

    def _cmd_trace(self, parts):
        """
        啟用或關閉 TRACE 模式。啟用時，直譯器執行每個 AST 節點前
        會在輸出中印出 [line n] <statement> 追蹤資訊，方便除錯。

        用法：TRACE ON / TRACE OFF
        """
        if len(parts) < 2:
            print("Usage: TRACE ON / TRACE OFF")
            return
        mode = parts[1].lower()
        if mode == 'on':
            self.trace = True
            self.interpreter.trace = True
            print("Trace mode enabled.")
        elif mode == 'off':
            self.trace = False
            self.interpreter.trace = False
            print("Trace mode disabled.")
        else:
            print("Usage: TRACE ON / TRACE OFF")

    def _cmd_vars(self):
        """
        顯示目前直譯器中所有全域變數的名稱、型別與數值。

        輸出格式：
          - 一般變數：int x = 42
          - char 變數：char c = 65 (A)（同時顯示 ASCII 字元）
          - 指標：int *p = 1024（顯示所指位址）
          - 陣列：int arr[8] = {1, 2, 3, ...}（最多顯示前 10 個元素）

        用法：VARS
        """
        globals_ = self.interpreter.symtable.get_all_globals()
        if not globals_:
            print("No global variables.")
            return
        for name, symbol in globals_.items():
            if symbol.is_array:
                elements = []
                for i in range(min(symbol.array_size, 10)):
                    elements.append(str(self.interpreter.memory.read(symbol.addr + i)))
                elems_str = '{' + ', '.join(elements)
                if symbol.array_size > 10:
                    elems_str += ', ...'
                elems_str += '}'
                print(f"  {symbol.var_type} {name}[{symbol.array_size}] = {elems_str}")
            elif symbol.is_pointer:
                addr = self.interpreter.memory.read(symbol.addr)
                print(f"  {symbol.var_type} *{name} = {addr}")
            else:
                val = self.interpreter.memory.read(symbol.addr)
                if symbol.var_type == 'char':
                    ch_repr = f"'{chr(val)}'" if 32 <= val <= 126 else "'?'"
                    print(f"  char {name} = {val} ({ch_repr})")
                else:
                    print(f"  int {name} = {val}")

    def _cmd_funcs(self):
        """
        列出目前直譯器中所有已定義的函式（含使用者定義與內建函式）。

        使用者定義函式顯示回傳型別、名稱與參數列表；
        內建函式一律標示 [built-in]。

        用法：FUNCS
        """
        if self.interpreter.functions:
            for name, func in self.interpreter.functions.items():
                params = ', '.join(
                    f"{p.var_type} {'*' if p.is_pointer else ''}{p.name}"
                    for p in func.params
                )
                star = '*' if getattr(func, 'is_pointer', False) else ''
                line_info = f"    line {func.line}" if getattr(func, 'line', 0) else ''
                print(f"  {func.ret_type} {star}{name}({params}){line_info}")

        print("  --- built-in functions ---")
        builtins_list = [
            "int putchar(int ch)",
            "int getchar()",
            "void printf(char *fmt, ...)",
            "void puts(char *s)",
            "int scanf(char *fmt, ...)",
            "int strlen(char *s)",
            "void strcpy(char *dest, char *src)",
            "int strcmp(char *s1, char *s2)",
            "void strcat(char *dest, char *src)",
            "int abs(int x)",
            "int max(int a, int b)",
            "int min(int a, int b)",
            "int pow(int base, int exp)",
            "int sqrt(int x)",
            "int mod(int a, int b)",
            "int rand()",
            "void srand(int seed)",
            "void memset(char *ptr, int value, int size)",
            "int sizeof_int()",
            "int sizeof_char()",
            "int atoi(char *s)",
            "void itoa(int value, char *str)",
            "void exit(int code)",
        ]
        for b in builtins_list:
            print(f"  {b}  [built-in]")

    # ── 系統工具指令 ──────────────────────────────

    def _cmd_help(self, parts):
        """
        顯示所有可用指令的摘要，或特定指令的詳細說明。

        用法：
          HELP        → 列出所有指令摘要
          HELP <cmd>  → 顯示指定指令的詳細說明
        """
        if len(parts) >= 2:
            self._show_help_detail(parts[1].lower())
            return
        print("Available commands:")
        helps = [
            ("LOAD <file>",        "Load source file into buffer"),
            ("SAVE <file>",        "Save buffer to file"),
            ("LIST [n|n1-n2]",     "List buffer contents"),
            ("EDIT <n>",           "Edit line n"),
            ("DELETE <n|n1-n2>",   "Delete line(s)"),
            ("INSERT <n>",         "Insert lines before line n"),
            ("APPEND",             "Append lines to end of buffer"),
            ("NEW",                "Clear buffer and reset state"),
            ("RUN",                "Run program in buffer"),
            ("CHECK",              "Check syntax without running"),
            ("TRACE ON|OFF",       "Enable/disable trace mode"),
            ("VARS",               "Show all global variables"),
            ("FUNCS",              "List all defined functions"),
            ("HELP [cmd]",         "Show help"),
            ("ABOUT",              "Show interpreter info"),
            ("CLEAR",              "Clear screen"),
            ("QUIT / EXIT",        "Exit interpreter"),
        ]
        for cmd, desc in helps:
            print(f"  {cmd:<20} {desc}")

    def _show_help_detail(self, cmd: str):
        """
        顯示單一指令的詳細說明文字。

        Args:
            cmd (str): 指令名稱（小寫）。
        """
        details = {
            'load':   "LOAD <filename> - Load a Small-C source file into the program buffer.",
            'save':   "SAVE <filename> - Save the current buffer to a file.",
            'list':   "LIST / LIST <n> / LIST <n1>-<n2> - List buffer contents.",
            'edit':   "EDIT <n> - Show line n and allow editing.",
            'delete': "DELETE <n> / DELETE <n1>-<n2> - Delete line(s) from buffer.",
            'insert': "INSERT <n> - Insert lines before line n. End with '.'",
            'append': "APPEND - Append lines to end of buffer. End with '.'",
            'new':    "NEW - Clear buffer and reset all state.",
            'run':    "RUN - Execute the program in the buffer.",
            'check':  "CHECK - Check syntax and semantics without executing.",
            'trace':  "TRACE ON/OFF - Enable or disable trace mode.",
            'vars':   "VARS - Display all global variables and their values.",
            'funcs':  "FUNCS - List all defined functions.",
            'quit':   "QUIT / EXIT - Exit the interpreter.",
        }
        print(details.get(cmd, f"No detailed help for '{cmd}'."))

    def _cmd_about(self):
        """顯示直譯器的名稱、版本、作者與學期資訊。"""
        print("Small-C Interactive Interpreter v1.0")
        print("作者：Yubo Lin")
        print("System Software Final Project, Spring 2026")

    def _cmd_quit(self):
        """
        退出直譯器。若緩衝區有未儲存的修改，會先詢問是否放棄後再離開。

        用法：QUIT / EXIT
        """
        if self.modified:
            try:
                ans = input("Buffer has unsaved changes. Discard and quit? (y/n): ").strip().lower()
            except EOFError:
                ans = 'y'
            if ans != 'y':
                return
        print("Goodbye.")
        sys.exit(0)