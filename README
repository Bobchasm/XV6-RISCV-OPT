# XV6-RISC-V

## 1 构建与启动

### 1.1 环境准备

Win 上使用 WSL/Ubuntu 24.04

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  gcc-riscv64-linux-gnu \
  binutils-riscv64-linux-gnu \
  qemu-system-misc \
  qemu-utils
```

### 1.2 构建运行

```bash
# 可选清理
make clean

# 构建
make -j$(nproc)

# 运行系统
make qemu
```

退出 QEMU：

```text
Ctrl a + x
```
