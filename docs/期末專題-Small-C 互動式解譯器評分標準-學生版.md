# Small-C 互動式解譯器：期末專題驗收測試腳本

**課程名稱：** 系統軟體（System Software）
**適用學期：** Spring 2026
**文件用途：** 教師驗收學生繳交之 Small-C 解譯器時使用
**測試腳本數量：** 共五份（測試 A 為公開版，測試 B–E 為驗收用抽選版）

---

## 使用說明

本文件包含五份難度相當的測試腳本，每一份均完整涵蓋作業說明中所有語言規範與互動環境指令。

**覆蓋範圍一致性：** 每份測試腳本均涵蓋以下所有項目——基本算術與運算子優先順序、關係與邏輯運算（含短路求值）、位元運算、變數宣告與指定（含複合指定）、if/else 條件分支、while 迴圈、for 迴圈、do/while 迴圈、break 與 continue、一維陣列、指標操作（取址與取值）、函式定義與遞迴呼叫、所有內建函式類別（I/O、字串、數學、工具）、字元與跳脫序列、十六進位常數、#define 常數、註解（單行與區塊）、以及所有互動環境指令。

**難度等價性：** 五份測試腳本使用不同的演算法主題，但每份所測試的語言特性數量、互動指令數量、以及預期錯誤偵測項目均保持一致。

**驗收流程：** 請學生啟動其 Small-C 解譯器，由教師依照測試腳本逐步口述或投影指令，由學生在解譯器中輸入。教師對照腳本中的「預期輸出」欄位，確認每一步的執行結果是否正確。

---

## 評分記錄表（每份測試腳本通用）

| 測試類別 | 測試項目 | 通過 | 未通過 | 備註 |
|---------|---------|------|-------|------|
| 互動指令 | ABOUT | ☐ | ☐ | |
| 互動指令 | HELP | ☐ | ☐ | |
| 互動指令 | APPEND | ☐ | ☐ | |
| 互動指令 | LIST / LIST n / LIST n1-n2 | ☐ | ☐ | |
| 互動指令 | EDIT | ☐ | ☐ | |
| 互動指令 | DELETE | ☐ | ☐ | |
| 互動指令 | INSERT | ☐ | ☐ | |
| 互動指令 | CHECK | ☐ | ☐ | |
| 互動指令 | RUN | ☐ | ☐ | |
| 互動指令 | SAVE | ☐ | ☐ | |
| 互動指令 | NEW | ☐ | ☐ | |
| 互動指令 | LOAD | ☐ | ☐ | |
| 互動指令 | TRACE ON/OFF | ☐ | ☐ | |
| 互動指令 | VARS | ☐ | ☐ | |
| 互動指令 | FUNCS | ☐ | ☐ | |
| 互動指令 | CLEAR | ☐ | ☐ | |
| 語言特性 | 算術運算與優先順序 | ☐ | ☐ | |
| 語言特性 | 關係與邏輯運算 | ☐ | ☐ | |
| 語言特性 | 位元運算 | ☐ | ☐ | |
| 語言特性 | 變數宣告與指定 | ☐ | ☐ | |
| 語言特性 | if/else 條件分支 | ☐ | ☐ | |
| 語言特性 | while 迴圈 | ☐ | ☐ | |
| 語言特性 | for 迴圈 | ☐ | ☐ | |
| 語言特性 | do/while 迴圈 | ☐ | ☐ | |
| 語言特性 | break 與 continue | ☐ | ☐ | |
| 語言特性 | 陣列操作 | ☐ | ☐ | |
| 語言特性 | 指標操作 | ☐ | ☐ | |
| 語言特性 | 函式定義與呼叫 | ☐ | ☐ | |
| 語言特性 | 遞迴 | ☐ | ☐ | |
| 語言特性 | 內建 I/O 函式 | ☐ | ☐ | |
| 語言特性 | 內建字串函式 | ☐ | ☐ | |
| 語言特性 | 內建數學函式 | ☐ | ☐ | |
| 語言特性 | 內建工具函式 | ☐ | ☐ | |
| 語言特性 | 字元與跳脫序列 | ☐ | ☐ | |
| 語言特性 | 十六進位常數 | ☐ | ☐ | |
| 語言特性 | #define 常數 | ☐ | ☐ | |
| 語言特性 | 註解 | ☐ | ☐ | |
| 錯誤處理 | 語法錯誤偵測 | ☐ | ☐ | |
| 錯誤處理 | 執行期錯誤偵測 | ☐ | ☐ | |

