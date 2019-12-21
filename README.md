## STM32F401

### Usage

1. Launch and build `qemu` with patches.
```
vagrant up
```
1. Add images into the `images/` directory.
1. Launch `qemu`.
```
vagrant ssh
tmux

sh -c """
    while [ 1 ]; do
        echo '---- Spawning new qemu process ----'
        qemu-system-arm \
            -nographic \
            -M stm32-f401re \
            -cpu cortex-m4 \
            -gdb tcp:127.0.0.1:1234 \
            -semihosting \
            -kernel /opt/images/Netatmo_STM32F4x.bin \
            -S
    done
"""
```
1. Attach GDB.
```
vagrant ssh
arm-none-eabi-gdb
set disassemble-next-line on
target remote 127.0.0.1:1234

```