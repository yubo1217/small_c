from parser import (
    Program, FuncDef, VarDecl, ArrayDecl, Block,
    IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    BreakStmt, ContinueStmt, Return,
    BinOp, UnaryOp, Assignment, Call,
    Identifier, Number, Char, StringLiteral,
    AddressOf, Deref, ArrayAccess,
)
from symtable import SymbolTable
from memory import Memory
from builtins_funcs import Builtins

# ----- 控制流例外 -----
class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

# ----- Interpreter -----
class Interpreter:
    def __init__(self):
        self.memory = Memory()
        self.symtable = SymbolTable(self.memory)
        self.builtins = Builtins(self.memory)
        self.functions = {}   # name -> FuncDef AST node
        self.trace = False    # TRACE ON/OFF

    def reset(self):
        self.memory.reset()
        self.symtable.reset()
        self.functions = {}
        self.trace = False

    # ----- 執行入口 -----
    def execute(self, program):
        """執行整個 Program（檔案模式或 RUN 指令）"""
        # 第一遍：收集函式定義和全域變數
        for decl in program.decls:
            if isinstance(decl, FuncDef):
                self.functions[decl.name] = decl
            elif isinstance(decl, (VarDecl, ArrayDecl)):
                self.exec_decl(decl)

        # 第二遍：執行 main
        if 'main' not in self.functions:
            raise RuntimeError("No main() function defined")
        return self.call_function('main', [])

    def execute_interactive(self, program):
        """互動模式：直接執行片段，不需要 main"""
        for decl in program.decls:
            if isinstance(decl, FuncDef):
                self.functions[decl.name] = decl
            elif isinstance(decl, (VarDecl, ArrayDecl)):
                self.exec_decl(decl)
            else:
                self.exec_stmt(decl)

    # ----- 宣告 -----
    def exec_decl(self, node):
        if isinstance(node, VarDecl):
            symbol = self.symtable.declare(node.name, node.var_type, node.is_pointer)
            if node.value is not None:
                val = self.eval_expr(node.value)
                self.symtable.set_value(node.name, val)

        elif isinstance(node, ArrayDecl):
            size = self.eval_expr(node.size)
            symbol = self.symtable.declare_array(node.name, node.var_type, size)
            if node.value is not None:
                for i, v in enumerate(node.value):
                    val = self.eval_expr(v)
                    if node.var_type == 'char':
                        self.memory.write_char(symbol.addr + i, val)
                    else:
                        self.memory.write(symbol.addr + i, val)

    # ----- 語句執行 -----
    def exec_stmt(self, node):
        if self.trace:
            print(f"[trace] {node}")

        if isinstance(node, (VarDecl, ArrayDecl)):
            self.exec_decl(node)

        elif isinstance(node, Block):
            for stmt in node.statements:
                self.exec_stmt(stmt)

        elif isinstance(node, IfStmt):
            cond = self.eval_expr(node.condition)
            if cond:
                self.exec_stmt(node.then_branch)
            elif node.else_branch:
                self.exec_stmt(node.else_branch)

        elif isinstance(node, WhileStmt):
            while self.eval_expr(node.condition):
                try:
                    self.exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    continue

        elif isinstance(node, DoWhileStmt):
            while True:
                try:
                    self.exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                if not self.eval_expr(node.condition):
                    break

        elif isinstance(node, ForStmt):
            if node.init:
                self.eval_expr(node.init)
            while True:
                if node.condition and not self.eval_expr(node.condition):
                    break
                try:
                    self.exec_stmt(node.body)
                except BreakException:
                    break
                except ContinueException:
                    pass
                if node.update:
                    self.eval_expr(node.update)

        elif isinstance(node, Return):
            val = self.eval_expr(node.value) if node.value else 0
            raise ReturnException(val)

        elif isinstance(node, BreakStmt):
            raise BreakException()

        elif isinstance(node, ContinueStmt):
            raise ContinueException()

        else:
            # 表達式語句
            self.eval_expr(node)

    # ----- 表達式求值 -----
    def eval_expr(self, node):
        if isinstance(node, Number):
            return node.value

        elif isinstance(node, Char):
            return ord(node.value)

        elif isinstance(node, StringLiteral):
            addr = self.memory.allocate(len(node.value) + 1)
            self.memory.write_string(addr, node.value)
            return addr

        elif isinstance(node, Identifier):
            return self.symtable.get_value(node.name)

        elif isinstance(node, BinOp):
            return self.eval_binop(node)

        elif isinstance(node, UnaryOp):
            return self.eval_unaryop(node)

        elif isinstance(node, Assignment):
            return self.eval_assignment(node)

        elif isinstance(node, Call):
            return self.eval_call(node)

        elif isinstance(node, AddressOf):
            return self.eval_addressof(node)

        elif isinstance(node, Deref):
            addr = self.eval_expr(node.pointer)
            return self.memory.read(addr)

        elif isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self.eval_expr(node.index)
            if index < 0 or index >= symbol.array_size:
                raise RuntimeError(f"Array index out of bounds (index {index}, size {symbol.array_size})")
            return self.memory.read(symbol.addr + index)

        raise RuntimeError(f"Unknown AST node: {type(node)}")

    # ----- BinOp -----
    def eval_binop(self, node):
        # 短路求值
        if node.op == "AND":
            return 1 if (self.eval_expr(node.left) and self.eval_expr(node.right)) else 0
        if node.op == "OR":
            return 1 if (self.eval_expr(node.left) or self.eval_expr(node.right)) else 0

        left = self.eval_expr(node.left)
        right = self.eval_expr(node.right)

        op = node.op
        if op == "PLUS":    return self._int32(left + right)
        if op == "MINUS":   return self._int32(left - right)
        if op == "MUL":     return self._int32(left * right)
        if op == "DIV":
            if right == 0:
                raise RuntimeError("Runtime error: division by zero")
            return self._int32(int(left / right))
        if op == "MOD":
            if right == 0:
                raise RuntimeError("Runtime error: division by zero")
            return self._int32(left % right)
        if op == "EQ":      return 1 if left == right else 0
        if op == "NEQ":     return 1 if left != right else 0
        if op == "LT":      return 1 if left < right else 0
        if op == "GT":      return 1 if left > right else 0
        if op == "LTE":     return 1 if left <= right else 0
        if op == "GTE":     return 1 if left >= right else 0
        if op == "BIT_AND": return self._int32(left & right)
        if op == "BIT_OR":  return self._int32(left | right)
        if op == "BIT_XOR": return self._int32(left ^ right)
        if op == "LSHIFT":  return self._int32(left << right)
        if op == "RSHIFT":  return self._int32(left >> right)

        raise RuntimeError(f"Unknown binary operator: {op}")

    # ----- UnaryOp -----
    def eval_unaryop(self, node):
        op = node.op
        if op == "MINUS":
            return self._int32(-self.eval_expr(node.operand))
        if op == "PLUS":
            return self.eval_expr(node.operand)
        if op == "NOT":
            return 1 if not self.eval_expr(node.operand) else 0
        if op == "BIT_NOT":
            return self._int32(~self.eval_expr(node.operand))
        if op == "INC":
            return self.eval_inc_dec(node.operand, 1)
        if op == "DEC":
            return self.eval_inc_dec(node.operand, -1)

        raise RuntimeError(f"Unknown unary operator: {op}")

    def eval_inc_dec(self, target, delta):
        if isinstance(target, Identifier):
            val = self.symtable.get_value(target.name)
            self.symtable.set_value(target.name, val + delta)
            return val + delta
        if isinstance(target, Deref):
            addr = self.eval_expr(target.pointer)
            val = self.memory.read(addr)
            self.memory.write(addr, val + delta)
            return val + delta
        if isinstance(target, ArrayAccess):
            symbol = self.symtable.lookup(target.array.name)
            index = self.eval_expr(target.index)
            addr = symbol.addr + index
            val = self.memory.read(addr)
            self.memory.write(addr, val + delta)
            return val + delta
        raise RuntimeError("Invalid increment/decrement target")

    # ----- Assignment -----
    def eval_assignment(self, node):
        val = self.eval_expr(node.value)

        # 複合指定運算子先取舊值
        if node.op != "ASSIGN":
            old = self.eval_lvalue_read(node.target)
            if node.op == "ADD_ASSIGN": val = self._int32(old + val)
            elif node.op == "SUB_ASSIGN": val = self._int32(old - val)
            elif node.op == "MUL_ASSIGN": val = self._int32(old * val)
            elif node.op == "DIV_ASSIGN":
                if val == 0: raise RuntimeError("Runtime error: division by zero")
                val = self._int32(int(old / val))
            elif node.op == "MOD_ASSIGN":
                if val == 0: raise RuntimeError("Runtime error: division by zero")
                val = self._int32(old % val)

        self.eval_lvalue_write(node.target, val)
        return val

    def eval_lvalue_read(self, node):
        if isinstance(node, Identifier):
            return self.symtable.get_value(node.name)
        if isinstance(node, Deref):
            addr = self.eval_expr(node.pointer)
            return self.memory.read(addr)
        if isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self.eval_expr(node.index)
            return self.memory.read(symbol.addr + index)
        raise RuntimeError("Invalid assignment target")

    def eval_lvalue_write(self, node, val):
        if isinstance(node, Identifier):
            self.symtable.set_value(node.name, val)
        elif isinstance(node, Deref):
            addr = self.eval_expr(node.pointer)
            self.memory.write(addr, val)
        elif isinstance(node, ArrayAccess):
            symbol = self.symtable.lookup(node.array.name)
            index = self.eval_expr(node.index)
            if index < 0 or index >= symbol.array_size:
                raise RuntimeError(f"Array index out of bounds (index {index}, size {symbol.array_size})")
            if symbol.var_type == 'char':
                self.memory.write_char(symbol.addr + index, val)
            else:
                self.memory.write(symbol.addr + index, val)
        else:
            raise RuntimeError("Invalid assignment target")

    # ----- Call -----
    def eval_call(self, node):
        name = node.name.name
        args = [self.eval_expr(a) for a in node.args]

        if self.builtins.is_builtin(name):
            return self.builtins.call(name, args)

        return self.call_function(name, args)

    def call_function(self, name, args):
        if name not in self.functions:
            raise RuntimeError(f"Undefined function '{name}'")
        func = self.functions[name]

        save_top = self.memory.heap_top
        self.symtable.push_scope()

        # 綁定參數
        for param, arg in zip(func.params, args):
            symbol = self.symtable.declare(param.name, param.var_type, param.is_pointer)
            self.symtable.set_value(param.name, arg)

        ret_val = 0
        try:
            self.exec_stmt(func.body)
        except ReturnException as e:
            ret_val = e.value

        self.symtable.pop_scope()
        self.memory.free_to(save_top)
        return ret_val

    # ----- AddressOf -----
    def eval_addressof(self, node):
        target = node.target
        if isinstance(target, Identifier):
            return self.symtable.lookup(target.name).addr
        if isinstance(target, ArrayAccess):
            symbol = self.symtable.lookup(target.array.name)
            index = self.eval_expr(target.index)
            return symbol.addr + index
        raise RuntimeError("Invalid & target")

    # ----- 工具 -----
    def _int32(self, value):
        """截斷為 32 位元有號整數"""
        value = int(value)
        return ((value + 2**31) % 2**32) - 2**31