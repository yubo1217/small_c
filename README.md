# Small-C 互動式解譯器

**課程：** 系統程式｜**學期：** Spring 2026｜**作者：** 林煜博

---

## 目錄

1. [專案概述](#1-專案概述)
2. [系統需求](#2-系統需求)
3. [啟動方式](#3-啟動方式)
4. [REPL 互動環境](#4-repl-互動環境)
5. [Small-C 語言規格](#5-small-c-語言規格)
6. [內建函式規格](#6-內建函式規格)
7. [錯誤處理規格](#7-錯誤處理規格)
8. [系統架構](#8-系統架構)
9. [模組說明](#9-模組說明)
10. [程式範例](#10-程式範例)

---

## 1. 專案概述

Small-C 互動式解譯器是一個以純 Python 3 實作的樹狀走訪（tree-walking）解譯器，支援 C 語言的核心子集。使用者可透過互動式 REPL（Read-Eval-Print Loop）直接輸入並執行 Small-C 程式碼，亦可載入完整程式檔案後批次執行。

**設計目標：**

- 實作標準 C 語言語意的核心子集，包含指標、陣列、遞迴函式
- 提供完整的互動式行編輯環境（緩衝區管理、逐行修改、存取檔案）
- 不依賴任何第三方套件，僅使用 Python 3 標準函式庫
- 提供 TRACE 追蹤模式以協助除錯

---

## 2. 系統需求

| 項目 | 需求 |
|------|------|
| Python 版本 | Python 3.8 以上 |
| 外部相依套件 | 無 |
| 作業系統 | Windows / macOS / Linux |
| 記憶體空間 | 預設 65,536 個整數單元（可在 `memory.py` 調整） |

---

## 3. 啟動方式

```bash
python main.py
```

啟動後顯示歡迎畫面並進入 REPL：

```
==========================================
  Small-C Interactive Interpreter v1.0
  System Software Final Project, Spring 2026
==========================================
Type `HELP` for a list of commands.

sc>
```

提示符說明：
- `sc>` — 等待輸入新的程式碼或指令
- `  >` — 多行輸入模式（尚有未閉合的大括號）

---

## 4. REPL 互動環境

REPL 維護一個**程式碼緩衝區**（buffer），所有行編輯操作均作用於此緩衝區。指令名稱**不區分大小寫**。

### 4.1 程式管理指令

| 指令 | 語法 | 說明 |
|------|------|------|
| `APPEND` | `APPEND` | 在緩衝區末尾逐行追加程式碼，輸入單獨一行 `.` 結束 |
| `LIST` | `LIST` / `LIST n` / `LIST n1-n2` | 列出全部、第 n 行、或第 n1 至 n2 行的緩衝區內容（附行號） |
| `EDIT` | `EDIT n` | 顯示第 n 行並等待輸入新內容取代；直接按 Enter 保留原內容 |
| `DELETE` | `DELETE n` / `DELETE n1-n2` | 刪除第 n 行或第 n1 至 n2 行，後續行號自動遞減 |
| `INSERT` | `INSERT n` | 在第 n 行之前插入一或多行，輸入單獨一行 `.` 結束 |
| `NEW` | `NEW` | 清空緩衝區並重置直譯器狀態；若有未儲存修改會先提示確認 |
| `LOAD` | `LOAD <filename>` | 從檔案載入原始碼到緩衝區；若有未儲存修改會先提示確認 |
| `SAVE` | `SAVE <filename>` | 將緩衝區內容儲存到指定檔案 |

### 4.2 執行指令

| 指令 | 語法 | 說明 |
|------|------|------|
| `RUN` | `RUN` | 對緩衝區程式進行前處理、解析並執行；需包含 `main()` 函式 |
| `CHECK` | `CHECK` | 對緩衝區程式進行語法檢查，不實際執行；顯示錯誤數量 |
| `TRACE` | `TRACE ON` / `TRACE OFF` | 啟用或關閉追蹤模式；啟用後每個執行步驟前輸出 `[line n] <statement>` |

**互動模式**：不使用以上指令時，直接在 `sc>` 提示符輸入 Small-C 程式片段（包含函式定義、敘述、運算式），即時解析並執行，無需 `main()` 函式。

### 4.3 狀態查詢指令

| 指令 | 語法 | 說明 |
|------|------|------|
| `VARS` | `VARS` | 列出所有全域變數的名稱、型別與目前數值 |
| `FUNCS` | `FUNCS` | 列出所有使用者定義函式（含回傳型別、參數、定義行號）與內建函式 |

`VARS` 輸出格式：

```
  int x = 42
  char c = 65 (A)
  int *p = 1024
  int arr[8] = {1, 2, 3, ...}
```

`FUNCS` 輸出格式：

```
  void swap(int *a, int *b)    line 5
  int main()    line 11
  --- built-in functions ---
  int abs(int x)  [built-in]
  ...
```

### 4.4 系統指令

| 指令 | 語法 | 說明 |
|------|------|------|
| `HELP` | `HELP` / `HELP <cmd>` | 顯示所有指令摘要，或指定指令的詳細說明 |
| `ABOUT` | `ABOUT` | 顯示解譯器名稱、版本號、作者資訊與修課學期 |
| `CLEAR` | `CLEAR` | 清除終端機畫面 |
| `QUIT` / `EXIT` | `QUIT` 或 `EXIT` | 退出解譯器；若有未儲存修改會先提示確認 |

---

## 5. Small-C 語言規格

### 5.1 資料型別

| 型別 | 位元寬度 | 數值範圍 |
|------|---------|---------|
| `int` | 32 位元有號整數 | −2,147,483,648 ～ 2,147,483,647 |
| `char` | 8 位元有號整數 | −128 ～ 127 |
| `void` | 僅用於函式回傳型別 | — |
| 指標 `*` | 同 `int`（記憶體位址） | 0 ～ 65535 |

整數截斷：所有 `int` 運算結果均截斷為 32 位元有號整數範圍；`char` 賦值截斷為 8 位元有號整數範圍。

### 5.2 常數字面量

| 類型 | 範例 | 說明 |
|------|------|------|
| 十進位整數 | `42`, `-100` | 標準十進位表示 |
| 十六進位整數 | `0xFF`, `0xAB` | 前綴 `0x` 或 `0X` |
| 字元字面量 | `'A'`, `'\n'`, `'\0'` | 單引號包圍，支援跳脫序列 |
| 字串字面量 | `"hello\n"` | 雙引號包圍，儲存為 C 字串（null 結尾） |

支援的跳脫序列：`\n`、`\t`、`\r`、`\\`、`\'`、`\"`、`\0`。

### 5.3 運算子

**優先順序（由低至高）：**

| 優先順序 | 運算子 | 結合性 |
|---------|-------|-------|
| 1（最低） | `=` `+=` `-=` `*=` `/=` `%=` | 右至左 |
| 2 | `\|\|` | 左至右 |
| 3 | `&&` | 左至右 |
| 4 | `\|` | 左至右 |
| 5 | `^` | 左至右 |
| 6 | `&` | 左至右 |
| 7 | `==` `!=` | 左至右 |
| 8 | `<` `<=` `>` `>=` | 左至右 |
| 9 | `<<` `>>` | 左至右 |
| 10 | `+` `-` | 左至右 |
| 11 | `*` `/` `%` | 左至右 |
| 12（最高） | 前置 `++` `--` `!` `~` `-` `*` `&` | 右至左 |

**語意說明：**
- `%` 使用 C 語言截斷除法語意（符號跟隨被除數），而非 Python 的地板除法語意
- `&&` 與 `||` 支援短路求值（short-circuit evaluation）
- 前置 `++`/`--` 先修改值再使用；**不支援後置** `++`/`--`

### 5.4 宣告

```c
// 一般變數（可帶初始值）
int x;
int y = 42;
char c = 'A';

// 陣列（固定大小，索引從 0 起）
int arr[10];
char buf[50];
int data[5] = {1, 2, 3, 4, 5};

// 指標
int *p;
char *s;
```

**限制：** 依據規格，區域變數宣告應集中於函式開頭，不支援在區塊中途宣告變數。

### 5.5 函式

```c
// 函式定義
int add(int a, int b) {
    return a + b;
}

// 回傳指標的函式
int *get_ptr(int *arr, int i) {
    return &arr[i];
}

// void 函式
void print_hello() {
    printf("Hello\n");
}

// 程式進入點（緩衝模式需要）
int main() {
    return 0;
}
```

支援遞迴呼叫。參數傳遞為**值傳遞**；若要修改呼叫端變數，需傳遞指標。

### 5.6 控制流程

**條件：**
```c
if (x > 0) {
    printf("positive\n");
} else {
    printf("non-positive\n");
}
```

**迴圈：**
```c
while (i < n) { i += 1; }

for (i = 0; i < n; i += 1) { ... }

do {
    ...
} while (condition);
```

**Switch（支援 fall-through）：**
```c
switch (x) {
    case 1:
        printf("one\n");
        break;
    case 2:
    case 3:
        printf("two or three\n");
        break;
    default:
        printf("other\n");
}
```

**跳轉：**
- `break` — 跳出最近的迴圈或 switch
- `continue` — 跳到最近迴圈的下一次迭代
- `return` / `return expr` — 從函式返回

### 5.7 前置處理器

支援無參數的 `#define` 巨集：

```c
#define SIZE 8
#define MAX_VAL 1000
```

展開規則：以識別字邊界為準進行文字替換，不會誤替換識別字內的子串。

**不支援：** 帶參數的函式式巨集、`#include`。

### 5.8 註解

```c
// 單行註解：從 // 到行尾

/* 區塊註解：
   可跨越多行 */
```

---

## 6. 內建函式規格

### 6.1 I/O 函式

| 函式 | 簽名 | 說明 |
|------|------|------|
| `printf` | `void printf(char *fmt, ...)` | 格式化輸出；支援 `%d`（十進位整數）、`%c`（字元）、`%s`（字串）、`%x`（十六進位）、`%%`（百分號） |
| `scanf` | `int scanf(char *fmt, ...)` | 格式化輸入；支援 `%d`（讀入整數）、`%c`（讀入字元）；回傳成功讀入的項目數 |
| `putchar` | `int putchar(int ch)` | 輸出單一字元，回傳輸出的字元值 |
| `getchar` | `int getchar()` | 讀入單一字元，回傳字元的 ASCII 值；EOF 時回傳 -1 |
| `puts` | `void puts(char *s)` | 輸出字串並自動換行 |

### 6.2 字串函式

| 函式 | 簽名 | 說明 |
|------|------|------|
| `strlen` | `int strlen(char *s)` | 回傳字串長度（不含結尾 null） |
| `strcpy` | `void strcpy(char *dest, char *src)` | 將 `src` 複製到 `dest`（含結尾 null） |
| `strcmp` | `int strcmp(char *s1, char *s2)` | 比較兩字串；s1 < s2 回傳負值，相等回傳 0，s1 > s2 回傳正值 |
| `strcat` | `void strcat(char *dest, char *src)` | 將 `src` 附加到 `dest` 末尾 |

### 6.3 數學函式

| 函式 | 簽名 | 說明 |
|------|------|------|
| `abs` | `int abs(int x)` | 回傳絕對值 |
| `max` | `int max(int a, int b)` | 回傳較大值 |
| `min` | `int min(int a, int b)` | 回傳較小值 |
| `pow` | `int pow(int base, int exp)` | 回傳 base 的 exp 次方（整數） |
| `sqrt` | `int sqrt(int x)` | 回傳正整數平方根（截斷取整）；引數為負時產生執行期錯誤 |
| `mod` | `int mod(int a, int b)` | 同 `%` 運算子（C 語意截斷除法之餘數） |
| `rand` | `int rand()` | 回傳偽隨機整數 |
| `srand` | `void srand(int seed)` | 設定隨機數種子 |

### 6.4 工具函式

| 函式 | 簽名 | 說明 |
|------|------|------|
| `memset` | `void memset(char *ptr, int value, int size)` | 將 `size` 個記憶體單元設為 `value` |
| `sizeof_int` | `int sizeof_int()` | 回傳 `int` 型別大小（固定為 4） |
| `sizeof_char` | `int sizeof_char()` | 回傳 `char` 型別大小（固定為 1） |
| `atoi` | `int atoi(char *s)` | 將數字字串轉為整數 |
| `itoa` | `void itoa(int value, char *str)` | 將整數轉為十進位字串存入 `str` |
| `exit` | `void exit(int code)` | 以指定回傳碼終止程式 |

---

## 7. 錯誤處理規格

所有錯誤均捕捉於 REPL 層，印出訊息後回到 `sc>` 提示符，解譯器不崩潰。

### 7.1 語法錯誤

```
Syntax error at line 3: unexpected token ';', expected expression.
Lexical error at line 5: unterminated string literal.
```

### 7.2 執行期錯誤

| 錯誤情境 | 訊息格式 |
|---------|---------|
| 除以零 | `Runtime error: division by zero.` |
| 陣列索引越界 | `Runtime error: array index out of bounds (index 10, size 5).` |
| `sqrt()` 引數為負 | `Runtime error: sqrt() argument must be non-negative.` |
| 記憶體不足 | `Runtime error: Out of memory` |
| 記憶體存取越界 | `Runtime error: Memory access out of bounds: address N` |
| 函式參數數量錯誤 | 執行期錯誤，顯示函式名稱與期望/實際參數數量 |

### 7.3 互動模式的 `exit()` 呼叫

```
Program exited with return value N.
```

---

## 8. 系統架構

### 8.1 管線架構

資料從原始碼到輸出，嚴格單向流動：

```
原始碼（字串）
    │
    ▼
preprocess()           ← 展開 #define 巨集
    │
    ▼
Lexer.tokenize()       ← 詞法分析，產生 Token 序列
    │  Token(kind, value, line)
    ▼
Parser.parse()         ← 語法分析，產生 AST
    │  Program / FuncDef / Stmt / Expr 節點
    ▼
Interpreter.execute()  ← 樹狀走訪，直接執行
    │
    ▼
標準輸出（stdout）
```

### 8.2 記憶體模型

採用線性堆疊式配置器（bump allocator）：

- 全域空間大小：65,536 個整數單元
- `allocate(n)`：從 `heap_top` 往高位址方向延伸 n 個單元
- `free_to(addr)`：將 `heap_top` 回退到 `addr`，批次釋放函式的區域變數
- 所有變數、陣列、字串均配置於此空間

### 8.3 符號表模型

採用作用域堆疊：

- `scopes[0]` — 全域作用域（永久保留）
- `scopes[1+]` — 每次函式呼叫時 push，函式返回時 pop
- `lookup()` 由內向外搜尋，實現 C 語言的變數遮蔽（shadowing）語意

### 8.4 控制流程實作

`break`、`continue`、`return` 透過 Python 例外實作：

| 控制流程 | Python 例外 | 捕捉點 |
|---------|------------|-------|
| `break` | `BreakException` | 最近的迴圈或 switch |
| `continue` | `ContinueException` | 最近的迴圈 |
| `return expr` | `ReturnException(value)` | 函式呼叫點 |

---

## 9. 模組說明

| 檔案 | 職責 |
|------|------|
| `main.py` | 程式進入點，實例化 `REPL` 並呼叫 `run()` |
| `lexer.py` | `preprocess()`（#define 展開）+ `Lexer`（詞法分析器）+ `Token` 資料類別 |
| `parser.py` | 所有 AST 節點類別（`Expr` / `Stmt` / `FuncDef` / `Program` 階層）+ `Parser`（遞迴下降解析器） |
| `interpreter.py` | `Interpreter`（AST 樹狀走訪直譯器）；包含 `BreakException`、`ContinueException`、`ReturnException` |
| `symtable.py` | `SymbolTable`（作用域堆疊）+ `Symbol`（型別、位址、指標/陣列旗標） |
| `memory.py` | `Memory`（線性記憶體空間）；提供 allocate / free_to / read / write / read_string / write_string |
| `builtins_funcs.py` | `Builtins`；實作所有內建函式的分派與執行邏輯 |
| `repl.py` | `ReplInputCollector`（多行輸入收集器）+ `REPL`（互動環境主體） |

---

## 10. 程式範例

### 10.1 遞迴：費波那契數列

```c
int fib(int n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i;
    for (i = 0; i <= 10; i += 1) {
        printf("fib(%d) = %d\n", i, fib(i));
    }
    return 0;
}
```

### 10.2 指標與陣列：泡沫排序

```c
void swap(int *a, int *b) {
    int temp;
    temp = *a;
    *a = *b;
    *b = temp;
}

int main() {
    int arr[5];
    int i;
    int j;
    arr[0] = 5; arr[1] = 3; arr[2] = 8; arr[3] = 1; arr[4] = 4;

    for (i = 0; i < 4; i += 1) {
        for (j = 0; j < 4 - i; j += 1) {
            if (arr[j] > arr[j + 1]) {
                swap(&arr[j], &arr[j + 1]);
            }
        }
    }

    for (i = 0; i < 5; i += 1) {
        printf("%d ", arr[i]);
    }
    printf("\n");
    return 0;
}
```

### 10.3 字串處理

```c
#define BUF_SIZE 64

int main() {
    char buf[BUF_SIZE];
    char name[20];

    strcpy(name, "Small-C");
    strcpy(buf, "Hello, ");
    strcat(buf, name);
    strcat(buf, "!");

    printf("%s\n", buf);
    printf("Length: %d\n", strlen(buf));
    return 0;
}
```

### 10.4 互動模式快速測試

```
sc> printf("%d\n", 3 + 4 * 5);
23
sc> int x = 100;
sc> printf("sqrt(%d) = %d\n", x, sqrt(x));
sqrt(100) = 10
sc> VARS
  int x = 100
```
