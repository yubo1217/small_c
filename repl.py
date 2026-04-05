import os
import sys
from lexer import Lexer, preprocess
from parser import Parser
from interpreter import Interpreter

class ReplInputCollector:
    def __init__(self):
        self.source = ""
        self.depth = 0
        self.in_block_comment = False
        self.in_string = False
        self.in_char = False

    def feed(self, line):
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
                    i += 1
                elif c == '"':
                    self.in_string = False
            elif self.in_char:
                if c == '\\':
                    i += 1
                elif c == "'":
                    self.in_char = False
            else:
                if c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    break  # 單行註解，跳過此行剩餘
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

    def is_complete(self):
        return self.depth == 0 and not self.in_block_comment

    def reset(self):
        self.source = ""
        self.depth = 0
        self.in_block_comment = False
        self.in_string = False
        self.in_char = False


class REPL:
    def __init__(self):
        self.interpreter = Interpreter()
        self.buffer = []        # 程式緩衝區，每個元素是一行字串
        self.modified = False   # 緩衝區是否有未儲存的修改
        self.trace = False

    COMMANDS = {
        'load', 'save', 'list', 'edit', 'delete', 'insert',
        'append', 'new', 'run', 'check', 'trace', 'vars',
        'funcs', 'help', 'about', 'clear', 'quit', 'exit',
    }

    def is_command(self, line):
        first = line.strip().split()[0].lower() if line.strip() else ''
        return first in self.COMMANDS

    # ----- 主迴圈 -----
    def run(self):
        print("=" * 42)
        print("  Small-C Interactive Interpreter v1.0")
        print("  System Software Final Project, Spring 2026")
        print("=" * 42)
        print("Type `HELP` for a list of commands.")
        print()

        collector = ReplInputCollector()

        while True:
            prompt = "sc> " if not collector.source else "  > "
            try:
                line = input(prompt)
            except EOFError:
                print()
                break

            # 空行
            if not line.strip():
                if collector.source:
                    collector.feed(line)
                continue

            # 第一行且是環境指令
            if not collector.source and self.is_command(line):
                self.handle_command(line.strip())
                continue

            collector.feed(line)

            if collector.is_complete():
                source = collector.source.strip()
                collector.reset()
                if source:
                    self.execute_interactive(source)

    # ----- 互動執行 -----
    def execute_interactive(self, source):
        try:
            source = preprocess(source)
            parser = Parser(source)
            program = parser.parse()
            self.interpreter.execute_interactive(program)
        except SystemExit as e:
            print(f"Program exited with return value {e.code}.")
        except Exception as e:
            print(f"Error: {e}")

    # ----- 環境指令分派 -----
    def handle_command(self, line):
        parts = line.split()
        cmd = parts[0].lower()

        if cmd == 'load':
            self.cmd_load(parts)
        elif cmd == 'save':
            self.cmd_save(parts)
        elif cmd == 'list':
            self.cmd_list(parts)
        elif cmd == 'edit':
            self.cmd_edit(parts)
        elif cmd == 'delete':
            self.cmd_delete(parts)
        elif cmd == 'insert':
            self.cmd_insert(parts)
        elif cmd == 'append':
            self.cmd_append()
        elif cmd == 'new':
            self.cmd_new()
        elif cmd == 'run':
            self.cmd_run()
        elif cmd == 'check':
            self.cmd_check()
        elif cmd == 'trace':
            self.cmd_trace(parts)
        elif cmd == 'vars':
            self.cmd_vars()
        elif cmd == 'funcs':
            self.cmd_funcs()
        elif cmd == 'help':
            self.cmd_help(parts)
        elif cmd == 'about':
            self.cmd_about()
        elif cmd == 'clear':
            os.system('clear' if os.name != 'nt' else 'cls')
        elif cmd in ('quit', 'exit'):
            self.cmd_quit()

    # ----- 程式管理指令 -----
    def cmd_load(self, parts):
        if len(parts) < 2:
            print("Usage: LOAD <filename>")
            return
        filename = parts[1]
        if self.modified:
            ans = input("Buffer has unsaved changes. Discard? (y/n): ").strip().lower()
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

    def cmd_save(self, parts):
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

    def cmd_list(self, parts):
        if not self.buffer:
            print("Buffer is empty.")
            return
        # 解析範圍
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

    def cmd_edit(self, parts):
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
        new_line = input(f"{n:4}: ")
        if new_line:
            self.buffer[n - 1] = new_line
            self.modified = True

    def cmd_delete(self, parts):
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

        if start < 1 or end > len(self.buffer):
            print("Error: Line number out of range.")
            return

        del self.buffer[start - 1:end]
        self.modified = True

    def cmd_insert(self, parts):
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
            line = input(f"{line_num:4}> ")
            if line.strip() == '.':
                break
            insert_lines.append(line)
            line_num += 1

        self.buffer[n - 1:n - 1] = insert_lines
        self.modified = True

    def cmd_append(self):
        print("Enter lines (type '.' to finish):")
        line_num = len(self.buffer) + 1
        while True:
            line = input(f"{line_num:4}> ")
            if line.strip() == '.':
                break
            self.buffer.append(line)
            self.modified = True
            line_num += 1

    def cmd_new(self):
        if self.modified:
            ans = input("Buffer has unsaved changes. Discard? (y/n): ").strip().lower()
            if ans != 'y':
                return
        self.buffer = []
        self.modified = False
        self.interpreter.reset()
        print("All cleared.")

    # ----- 執行指令 -----
    def cmd_run(self):
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
            if ret is not None:
                print(f"Program exited with return value {ret}.")
        except SystemExit as e:
            print(f"Program exited with return value {e.code}.")
        except Exception as e:
            print(f"Error: {e}")

    def cmd_check(self):
        if not self.buffer:
            print("Buffer is empty.")
            return
        source = '\n'.join(self.buffer)
        errors = []
        try:
            source = preprocess(source)
            parser = Parser(source)
            parser.parse()
        except Exception as e:
            errors.append(str(e))

        if errors:
            for err in errors:
                print(err)
            print(f"{len(errors)} error(s) found.")
        else:
            print("No errors found.")

    def cmd_trace(self, parts):
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

    def cmd_vars(self):
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
                    print(f"  char {name} = {val} ({chr(val) if 32 <= val <= 126 else '?'})")
                else:
                    print(f"  int {name} = {val}")

    def cmd_funcs(self):
        if self.interpreter.functions:
            for name, func in self.interpreter.functions.items():
                params = ', '.join(
                    f"{p.var_type} {'*' if p.is_pointer else ''}{p.name}"
                    for p in func.params
                )
                # 找起始行號（暫時沒有行號資訊就顯示 ?）
                print(f"  {func.ret_type} {name}({params})")
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

    # ----- 系統指令 -----
    def cmd_help(self, parts):
        if len(parts) >= 2:
            self.show_help_detail(parts[1].lower())
            return
        print("Available commands:")
        helps = [
            ("LOAD <file>",       "Load source file into buffer"),
            ("SAVE <file>",       "Save buffer to file"),
            ("LIST [n|n1-n2]",    "List buffer contents"),
            ("EDIT <n>",          "Edit line n"),
            ("DELETE <n|n1-n2>",  "Delete line(s)"),
            ("INSERT <n>",        "Insert lines before line n"),
            ("APPEND",            "Append lines to end of buffer"),
            ("NEW",               "Clear buffer and reset state"),
            ("RUN",               "Run program in buffer"),
            ("CHECK",             "Check syntax without running"),
            ("TRACE ON|OFF",      "Enable/disable trace mode"),
            ("VARS",              "Show all global variables"),
            ("FUNCS",             "List all defined functions"),
            ("HELP [cmd]",        "Show help"),
            ("ABOUT",             "Show interpreter info"),
            ("CLEAR",             "Clear screen"),
            ("QUIT / EXIT",       "Exit interpreter"),
        ]
        for cmd, desc in helps:
            print(f"  {cmd:<20} {desc}")

    def show_help_detail(self, cmd):
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

    def cmd_about(self):
        print("Small-C Interactive Interpreter v1.0")
        print("System Software Final Project, Spring 2026")

    def cmd_quit(self):
        if self.modified:
            ans = input("Buffer has unsaved changes. Discard and quit? (y/n): ").strip().lower()
            if ans != 'y':
                return
        print("Goodbye.")
        sys.exit(0)