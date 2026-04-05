from lexer import Lexer

# ===== AST =====
class AST:
    pass

# --- Expression ---
class Expr(AST):
    pass

class Number(Expr):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Number({self.value})"

class Char(Expr):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Char('{self.value}')"

class StringLiteral(Expr):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"StringLiteral({self.value!r})"

class Identifier(Expr):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Identifier({self.name})"


class UnaryOp(Expr):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
    def __repr__(self):
        return f"UnaryOp({self.op}, {self.operand})"

class BinOp(Expr):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self):
        return f"BinOp({self.left}, {self.op}, {self.right})"

class AddressOf(Expr):
    def __init__(self, target):
        self.target = target
    def __repr__(self):
        return f"AddressOf({self.target})"

class Deref(Expr):
    def __init__(self, pointer):
        self.pointer = pointer
    def __repr__(self):
        return f"Deref({self.pointer})"

class Call(Expr):
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return f"Call({self.name}, {self.args})"

class ArrayAccess(Expr):
    def __init__(self, array, index):
        self.array = array
        self.index = index
    def __repr__(self):
        return f"ArrayAccess({self.array}, {self.index})"

class Assignment(Expr):
    def __init__(self, target, op, value):  # [1] 加上 op
        self.target = target
        self.op = op
        self.value = value
    def __repr__(self):
        return f"Assignment({self.target}, {self.op}, {self.value})"

# --- Statement ---
class Stmt(AST):
    pass



class VarDecl(Stmt):
    def __init__(self, var_type, name, value=None, is_pointer=False):
        self.var_type = var_type
        self.name = name
        self.value = value
        self.is_pointer = is_pointer
    def __repr__(self):
        return f"VarDecl({self.var_type}, {self.name}, {self.value}, pointer={self.is_pointer})"

class ArrayDecl(Stmt):
    def __init__(self, var_type, name, size, value=None):  # 補回 value
        self.var_type = var_type
        self.name = name
        self.size = size
        self.value = value
    def __repr__(self):
        return f"ArrayDecl({self.var_type}, {self.name}, size={self.size}, value={self.value})"



class Block(Stmt):
    def __init__(self, statements):
        self.statements = statements
    def __repr__(self):
        return f"Block({self.statements})"

class Return(Stmt):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Return({self.value})"

class IfStmt(Stmt):
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
    def __repr__(self):
        return f"IfStmt({self.condition}, {self.then_branch}, {self.else_branch})"

class WhileStmt(Stmt):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body
    def __repr__(self):
        return f"WhileStmt({self.condition}, {self.body})"

class DoWhileStmt(Stmt):
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition
    def __repr__(self):
        return f"DoWhileStmt({self.body}, {self.condition})"

class ForStmt(Stmt):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body
    def __repr__(self):
        return f"ForStmt({self.init}, {self.condition}, {self.update}, {self.body})"

class BreakStmt(Stmt):
    def __repr__(self):
        return "BreakStmt()"

class ContinueStmt(Stmt):
    def __repr__(self):
        return "ContinueStmt()"

class FuncDef(Stmt):
    def __init__(self, ret_type, name, params, body, is_pointer=False):
        self.ret_type = ret_type
        self.name = name
        self.params = params
        self.body = body
        self.is_pointer = is_pointer
    def __repr__(self):
        return f"FuncDef({self.ret_type}, {'*' if self.is_pointer else ''}{self.name}, {self.params}, {self.body})"

# --- Program ---
class Program(AST):
    def __init__(self, decls):
        self.decls = decls
    def __repr__(self):
        return f"Program({self.decls})"


