class Token:
    def __init__(self, kind, value, line):  # [1] type -> kind
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.kind}, {self.value}, {self.line})"

def preprocess(source):
    defines = {}
    lines = []
    for line in source.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#define'):
            parts = stripped.split()
            if len(parts) == 3:
                defines[parts[1]] = parts[2]
        else:
            lines.append(line)
    result = '\n'.join(lines)
    for name, value in defines.items():
        result = result.replace(name, value)
    return result


class Lexer:
    KEYWORDS = {
        'int': "INT",
        'char': "CHAR",
        'void': "VOID",
        'if': 'IF',
        'else': 'ELSE',
        'while': "WHILE",
        'for': 'FOR',
        'do': 'DO',
        'break': "BREAK",
        'continue': 'CONTINUE',
        'return': 'RETURN',
    }
    SINGLE_OPS = {
        '!': 'NOT',
        '&': 'BIT_AND',
        '~': 'BIT_NOT',
        '^': 'BIT_XOR',
        '|': 'BIT_OR',
        '+': 'PLUS',
        '-': 'MINUS',
        '*': 'MUL',
        '/': 'DIV',
        '%': 'MOD',
        '=': 'ASSIGN',
        '>': 'GT',
        '<': 'LT',
    }
    DOUBLE_OPS = {
        '++': 'INC',
        '--': 'DEC',
        '<<': 'LSHIFT',
        '>>': 'RSHIFT',
        '&&': 'AND',
        '||': 'OR',
        '==': 'EQ',
        '!=': 'NEQ',
        '>=': 'GTE',
        '<=': 'LTE',
        '+=': 'ADD_ASSIGN',
        '-=': 'SUB_ASSIGN',
        '*=': 'MUL_ASSIGN',
        '/=': 'DIV_ASSIGN',
        '%=': 'MOD_ASSIGN',
    }
    SYMBOLS = {
        ';': 'SEMI', ',': 'COMMA',
        '(': 'LPAREN', ')': 'RPAREN',
        '{': 'LBRACE', '}': 'RBRACE',
        '[': 'LBRACKET', ']': 'RBRACKET',
    }

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.current_char = self.text[self.pos] if text else None

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
        self.pos += 1
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None

    def peek(self):
        peek_pos = self.pos + 1
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]

    def skip_whitespace_and_comments(self):
        while self.current_char is not None:
            if self.current_char in ' \t\n':
                self.advance()
                continue
            elif self.current_char == '/' and self.peek() == '/':
                while self.current_char is not None and self.current_char != '\n':
                    self.advance()
            elif self.current_char == '/' and self.peek() == '*':
                self.advance()
                self.advance()
                while self.current_char is not None:
                    if self.current_char == '*' and self.peek() == '/':
                        self.advance()
                        self.advance()
                        break
                    self.advance()
                else:

                    return Token("ERROR", "Unterminated comment", self.line)
            else:
                break
        return None

    def character(self):
        start_line = self.line
        self.advance()  # 跳過開頭的 '

        if self.current_char is None:
            return Token("ERROR", "Unterminated char", start_line)

        if self.current_char == '\\':
            self.advance()
            if self.current_char is None:
                return Token("ERROR", "Unterminated char escape", start_line)
            escapes = {"n": "\n", "t": "\t", "0": "\0", "'": "'", '"': '"', "\\": "\\"}
            if self.current_char in escapes:
                value = escapes[self.current_char]
            else:
                return Token("ERROR", f"Invalid escape '\\{self.current_char}'", start_line)
        else:
            value = self.current_char

        self.advance()

        if self.current_char != "'":
            return Token("ERROR", "Unterminated char literal", start_line)

        self.advance()
        return Token("CHAR", value, start_line)

    def string_literal(self):
        value = ""
        start_line = self.line
        self.advance()  # 跳過開頭的 "

        while self.current_char is not None:
            if self.current_char == '"':
                self.advance()
                return Token("STRING", value, start_line)

            if self.current_char == '\n':
                return Token("ERROR", "Newline in char/string", start_line)

            if self.current_char == '\\':
                self.advance()
                if self.current_char is None:
                    return Token("ERROR", "Unterminated string escape", start_line)
                escapes = {"n": "\n", "t": "\t", "0": "\0", "'": "'", '"': '"', "\\": "\\"}
                if self.current_char in escapes:
                    value += escapes[self.current_char]
                else:
                    return Token("ERROR", f"Invalid escape '\\{self.current_char}'", start_line)
            else:
                value += self.current_char
            self.advance()

        return Token("ERROR", "Unterminated string literal", start_line)

    def number(self):
        num_str = ''
        start_line = self.line

        if self.current_char == '0' and (self.peek() in ['x', 'X']):
            num_str += self.current_char
            self.advance()
            num_str += self.current_char
            self.advance()
            if self.current_char is None or not (self.current_char.isdigit() or 'a' <= self.current_char.lower() <= 'f'):
                return Token("ERROR", "Invalid hex literal", start_line)
            while self.current_char is not None and (self.current_char.isdigit() or 'a' <= self.current_char.lower() <= 'f'):
                num_str += self.current_char
                self.advance()
            value = int(num_str, 16)
            return Token('NUMBER', value, start_line)

        while self.current_char is not None and self.current_char.isdigit():
            num_str += self.current_char
            self.advance()
        if not num_str:
            return Token("ERROR", "Expected number", start_line)
        return Token('NUMBER', int(num_str), start_line)

    def identifier(self):
        start_line = self.line
        id_str = ''
        while (self.current_char is not None and
               (self.current_char.isalnum() or self.current_char == '_')):
            id_str += self.current_char
            self.advance()
        if id_str in self.KEYWORDS:
            return Token(self.KEYWORDS[id_str], id_str, start_line)
        else:
            return Token('IDENT', id_str, start_line)

    def get_next_token(self):
        while self.current_char is not None:
            # [4][9] skip 現在直接回傳 error token，不再透過 self.error 傳遞
            error_token = self.skip_whitespace_and_comments()
            if error_token is not None:
                return error_token

            if self.current_char is None:
                return Token('EOF', None, self.line)

            if self.current_char == '\'':
                return self.character()

            if self.current_char == '\"':
                return self.string_literal()

            # [8] 改成明確的 None 檢查
            next_char = self.peek()
            two_char = self.current_char + (next_char if next_char is not None else '')
            if two_char in self.DOUBLE_OPS:
                token = Token(self.DOUBLE_OPS[two_char], two_char, self.line)
                self.advance()
                self.advance()
                return token

            if self.current_char in self.SINGLE_OPS:
                token = Token(self.SINGLE_OPS[self.current_char], self.current_char, self.line)
                self.advance()
                return token

            if self.current_char in self.SYMBOLS:
                token = Token(self.SYMBOLS[self.current_char], self.current_char, self.line)
                self.advance()
                return token

            if '0' <= self.current_char <= '9':
                return self.number()

            if self.current_char.isalpha() or self.current_char == '_':
                return self.identifier()

            err_line = self.line
            err_char = self.current_char
            self.advance()
            return Token("ERROR", f"Unknown character '{err_char}'", err_line)

        return Token('EOF', None, self.line)

    def tokenize(self):
        while True:
            token = self.get_next_token()
            yield token
            if token.kind == 'EOF':  # [1] .type -> .kind
                break