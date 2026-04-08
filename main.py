"""
main.py — Small-C 互動式直譯器的程式進入點
==========================================
執行本檔案即可啟動 Small-C 互動式直譯器（REPL）。

啟動方式：
    python main.py

啟動後會顯示歡迎畫面並進入互動提示符（sc>），
輸入 HELP 可查看所有可用指令，輸入 QUIT 或 EXIT 離開。
"""

from repl import REPL


def main():
    """建立 REPL 實例並啟動互動迴圈。"""
    repl = REPL()
    repl.run()


if __name__ == '__main__':
    main()