# ===== Parser =====
class Parser:
    def __init__(self, text):
        self.lexer = Lexer(text)
        self.tokens = list(self.lexer.tokenize())  # [3] generate_tokens -> tokenize
        self.pos = 0
        self.current_token = self.tokens[self.pos]

    # ----- 工具 -----
    def eat(self, kind):
        if self.current_token.kind == "ERROR":  # [15] ERROR token 統一在這裡 raise
            raise Exception(f"Line {self.current_token.line}: {self.current_token.value}")
        if self.current_token.kind == kind:  # [4] .type -> .kind
            self.pos += 1
            if self.pos < len(self.tokens):
                self.current_token = self.tokens[self.pos]
        else:
            raise Exception(f"Line {self.current_token.line}: Expected {kind}, got {self.current_token.kind}")

    def peek(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def peek2(self):
        if self.pos + 2 < len(self.tokens):
            return self.tokens[self.pos + 2]
        return None

    def is_type_token(self):  # [6] 集中判斷 type token
        return self.current_token.kind in ("INT", "CHAR", "VOID")

    # ----- 入口 -----
    def parse(self):
        decls = []
        while self.current_token.kind != "EOF":  # [4]
            decls.append(self.declaration())
        return Program(decls)

    # ----- declaration -----

    def is_func_def(self):
        p1 = self.peek()
        p2 = self.peek2()
        if p1 and p1.kind == "MUL":
            # int *func() 的情況
            p3 = self.tokens[self.pos + 3] if self.pos + 3 < len(self.tokens) else None
            return p2 and p2.kind == "IDENT" and p3 and p3.kind == "LPAREN"
        # int func() 的情況
        return p1 and p1.kind == "IDENT" and p2 and p2.kind == "LPAREN"

    def declaration(self):
        if self.is_type_token():
            if self.is_func_def():
                return self.func_def()
            else:
                return self.var_decl()
        return self.statement()

    # ----- statement -----
    def statement(self):  # [9] 移除 try/except
        tok = self.current_token
        if tok.kind == "IF":  # [4]
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
            return BreakStmt()
        if tok.kind == "CONTINUE":
            self.eat("CONTINUE")
            self.eat("SEMI")
            return ContinueStmt()
        if tok.kind == "LBRACE":
            return self.block()
        expr = self.expr()
        self.eat("SEMI")
        return expr

    # ----- block -----
    def block(self):
        self.eat("LBRACE")
        stmts = []
        while self.current_token.kind != "RBRACE" and self.current_token.kind != "EOF":  # [4]
            if self.is_type_token():  # [6]
                stmts.append(self.var_decl())
            else:
                stmts.append(self.statement())
        self.eat("RBRACE")
        return Block(stmts)

    # ----- block_or_stmt -----
    def block_or_stmt(self):
        if self.current_token.kind == "LBRACE":  # [4]
            return self.block()
        stmt = self.statement()
        return Block([stmt])

    # ----- var_decl -----
    def var_decl(self):
        var_type = self.current_token.value
        self.eat(self.current_token.kind)  # [7] 動態 eat 當前 type token
        is_pointer = False
        if self.current_token.kind == "MUL":  # [4]
            is_pointer = True
            self.eat("MUL")
        name = self.current_token.value
        self.eat("IDENT")  # [8]

        if self.current_token.kind == "LBRACKET":  # [4]
            return self.array_decl(var_type, name)

        value = None
        if self.current_token.kind == "ASSIGN":  # [4]
            self.eat("ASSIGN")
            value = self.expr()

        self.eat("SEMI")
        return VarDecl(var_type, name, value, is_pointer)

    def array_decl(self, var_type, name):
        self.eat("LBRACKET")
        size = self.expr()
        self.eat("RBRACKET")

        value = None
        if self.current_token.kind == "ASSIGN":  # [4]
            self.eat("ASSIGN")
            self.eat("LBRACE")
            value = []
            if self.current_token.kind != "RBRACE":  # [4]
                value.append(self.expr())
                while self.current_token.kind == "COMMA":  # [4]
                    self.eat("COMMA")
                    value.append(self.expr())
            self.eat("RBRACE")

        self.eat("SEMI")
        return ArrayDecl(var_type, name, size, value)

    # ----- func_def -----
    def func_def(self):
        ret_type = self.current_token.value
        self.eat(self.current_token.kind)
        
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
        return FuncDef(ret_type, name, params, body, is_pointer)

    def param(self):
        var_type = self.current_token.value
        self.eat(self.current_token.kind)  # [7]
        is_pointer = False
        if self.current_token.kind == "MUL":  # [4]
            is_pointer = True
            self.eat("MUL")
        name = self.current_token.value
        self.eat("IDENT")  # [8]
        return VarDecl(var_type, name, None, is_pointer)

    # ----- if / while / do / for -----
    def if_stmt(self):
        self.eat("IF")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        then_branch = self.block_or_stmt()
        else_branch = None
        if self.current_token.kind == "ELSE":  # [4]
            self.eat("ELSE")
            else_branch = self.block_or_stmt()
        return IfStmt(cond, then_branch, else_branch)

    def while_stmt(self):
        self.eat("WHILE")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        body = self.block_or_stmt()
        return WhileStmt(cond, body)

    def do_while_stmt(self):
        self.eat("DO")
        body = self.block_or_stmt()
        self.eat("WHILE")
        self.eat("LPAREN")
        cond = self.expr()
        self.eat("RPAREN")
        self.eat("SEMI")
        return DoWhileStmt(body, cond)

    def for_stmt(self):
        self.eat("FOR")
        self.eat("LPAREN")

        init = None
        if self.current_token.kind != "SEMI":
            init = self.expr()
        self.eat("SEMI")

        condition = None
        if self.current_token.kind != "SEMI":  # [4]
            condition = self.expr()
        self.eat("SEMI")

        update = None
        if self.current_token.kind != "RPAREN":  # [4]
            update = self.expr()
        self.eat("RPAREN")

        body = self.block_or_stmt()
        return ForStmt(init, condition, update, body)

    # ----- return -----
    def return_stmt(self):
        self.eat("RETURN")
        val = None
        if self.current_token.kind != "SEMI":
            val = self.expr()
        self.eat("SEMI")
        return Return(val)

    # ----- expressions -----
    def expr(self):
        return self.assignment()

    # assignment : logic_or (ASSIGN | ADD_ASSIGN | ...) assignment
    def assignment(self):
        node = self.logic_or()
        if self.current_token.kind in ("ASSIGN", "ADD_ASSIGN", "SUB_ASSIGN", "MUL_ASSIGN", "DIV_ASSIGN", "MOD_ASSIGN"):  # [4]
            op = self.current_token.kind
            self.eat(op)
            value = self.assignment()
            return Assignment(node, op, value)  # [1] 傳入 op
        return node

    # logic_or : logic_and ('||' logic_and)*
    def logic_or(self):
        node = self.logic_and()
        while self.current_token.kind == "OR":  # [10] OR_OR -> OR
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.logic_and())
        return node

    # logic_and : bit_or ('&&' bit_or)*
    def logic_and(self):
        node = self.bit_or()
        while self.current_token.kind == "AND":  # [11] AND_AND -> AND
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_or())
        return node

    # bit_or : bit_xor ('|' bit_xor)*
    def bit_or(self):
        node = self.bit_xor()
        while self.current_token.kind == "BIT_OR":  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_xor())
        return node

    # bit_xor : bit_and ('^' bit_and)*
    def bit_xor(self):
        node = self.bit_and()
        while self.current_token.kind == "BIT_XOR":  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.bit_and())
        return node

    # bit_and : equality ('&' equality)*
    def bit_and(self):
        node = self.equality()
        while self.current_token.kind == "BIT_AND":  # [13] AMP -> BIT_AND
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.equality())
        return node

    # equality : rel (('==' | '!=') rel)*
    def equality(self):
        node = self.rel()
        while self.current_token.kind in ("EQ", "NEQ"):  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.rel())
        return node

    # rel : shift ('<' | '>' | '<=' | '>=') shift
    def rel(self):
        node = self.shift()
        while self.current_token.kind in ("LT", "GT", "LTE", "GTE"):  # [12] LE/GE -> LTE/GTE
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.shift())
        return node

    # shift : add (('<<' | '>>') add)*
    def shift(self):
        node = self.add()
        while self.current_token.kind in ("LSHIFT", "RSHIFT"):  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.add())
        return node

    # add : mul ('+' | '-')*
    def add(self):
        node = self.mul()
        while self.current_token.kind in ("PLUS", "MINUS"):  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.mul())
        return node

    # mul : unary ('*' | '/' | '%')*
    def mul(self):
        node = self.unary()
        while self.current_token.kind in ("MUL", "DIV", "MOD"):  # [4]
            op = self.current_token.kind
            self.eat(op)
            node = BinOp(node, op, self.unary())
        return node

    # unary : ('+' | '-' | '!' | '~' | '*' | '&' | '++' | '--') unary | primary
    def unary(self):
        tok = self.current_token
        if tok.kind in ("PLUS", "MINUS", "NOT", "BIT_NOT"):  # [4]
            self.eat(tok.kind)
            return UnaryOp(tok.kind, self.unary())
        if tok.kind == "MUL":
            self.eat("MUL")
            return Deref(self.unary())
        if tok.kind == "BIT_AND":  # [13] AMP -> BIT_AND
            self.eat("BIT_AND")
            return AddressOf(self.unary())
        if tok.kind in ("INC", "DEC"):  # 前置 ++x / --x
            self.eat(tok.kind)
            return UnaryOp(tok.kind, self.unary())
        return self.primary()

    # primary : NUMBER | CHAR | IDENT | IDENT '(' args ')' | IDENT '[' expr ']' | '(' expr ')'
    def primary(self):
        tok = self.current_token
        if tok.kind == "NUMBER":
            self.eat("NUMBER")
            return Number(tok.value)
        if tok.kind == "CHAR":  # 字元字面量
            self.eat("CHAR")
            return Char(tok.value)
        if tok.kind == "STRING":
            self.eat("STRING")
            return StringLiteral(tok.value)
        if tok.kind == "IDENT":  # [8]
            name = tok.value
            self.eat("IDENT")
            node = Identifier(name)
            if self.current_token.kind == "LPAREN":  # 函式呼叫
                self.eat("LPAREN")
                args = []
                if self.current_token.kind != "RPAREN":  # [4]
                    args.append(self.expr())
                    while self.current_token.kind == "COMMA":  # [4]
                        self.eat("COMMA")
                        args.append(self.expr())
                self.eat("RPAREN")
                node = Call(node, args)  # [14] Call(node, args) 不重複建立 Identifier
            if self.current_token.kind == "LBRACKET":  # 陣列存取
                self.eat("LBRACKET")
                index = self.expr()
                self.eat("RBRACKET")
                node = ArrayAccess(node, index)
            return node
        if tok.kind == "LPAREN":
            self.eat("LPAREN")
            node = self.expr()
            self.eat("RPAREN")
            return node
        raise Exception(f"Line {tok.line}: Unexpected token {tok.kind}")  # [9] 直接 raise