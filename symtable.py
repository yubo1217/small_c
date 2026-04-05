class Symbol:
    def __init__(self, name, var_type, addr, is_pointer=False, is_array=False, array_size=0):
        self.name = name
        self.var_type = var_type  # 'int', 'char', 'void'
        self.addr = addr          # 在 memory 中的位址
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
    def __init__(self, memory):
        self.memory = memory
        self.scopes = [{}]  # scopes[0] 是全域，之後每次函式呼叫 push 一層

    # ----- scope 管理 -----
    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def is_global(self):
        return len(self.scopes) == 1

    # ----- 宣告 -----
    def declare(self, name, var_type, is_pointer=False):
        scope = self.scopes[-1]
        if name in scope:
            raise RuntimeError(f"Variable '{name}' already declared in this scope")
        addr = self.memory.allocate(1)
        self.memory.write(addr, 0)  # 初始化為 0
        symbol = Symbol(name, var_type, addr, is_pointer=is_pointer)
        scope[name] = symbol
        return symbol

    def declare_array(self, name, var_type, size):
        scope = self.scopes[-1]
        if name in scope:
            raise RuntimeError(f"Variable '{name}' already declared in this scope")
        addr = self.memory.allocate(size)
        for i in range(size):
            self.memory.write(addr + i, 0)  # 初始化為 0
        symbol = Symbol(name, var_type, addr, is_array=True, array_size=size)
        scope[name] = symbol
        return symbol

    # ----- 查詢 -----
    def lookup(self, name):
        # 從最內層 scope 往外找
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise RuntimeError(f"Undefined variable '{name}'")

    def lookup_or_none(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # ----- 讀寫值 -----
    def get_value(self, name):
        symbol = self.lookup(name)
        return self.memory.read(symbol.addr)

    def set_value(self, name, value):
        symbol = self.lookup(name)
        if symbol.var_type == 'char' and not symbol.is_pointer:
            self.memory.write_char(symbol.addr, value)
        else:
            self.memory.write(symbol.addr, value)

    # ----- VARS 指令用 -----
    def get_all_globals(self):
        return dict(self.scopes[0])

    # ----- NEW / RUN 時重置 -----
    def reset(self):
        self.scopes = [{}]