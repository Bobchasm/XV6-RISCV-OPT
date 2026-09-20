# XV6-RISC-V

## 1 构建与启动

### 1.1 环境准备

Win 上使用 WSL/Ubuntu 22.04 或 Ubuntu 24.04。

```bash
./scripts/setup-env.sh
```

脚本会自动检测 Ubuntu 版本，安装 RISC-V 工具链和构建依赖，并确保
`qemu-system-riscv64` 版本不低于 7.2。Ubuntu 22.04 软件源中的 QEMU
版本较旧时，脚本会自动编译并安装 QEMU 7.2.0。

也可以手动检查环境：

```bash
riscv64-linux-gnu-gcc --version
qemu-system-riscv64 --version
make --version
python3 --version
```

如果 Makefile 未自动识别工具链，可以显式指定：

```bash
export TOOLPREFIX=riscv64-linux-gnu-
```

### 1.2 构建运行

```bash
# 可选清理
make clean

# 构建，默认调度策略为 RR
make -j"$(nproc)" SCHED_DEFAULT_POLICY=SCHED_RR

# 运行系统
make qemu
```

也可以使用单 CPU 启动：

```bash
make qemu CPUS=1
```

一次构建三种调度策略镜像：

```bash
make policies
```

运行测试：

```bash
./test-xv6.py -q usertests
```

退出 QEMU：

```text
Ctrl a + x
```