---

## 測試 A（公開版——事先提供給學生自行測試）

**主題：陣列統計與選擇排序**

### 步驟 1：啟動與系統指令

啟動解譯器，確認歡迎畫面正常顯示。

```
sc> ABOUT
```

**預期輸出：** 顯示解譯器名稱、版本號、作者資訊與修課學期。（具體內容依學生實作而定，但必須包含上述四項資訊。）

```
sc> HELP
```

**預期輸出：** 顯示所有可用環境指令的摘要說明，至少包含 LOAD、SAVE、LIST、EDIT、DELETE、INSERT、APPEND、NEW、RUN、CHECK、TRACE、VARS、FUNCS、HELP、ABOUT、CLEAR、QUIT/EXIT。

### 步驟 2：互動模式——基本算術與運算子優先順序

```
sc> printf("%d\n", 3 + 4 * 5 - 2);
```

**預期輸出：**
```
21
```

```
sc> printf("%d\n", (3 + 4) * (5 - 2));
```

**預期輸出：**
```
21
```

```
sc> printf("%d\n", 100 / 7);
```

**預期輸出：**
```
14
```

```
sc> printf("%d\n", 100 % 7);
```

**預期輸出：**
```
2
```

```
sc> printf("%d\n", -15 / 4);
```

**預期輸出：**
```
-3
```

### 步驟 3：互動模式——關係、邏輯與位元運算

```
sc> printf("%d %d %d\n", 10 > 5, 10 < 5, 10 == 10);
```

**預期輸出：**
```
1 0 1
```

```
sc> printf("%d %d\n", 10 > 5 && 3 < 1, 10 > 5 || 3 < 1);
```

**預期輸出：**
```
0 1
```

```
sc> printf("%d\n", 0xAB & 0x0F);
```

**預期輸出：**
```
11
```

```
sc> printf("%d\n", 1 << 10);
```

**預期輸出：**
```
1024
```

```
sc> printf("0x%x\n", 0xF0 | 0x0D);
```

**預期輸出：**
```
0xfd
```

### 步驟 4：互動模式——變數、字元與數學函式

```
sc> int x = 25;
sc> int y = -18;
sc> printf("abs(%d) = %d\n", y, abs(y));
```

**預期輸出：**
```
abs(-18) = 18
```

```
sc> printf("max=%d, min=%d\n", max(x, 30), min(x, 30));
```

**預期輸出：**
```
max=30, min=25
```

```
sc> printf("pow(2,16) = %d\n", pow(2, 16));
```

**預期輸出：**
```
pow(2,16) = 65536
```

```
sc> printf("sqrt(625) = %d\n", sqrt(625));
```

**預期輸出：**
```
sqrt(625) = 25
```

```
sc> char ch = 'Z';
sc> printf("ch=%c, code=%d, next=%c\n", ch, ch, ch + 1);
```

**預期輸出：**
```
ch=Z, code=90, next=[
```

（注：ASCII 91 為 `[`。）

```
sc> VARS
```

**預期輸出：** 應至少顯示 int x = 25、int y = -18、char ch = 90 ('Z') 或等效表示。

### 步驟 5：互動模式——字串函式與工具函式

```
sc> char buf[50];
sc> strcpy(buf, "System");
sc> strcat(buf, " Software");
sc> printf("buf=\"%s\", len=%d\n", buf, strlen(buf));
```

**預期輸出：**
```
buf="System Software", len=15
```

```
sc> printf("cmp=%d\n", strcmp("apple", "banana"));
```

**預期輸出：** 回傳一個負整數（具體值依實作而定，但必須為負數）。
```
cmp=-1
```

```
sc> printf("atoi=%d\n", atoi("2026"));
```

**預期輸出：**
```
atoi=2026
```

```
sc> char numstr[20];
sc> itoa(12345, numstr);
sc> printf("itoa result: %s\n", numstr);
```

