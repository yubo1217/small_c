class Memory:
    def __init__(self, size=65536):
        self.data = [0] * size
        self.heap_top = 0

    def allocate(self, size):
        addr = self.heap_top
        self.heap_top += size
        if self.heap_top > len(self.data):
            raise RuntimeError("Out of memory")
        return addr

    def free_to(self, addr):
        """回收到指定位址（用於函式返回時釋放區域變數）"""
        self.heap_top = addr

    def read(self, addr):
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        return self.data[addr]

    def write(self, addr, value):
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        # Small-C int 是 32 位元有號整數
        value = int(value)
        value = ((value + 2**31) % 2**32) - 2**31
        self.data[addr] = value

    def write_char(self, addr, value):
        if addr < 0 or addr >= self.heap_top:
            raise RuntimeError(f"Memory access out of bounds: address {addr}")
        # char 是 8 位元有號整數
        value = int(value)
        value = ((value + 128) % 256) - 128
        self.data[addr] = value

    def read_string(self, addr):
        result = ""
        while True:
            if addr < 0 or addr >= self.heap_top:
                raise RuntimeError(f"Memory access out of bounds: address {addr}")
            ch = self.data[addr]
            if ch == 0:
                break
            result += chr(ch)
            addr += 1
        return result

    def write_string(self, addr, s):
        for ch in s:
            self.write_char(addr, ord(ch))
            addr += 1
        self.write_char(addr, 0)  # null terminator

    def reset(self):
        """NEW 指令或 RUN 前清除所有記憶體"""
        self.data = [0] * len(self.data)
        self.heap_top = 0