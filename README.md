```
.|'''|  |''||''| '||\   /||` ,'''|,  ''|, '||''''|    /||   .''',  ||  
||         ||     ||\\.//||      || '  ||  ||  .    // ||   |   | '||  
`|'''|,    ||     ||     ||   '''||   .|'  ||''|   //..||.. |   |  ||  
 .   ||    ||     ||     ||      ||  //    ||          ||   |   |  ||  
 |...|'   .||.   .||     ||. '...|' ((... .||.         ||   `,,,' .||. 
                                                                       
```

### Overview

This repository contains a number of helpers for attempting to reverse
engineer devices using an STM32F401 microcontroller. Though these tools
may work on other STM32 platforms they have not been tested.

The main components in this repository are intended to provide helpers for
loading firmware dumps into IDA - assisting with patching up a few common
issues to assist with getting initial auto-analysis working. In addition,
this repository contains a `Vagrantfile` which will provision a CentOS 8
virtual machine with a patched version of beckus' STM32 `qemu` fork in order
to provide a virtual platform in which dynamic analysis can be performed.

As below, this is tested and confirmed working for a device which uses an
STM32F401 - though there are some issues currently, as the patch does not
completely emulate the device.

![STM32F401](./docs/images/gdb-attach.png?raw=true)

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

In order to use these scripts, perform the following:

1. Load the dumped binary into IDA as a 'binary file', with the processor set
to ARM.
1. Set the appropriate RAM and ROM sections marked when prompted.
1. Run the script(s) via 'Run script' from the 'File' menu.
1. Wait for the script to complete - which may take some time.

Once complete, a summary of the script operations should be printed to the
output window.

### VM Usage

The `Vagrantfile` in the root of this repository will attempt to build a
CentOS 8 VM, and compile `qemu` with support for an STM32F401. This is
powered by a slightly tweaked version of the the amazing work already
done by beckus' STM32 qemu fork:

* https://github.com/beckus/qemu_stm32.git

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
vagrant ssh -- -L1234:127.0.0.1:1234  # If required.
arm-none-eabi-gdb -q
set disassemble-next-line on
target remote 127.0.0.1:1234
```

### References

* [ST STM32F401RE Documentation](https://www.st.com/en/microcontrollers-microprocessors/stm32f401re.html)
* [Beckus' qemu_stm32](https://github.com/beckus/qemu_stm32.git)