**預期輸出：**
```
itoa result: 12345
```

### 步驟 6：清除狀態並使用 APPEND 輸入程式

```
sc> NEW
```

**預期輸出：** 若先前有未儲存的修改，應提示確認；確認後顯示清除訊息。

```
sc> APPEND
   1> /* Selection Sort with Statistics */
   2> #define SIZE 8
   3>
   4> // Swap two integers via pointers
   5> void swap(int *a, int *b) {
   6>     int temp;
   7>     temp = *a;
   8>     *a = *b;
   9>     *b = temp;
  10> }
  11>
  12> void selection_sort(int *arr, int n) {
  13>     int i;
  14>     int j;
  15>     int min_idx;
  16>     for (i = 0; i < n - 1; i = i + 1) {
  17>         min_idx = i;
  18>         for (j = i + 1; j < n; j = j + 1) {
  19>             if (arr[j] < arr[min_idx]) {
  20>                 min_idx = j;
  21>             }
  22>         }
  23>         if (min_idx != i) {
  24>             swap(&arr[i], &arr[min_idx]);
  25>         }
  26>     }
  27> }
  28>
  29> int compute_sum(int *arr, int n) {
  30>     int i;
  31>     int total = 0;
  32>     for (i = 0; i < n; i = i + 1) {
  33>         total += arr[i];
  34>     }
  35>     return total;
  36> }
  37>
  38> int find_max(int *arr, int n) {
  39>     int i;
  40>     int m = arr[0];
  41>     for (i = 1; i < n; i = i + 1) {
  42>         m = max(m, arr[i]);
  43>     }
  44>     return m;
  45> }
  46>
  47> int find_min(int *arr, int n) {
  48>     int i;
  49>     int m = arr[0];
  50>     for (i = 1; i < n; i = i + 1) {
  51>         m = min(m, arr[i]);
  52>     }
  53>     return m;
  54> }
  55>
  56> int main() {
  57>     int data[SIZE];
  58>     int i;
  59>     int total;
  60>
  61>     data[0] = 64; data[1] = 25; data[2] = 12; data[3] = 22;
  62>     data[4] = 11; data[5] = 90; data[6] = 45; data[7] = 33;
  63>
  64>     printf("Original: ");
  65>     for (i = 0; i < SIZE; i = i + 1) {
  66>         printf("%d ", data[i]);
  67>     }
  68>     printf("\n");
  69>
  70>     printf("Max = %d\n", find_max(data, SIZE));
  71>     printf("Min = %d\n", find_min(data, SIZE));
  72>
  73>     total = compute_sum(data, SIZE);
  74>     printf("Sum = %d\n", total);
  75>     printf("Avg = %d\n", total / SIZE);
  76>
  77>     selection_sort(data, SIZE);
  78>
  79>     printf("Sorted:   ");
  80>     for (i = 0; i < SIZE; i = i + 1) {
  81>         printf("%d ", data[i]);
  82>     }
  83>     printf("\n");
  84>
  85>     return 0;
  86> }
  87> .
```

### 步驟 7：LIST 指令驗證

```
sc> LIST 1-5
```

**預期輸出：**
```
   1: /* Selection Sort with Statistics */
   2: #define SIZE 8
   3:
   4: // Swap two integers via pointers
   5: void swap(int *a, int *b) {
```

```
sc> LIST 56
```

**預期輸出：**
```
  56: int main() {
```

### 步驟 8：CHECK 與 RUN

```
sc> CHECK
```

**預期輸出：**
```
No errors found.
```

```
sc> RUN
```

**預期輸出：**
```
Original: 64 25 12 22 11 90 45 33
Max = 90
Min = 11
Sum = 302
Avg = 37
Sorted:   11 12 22 25 33 45 64 90
Program exited with return value 0.
```

### 步驟 9：FUNCS 指令

```
sc> FUNCS
```

**預期輸出：** 應列出 swap、selection_sort、compute_sum、find_max、find_min、main 六個使用者定義函式（含回傳型別、參數與行號），以及所有內建函式（標示 [built-in]）。

### 步驟 10：SAVE 與 EDIT 修改程式

```
sc> SAVE test_a.sc
```

