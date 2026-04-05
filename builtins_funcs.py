import sys
import math
import random

class Builtins:
    def __init__(self, memory):
        self.memory = memory
        self._rand_seed = 1

    def call(self, name, args):
        dispatch = {
            'printf':       self._printf,
            'putchar':      self._putchar,
            'getchar':      self._getchar,
            'puts':         self._puts,
            'scanf':        self._scanf,
            'strlen':       self._strlen,
            'strcpy':       self._strcpy,
            'strcmp':       self._strcmp,
            'strcat':       self._strcat,
            'abs':          self._abs,
            'max':          self._max,
            'min':          self._min,
            'pow':          self._pow,
            'sqrt':         self._sqrt,
            'mod':          self._mod,
            'rand':         self._rand,
            'srand':        self._srand,
            'memset':       self._memset,
            'sizeof_int':   self._sizeof_int,
            'sizeof_char':  self._sizeof_char,
            'atoi':         self._atoi,
            'itoa':         self._itoa,
            'exit':         self._exit,
        }
        if name not in dispatch:
            raise RuntimeError(f"Unknown builtin function '{name}'")
        return dispatch[name](args)

    def is_builtin(self, name):
        return name in {
            'printf', 'putchar', 'getchar', 'puts', 'scanf',
            'strlen', 'strcpy', 'strcmp', 'strcat',
            'abs', 'max', 'min', 'pow', 'sqrt', 'mod',
            'rand', 'srand', 'memset', 'sizeof_int', 'sizeof_char',
            'atoi', 'itoa', 'exit',
        }

    # ----- 輸入輸出 -----
    def _printf(self, args):
        if not args:
            raise RuntimeError("printf: missing format string")
        fmt_addr = args[0]
        fmt = self.memory.read_string(fmt_addr)
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
        if not args:
            raise RuntimeError("putchar: missing argument")
        ch = int(args[0]) & 0xFF
        sys.stdout.write(chr(ch))
        sys.stdout.flush()
        return ch

    def _getchar(self, args):
        ch = sys.stdin.read(1)
        if not ch:
            return -1
        return ord(ch)

    def _puts(self, args):
        if not args:
            raise RuntimeError("puts: missing argument")
        s = self.memory.read_string(int(args[0]))
        sys.stdout.write(s + '\n')
        sys.stdout.flush()
        return 0

    def _scanf(self, args):
        if not args:
            raise RuntimeError("scanf: missing format string")
        fmt_addr = args[0]
        fmt = self.memory.read_string(fmt_addr)
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

    # ----- 字串 -----
    def _strlen(self, args):
        if not args:
            raise RuntimeError("strlen: missing argument")
        return len(self.memory.read_string(int(args[0])))

    def _strcpy(self, args):
        if len(args) < 2:
            raise RuntimeError("strcpy: missing arguments")
        src = self.memory.read_string(int(args[1]))
        self.memory.write_string(int(args[0]), src)
        return int(args[0])

    def _strcmp(self, args):
        if len(args) < 2:
            raise RuntimeError("strcmp: missing arguments")
        s1 = self.memory.read_string(int(args[0]))
        s2 = self.memory.read_string(int(args[1]))
        if s1 < s2: return -1
        if s1 > s2: return 1
        return 0

    def _strcat(self, args):
        if len(args) < 2:
            raise RuntimeError("strcat: missing arguments")
        s1 = self.memory.read_string(int(args[0]))
        s2 = self.memory.read_string(int(args[1]))
        self.memory.write_string(int(args[0]), s1 + s2)
        return int(args[0])

    # ----- 數學 -----
    def _abs(self, args):
        if not args:
            raise RuntimeError("abs: missing argument")
        return abs(int(args[0]))

    def _max(self, args):
        if len(args) < 2:
            raise RuntimeError("max: missing arguments")
        return max(int(args[0]), int(args[1]))

    def _min(self, args):
        if len(args) < 2:
            raise RuntimeError("min: missing arguments")
        return min(int(args[0]), int(args[1]))

    def _pow(self, args):
        if len(args) < 2:
            raise RuntimeError("pow: missing arguments")
        base, exp = int(args[0]), int(args[1])
        if exp < 0:
            return 0
        return int(base ** exp)

    def _sqrt(self, args):
        if not args:
            raise RuntimeError("sqrt: missing argument")
        x = int(args[0])
        if x < 0:
            raise RuntimeError("sqrt: argument must be non-negative")
        return int(math.isqrt(x))

    def _mod(self, args):
        if len(args) < 2:
            raise RuntimeError("mod: missing arguments")
        a, b = int(args[0]), int(args[1])
        if b == 0:
            raise RuntimeError("mod: division by zero")
        return a % b

    def _rand(self, args):
        return random.randint(0, 32767)

    def _srand(self, args):
        if not args:
            raise RuntimeError("srand: missing argument")
        random.seed(int(args[0]))
        return 0

    # ----- 記憶體工具 -----
    def _memset(self, args):
        if len(args) < 3:
            raise RuntimeError("memset: missing arguments")
        ptr, value, size = int(args[0]), int(args[1]), int(args[2])
        for i in range(size):
            self.memory.write_char(ptr + i, value)
        return 0

    def _sizeof_int(self, args):
        return 4

    def _sizeof_char(self, args):
        return 1

    def _atoi(self, args):
        if not args:
            raise RuntimeError("atoi: missing argument")
        s = self.memory.read_string(int(args[0]))
        try:
            return int(s)
        except ValueError:
            return 0

    def _itoa(self, args):
        if len(args) < 2:
            raise RuntimeError("itoa: missing arguments")
        value, addr = int(args[0]), int(args[1])
        self.memory.write_string(addr, str(value))
        return 0

    def _exit(self, args):
        code = int(args[0]) if args else 0
        raise SystemExit(code)