```
  _____ _______ __  __ ____ ___  ______ _  _        
 / ____|__   __|  \/  |___ \__ \|  ____| || |       
| (___    | |  | \  / | __) | ) | |__  | || |___  __
 \___ \   | |  | |\/| ||__ < / /|  __| |__   _\ \/ /
 ____) |  | |  | |  | |___) / /_| |       | |  >  < 
|_____/   |_|  |_|  |_|____/____|_|       |_| /_/\_\

```

### Script Usage

Scripts inside of the `scripts/` directory are intended for use with loading
dumped firmware from STM32F401 devices into IDA. These scripts should assist
with the following:

  * Getting the reset vector, and initial stack pointer.
  * Setting the T-bit appropriately.
  * Marking the reset vector address as code, and triggering AA.
  * Ensure code sections following literal pools are marked as such.
  * Ensure Strings identified by IDA are marked as string literals.
  * Ensure data references are created for all LDR operations against strings.

### VM Usage

The `Vagrantfile` in the root of this repository will attempt to build a
CentOS 8 VM, and compile `qemu` with support for an STM32F401. This is
powered by a slightly tweaked version of the the amazing work already
done by beckus' STM32 qemu fork:

* https://github.com/beckus/qemu_stm32.git.

In order to use this VM, you will need Vagrant and an appropriate hypervisor
installed - such as Virtualbox, or VMWare.

1. Launch and build `qemu` with patches.
```
vagrant up
```
2. Add images into the `images/` directory.
3. Launch `qemu`.
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
4. Attach GDB.
```
vagrant ssh -- -L1234:127.0.0.1:1234
arm-none-eabi-gdb
set disassemble-next-line on
target remote 127.0.0.1:1234

```