**預期輸出：** 顯示成功儲存的行數（87 行）。

```
sc> EDIT 62
```

**預期輸出：** 顯示第 62 行目前內容，等候使用者輸入新內容。

輸入以下新內容取代第 62 行：
```
    data[4] = 11; data[5] = 90; data[6] = 45; data[7] = 77;
```

```
sc> LIST 61-63
```

**預期輸出：** 確認第 62 行已被修改，data[7] 的值從 33 變為 77。

```
sc> RUN
```

**預期輸出：**
```
Original: 64 25 12 22 11 90 45 77
Max = 90
Min = 11
Sum = 346
Avg = 43
Sorted:   11 12 22 25 45 64 77 90
Program exited with return value 0.
```

### 步驟 11：DELETE 與 INSERT 指令

```
sc> DELETE 3
```

（刪除空白行。）

```
sc> LIST 1-5
```

**預期輸出：** 第 3 行應變為原本的第 4 行（// Swap two integers via pointers），所有行號遞減一。

```
sc> INSERT 3
   3>
   4> .
```

（插入一個空白行，恢復原來的結構。）

```
sc> LIST 1-5
```

**預期輸出：** 結構應恢復為原始狀態（但第 62 行的修改仍保留）。

### 步驟 12：TRACE 模式驗證

```
sc> NEW
```

確認清除。

```
sc> APPEND
   1> int gcd(int a, int b) {
   2>     while (b != 0) {
   3>         int temp;
   4>         temp = b;
   5>         b = a % b;
   6>         a = temp;
   7>     }
   8>     return a;
   9> }
  10>
  11> int main() {
  12>     printf("GCD(48,18) = %d\n", gcd(48, 18));
  13>     return 0;
  14> }
  15> .
sc> TRACE ON
```

**預期輸出：** 顯示追蹤模式已啟用。

```
sc> RUN
```

**預期輸出：** 在正常輸出之前或之間，應穿插顯示 [line n] <statement> 格式的追蹤資訊。最終計算結果應為：
```
GCD(48,18) = 6
Program exited with return value 0.
```

```
sc> TRACE OFF
```

**預期輸出：** 顯示追蹤模式已關閉。

### 步驟 13：do/while 與 break/continue 測試

```
sc> NEW
All cleared.
sc> int n = 1;
sc> do {
  >     if (n % 3 == 0) {
  >         n = n + 1;
  >         continue;
  >     }
  >     if (n > 12) break;
  >     printf("%d ", n);
  >     n = n + 1;
  > } while (n <= 20);
sc> printf("\n");
```

**預期輸出：**
```
1 2 4 5 7 8 10 11
```

### 步驟 14：錯誤處理測試

```
sc> printf("%d\n", 10 / 0);
```

**預期輸出：** 顯示執行期錯誤訊息，包含 division by zero 或等效描述。解譯器不應崩潰，應回到 sc> 提示符。

```
sc> printf("%d\n", sqrt(-4));
```

**預期輸出：** 顯示執行期錯誤訊息，包含 sqrt 引數不可為負或等效描述。

```
sc> int bad = ;
```

**預期輸出：** 顯示語法錯誤訊息。

```
sc> int arr[3];
sc> arr[5] = 10;
```

**預期輸出：** 顯示陣列索引越界的執行期錯誤訊息。

### 步驟 15：LOAD 與最終驗證

```
sc> NEW
All cleared.
sc> LOAD test_a.sc
```

**預期輸出：** 顯示成功載入的行數。

```
sc> RUN
```

**預期輸出：** 應為步驟 8 中首次 RUN 的輸出（因為 SAVE 是在 EDIT 之前執行的，所以載入的是原始版本）：
```
Original: 64 25 12 22 11 90 45 33
Max = 90
Min = 11
Sum = 302
Avg = 37
Sorted:   11 12 22 25 33 45 64 90
Program exited with return value 0.
```

### 步驟 16：CLEAR 與 QUIT

```
sc> CLEAR
```

**預期輸出：** 終端機畫面被清除。

```
sc> QUIT
```

**預期輸出：** 若有未儲存的修改應提示確認，確認後顯示結束訊息並退出解譯器。
