# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Small-C is a tree-walking interpreter for a subset of C, implemented in pure Python with no external dependencies. It is the Spring 2026 System Software final project and ships as an interactive REPL. There is no build step, no test suite, and no lint config — the code runs directly on a stock Python 3 install.

## Running

```bash
python main.py
```

This launches the REPL (prompt `sc> `). There are no CLI flags or script-mode entry points — all interaction happens inside the REPL. To execute a `.c` file, start the REPL and use `LOAD <file>` followed by `RUN`. Use `CHECK` to parse without executing. `TRACE ON` enables per-node execution tracing for debugging the interpreter itself.

Because there are no tests, verification of changes is done by hand via the REPL: `LOAD` a sample program, `RUN` it, and inspect output / `VARS` / `FUNCS`.

## Architecture

The pipeline is a classic four-stage tree-walking interpreter. Data flows strictly in one direction:

```
source ─► preprocess() ─► Lexer ─► Parser ─► Interpreter ─► output
                         (Token)   (AST)    (walks AST)
```

- **`lexer.py`** — `preprocess()` handles parameter-less `#define` macro expansion (identifier-boundary aware, so `#define N 8` won't clobber `int`). `Lexer.tokenize()` is a hand-written character scanner that yields `Token(kind, value, line)`. Double-char operators are matched before single-char to avoid ambiguity (`==` before `=`).

- **`parser.py`** — Recursive-descent parser producing the AST. The **top half of the file defines all AST node classes** (`Expr`/`Stmt`/`FuncDef`/`Program` hierarchies); the **bottom half is the `Parser` class**. Expression precedence, low to high: `assignment > logic_or > logic_and > bit_or > bit_xor > bit_and > equality > rel > shift > add > mul > unary > primary`. `is_func_def()` does 3–4 token lookahead to disambiguate function definitions from variable declarations at the top level (it must handle both `int foo(` and `int *foo(`).

- **`interpreter.py`** — `Interpreter` walks the AST. Two entry points: `execute()` runs a full program (requires `main()`; does a two-pass scan — collect functions and globals first, then call `main`); `execute_interactive()` runs REPL fragments directly without requiring `main()`. **Control flow (`break`/`continue`/`return`) is implemented via Python exceptions** (`BreakException`, `ContinueException`, `ReturnException`) caught by the nearest enclosing loop or call site. All values are integers — `char` is just an 8-bit int, pointers are memory addresses (also ints).

- **`memory.py`** — `Memory` is a flat `list[int]` of 65536 cells with a bump allocator (`heap_top`). `allocate()` grows it, `free_to()` rewinds it (used on function return to release locals). `write()` truncates to 32-bit signed, `write_char()` to 8-bit signed. Strings are C-style null-terminated sequences written via `write_string()`.

- **`symtable.py`** — `SymbolTable` is a stack of scope dicts. `scopes[0]` is the global scope (permanent); each function call pushes a new scope and pops on return. `lookup()` walks from innermost outward, giving C-like shadowing. It only maps names → `Symbol` (which holds type, address, `is_pointer`, `is_array`, `array_size`); the actual cell read/write is delegated to `Memory`.

- **`builtins_funcs.py`** — `Builtins.call(name, args)` dispatches built-in functions by name. Built-ins receive already-evaluated integer arguments; string arguments arrive as memory addresses and must be read via `memory.read_string(addr)`. Covers I/O (`printf`, `scanf`, `putchar`, `getchar`, `puts`), string ops (`strlen`, `strcpy`, `strcmp`, `strcat`), math (`abs`, `max`, `min`, `pow`, `sqrt`, `mod`, `rand`, `srand`), and utilities (`memset`, `sizeof_int`, `sizeof_char`, `atoi`, `itoa`, `exit`). `Interpreter.eval_call()` checks `builtins.is_builtin(name)` before falling back to user-defined functions.

- **`repl.py`** — `REPL` holds a line buffer (`self.buffer`) and dispatches `LOAD / SAVE / LIST / EDIT / DELETE / INSERT / APPEND / NEW / RUN / CHECK / TRACE / VARS / FUNCS / HELP / ABOUT / CLEAR / QUIT`. `ReplInputCollector` tracks brace depth and comment/string state across lines so multi-line function definitions can be typed at the prompt before being handed to the parser as one unit. `main.py` is a 10-line shim that just instantiates `REPL` and calls `run()`.

### Small-C language subset

Supported: `int` / `char` / `void` (with pointer `*`); variable and array declarations with initializers; function definitions and calls; arithmetic / bitwise / logical / comparison / assignment (including compound `+= -= *= /= %=`); prefix `++` / `--`; `if`/`else`, `while`, `do-while`, `for`, `switch`/`case`/`default` (with fall-through), `break`, `continue`, `return`; `#define` for parameter-less macros only. **Not** supported: function-like macros, `struct`/`union`/`typedef`, `float`/`double`, postfix `++`/`--`, multi-dimensional arrays, `#include`.

## Conventions specific to this codebase

- **All docstrings and inline comments are in Traditional Chinese** (繁體中文). Module headers use a consistent ASCII box-drawing format with a flow diagram at the top. When editing existing modules, match this style — don't translate existing Chinese comments to English, and write new comments in Chinese if the surrounding code is in Chinese.
- Section dividers inside classes use `# ── Section Name ────` (en-dash + box-drawing). Top-level module sections use `# ═══` (double line).
- The interpreter uses exceptions for control flow by design — do not "fix" `BreakException`/`ContinueException`/`ReturnException` by trying to refactor them into return values.
- Integer truncation is centralized in `Memory.write()` / `write_char()` and `Interpreter._int32()`. Always go through these rather than applying masks inline.

## Assignment spec (authoritative — treat as source of truth)

Two spec documents live in the repo root and override any assumption you would otherwise derive from the code:

- `期末專題SmallC 互動式解譯器作業說明.pdf` — the assignment handout (scanned images, 22 pages). This defines the required language subset, built-ins, REPL commands, error message formats, submission file names, and grading rubric.
- `期末專題-Small-C 互動式解譯器評分標準-學生版.md` — the grading checklist. Five test scripts A–E; only **Test A** is visible to students, B–E are withheld and run by the grader. The MD lists every REPL command and language feature that will be checked.

When in doubt about required behavior, read the spec files rather than matching the current code — the code has known gaps (see below).

### Spec highlights that are easy to get wrong

- **No block-local variable declarations.** Per the PDF, Small-C只在函式開頭宣告區域變數. Do not encourage users to declare vars mid-block even though the current parser accepts it.
- **`switch`/`case` and postfix `++`/`--` are optional bonus features**, not core requirements. `switch` is already implemented; postfix `++`/`--` is intentionally absent.
- **REPL commands are case-insensitive** and the spec enumerates the exact set: `ABOUT HELP APPEND LIST EDIT DELETE INSERT CHECK RUN SAVE NEW LOAD TRACE VARS FUNCS CLEAR QUIT/EXIT`.
- **`ABOUT` must display 名稱、版本號、作者資訊、修課學期** — author info is required.
- **`TRACE` output format is `[line n] <statement>`**, not a free-form node dump.
- **`FUNCS` must print line numbers for user-defined functions**, e.g. `void swap(int *a, int *b)    line 2`. Built-ins are listed separately with no line number.
- **Error messages have specific required formats**, e.g.
  - `Runtime error: division by zero.`
  - `Runtime error: array index out of bounds (index 10, size 5).`
  - `Runtime error: sqrt() argument must be non-negative.`
  - `Syntax error: unexpected token ';', expected expression.`
  - `Error at line 3: expected ';' after expression statement.`
- **Required built-ins** (must all exist with these names): `printf scanf putchar getchar puts strlen strcpy strcmp strcat abs max min pow sqrt mod rand srand memset sizeof_int sizeof_char atoi itoa exit`. `printf` must accept `%d %c %s %x %%`; `scanf` must accept `%d %c`.
- **Submission file names**: `main.py lexer.py parser.py interpreter.py symtable.py memory.py builtins.py repl.py` + `requirements.txt` + `README.md` + 10+ test programs + PDF report (10+ pages) + 5–10 min screen recording. Note the spec expects `builtins.py`, not the current `builtins_funcs.py`.
- **Grading rubric (100 + 15 bonus)**: Lex/Parse 25 · Semantic/Exec 30 · REPL 20 · Quality/Docs 15 · Bonus (switch/case 5, runtime errors 5, #define 5).

### Known spec/implementation gaps

These were identified by spot-checking against the spec; fix them before submission, but don't silently "refactor" them without flagging the change:

1. **TRACE format** — `interpreter.py:214` prints `f"[trace] {node}"`. Spec requires `[line n] <statement>`. AST nodes currently don't carry line numbers, so a proper fix means threading `line` through the parser into each `Stmt` node.
2. **ABOUT missing author** — `repl.py:699-702` prints only name/version/semester. Must also include 作者資訊.
3. **FUNCS missing line numbers** — `repl.py:607` formats user functions without a line number. `FuncDef` in `parser.py` doesn't store one; this also needs parser plumbing.
4. **File name mismatch** — current `builtins_funcs.py` must be renamed to `builtins.py` for submission (and the import in `interpreter.py` updated).
5. **Block-local var decls accepted** — `parser.py` `block()` calls `var_decl()` anywhere inside a block. The spec only allows declarations at function start. Either tighten the parser or document this as an intentional leniency.
6. **Error messages** — current error strings may not match the spec's exact wording and punctuation. Audit `interpreter.py` runtime errors and `parser.py` syntax errors against the examples above.
