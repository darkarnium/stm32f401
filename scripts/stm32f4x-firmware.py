'''
Performs operations to load STM32F4x firmware into IDA, including:

  * Getting the reset vector, and initial stack pointer.
  * Setting the T-bit appropriately.
  * Marking the reset vector address as code, and triggering AA.

In addition to the above, once AA is complete this script will also attempt to:

  * Ensure code sections following literal pools are marked as such.
  * Ensure Strings identified by IDA are marked as string literals.
  * Ensure data references are created for all LDR operations against strings.

This script assumes that the firmware image has been loaded as a Binary file,
and that the appropriate ROM and RAM sections have been marked. This said,
mileage may vary depending on the firmware and device!
'''

import re
import idautils

ROM_ADDR_BEGIN = 0x8000000
ROM_ADDR_END = 0x807FFFF

# Define expected character sets for strings.
REGEX_CHARACTERS = r'^[\x0a\x0d\x20-\x7E]+$'

# Used to cache addresses of strings known to IDA (as int).
string_addrs = {}


def has_string_entry(addr):
    '''
    Check whether the provided address is being tracked by IDA as a string. In
    order to attempt to speed up subsequent lookups, string addresses will be
    cached into a dictionary on first use.

    Data returned will be a dictionary of strings, keyed by the address of the
    string with the length as the value.

    Args:
        addr (int): The address to check.

    Returns:
        A dictionary of string lengths keyed by their address.
    '''
    if len(string_addrs) == 0:
        for s in idautils.Strings():
            string_addrs[s.ea] = s.length

    try:
        return string_addrs[addr]
    except KeyError:
        return None


def create_string_literals(pattern=REGEX_CHARACTERS):
    '''
    Attempts to locate all NULL terminated strings known to IDA, checks whether
    they match the required regular expression, and if so, marks them as string
    literals.

    Args:
        pattern (str): The regex to match against (default: REGEX_CHARACTERS)
    
    Return:
        A list of addresses successfully marked as string literals.
    '''
    marked = set()

    for string in idautils.Strings():
        # Only look at strings that have a trailing NULL byte.
        if Byte(string.ea + string.length - 1) != 0:
            continue

        # In addition, ensure that strings adhere to the required format - as
        # defined by REGEX_CHARACTERS.
        if re.search(REGEX_CHARACTERS, str(string)):
            if create_strlit(string.ea, string.ea + string.length):
                marked.add(string.ea)  

    return marked


def get_literal_pools(s_addr, e_addr):
    '''
    Attempts to locate all potential literal pools within the provided address
    range by looking for sections which are either DATA, UNKNOWN, or TAIL and
    have a proceeding instruction of POP, or a Branch instruction.

    Args:
        s_addr (int): The starting to start scanning at.
        e_addr (int): The address to stop scanning at.
    
    Returns:
        A list of _potential_ literal pool addresses.
    '''
    pools = []

    c_addr = s_addr
    while c_addr < e_addr:
        flags = GetFlags(c_addr)
        size = get_item_size(c_addr)

        # Skip addresses marked as code.
        if isCode(flags):
            c_addr += size
            continue

        # Skip address if FF_REF flag is not set.
        if flags & 4096 != 4096:
            c_addr += size
            continue

        # Skip if the address is known to IDA as a string.
        if has_string_entry(c_addr):
            c_addr += size
            continue

        # Skip if the proceeding instruction is not another literal pool entry
        # a POP, or a branch.
        if (c_addr - 0x4) not in pools:
            # Rewind until we have a mnemonic. This is hacky, but hey this is
            # a best effort helper ;)
            p_addr = c_addr - 0x2
            while len(GetMnem(p_addr)) == 0:
                p_addr -= 0x1

            if GetMnem(p_addr) not in ['POP', 'POP.W', 'B.W', 'B']:
                c_addr += size
                continue

        # We we've not rejected this address by now, it may be a literal pool.
        pools.append(c_addr)
        c_addr += size

    return pools


def get_dword(addr):
    '''
    Attempts to get a DWORD at the provided address, marking the address as a
    DWORD before hand.

    Args:
        addr (int): The address to mark as a DWORD and return the value of.

    Return:
        The value from the specified address.
    '''
    if get_item_size(addr) < 0x4:
        create_dword(addr)

    return int(print_operand(addr, 0x4), 16)


def get_ldr_psudo_instructions(s_addr, e_addr):
    '''
    Attempts to build a dictionary of all LDR pseudo-instructions where an
    immediate value is referenced. These are pushed into a dictionary keyed by
    their address, with the immediate address as the value.

    Args:
        s_addr (int): The starting to start scanning at.
        e_addr (int): The address to stop scanning at.
    
    Returns:
        A dictionary of LDR pseudo-immediate instructions. Keyed by address,
        with the address of the immediate as the value.
    '''
    matches = dict()

    c_addr = s_addr
    while c_addr < e_addr:
        size = get_item_size(c_addr)

        # Check if this is an LDR instruction, and if so, record the address
        # and associated immediate address.
        if print_insn_mnem(c_addr) == 'LDR':
            try:
                matches[c_addr] = ida_ua.get_immvals(c_addr, 1)[0]
            except IndexError:
                pass

        c_addr += size

    return matches


def set_t(addr, value=0x1):
    '''
    Set the T-bit to the provided value at the given address. Used to mark
    whether as section is Thumb or ARM.
    
    Args:
        addr (int): The address to mark the T-bit at.
        value (int): The value to set the T-bit to (default: 0x1)
    '''
    if get_sreg(addr, 'T') == 0x0:
        set_default_sreg_value(addr, 'T', 0x1)


# Mark the T-Bit at the start of the ROM section.
set_t(ROM_ADDR_BEGIN, value=0x1)

# Get values from the vector table (per ST PM0214 2.3.4).
#
# 0x0 - Initial Stack Pointer Value.
# 0x4 - Reset Vector
#
vector_stack = get_dword(ROM_ADDR_BEGIN)
vector_reset = get_dword(ROM_ADDR_BEGIN + 4)

# Mark the reset address as ARM or Thumb - based on the LSb of the value of the
# reset vector - and mark as a procedure, waiting for auto-analysis to finish.
set_t(vector_reset, value=(vector_reset & 0x1))
reset_addr = vector_reset - (vector_reset & 0x1)
ida_auto.auto_make_proc(reset_addr)
ida_auto.auto_wait()

# Prepend 'reset_' to the name of the function at the reset vector address.
reset_name = get_func_name(reset_addr)
if reset_name.startswith('sub_'):
    set_name(reset_addr, reset_name.replace('sub_', 'reset_'))

# Manually walk the ROM section and ensure that all sections following what
# appear to be literal pools are marked as code. This is done recursively as
# new code sections may yield new literal pools.
iterations = 0
new_code_sections = set()
print('[-] Starting recursive enumeration of code following literal pools')

while True:
    marked_code = 0
    iterations += 1
    literal_pools = get_literal_pools(ROM_ADDR_BEGIN, ROM_ADDR_END)

    for addr in literal_pools:
        # If the next address is also a literal pool entry, skip this one.
        n_addr = addr + 0x4
        if n_addr in literal_pools:
            continue

        # If unknown, mark as code and wait for the AA queue to empty.
        if isUnknown(GetFlags(n_addr)):
            ida_auto.auto_make_code(n_addr)
            ida_auto.auto_wait()

            # If the address doesn't now have the FF_CODE flag after AA, then
            # it wasn't able to be processed as code.
            if isCode(GetFlags(n_addr)):
                new_code_sections.add(n_addr)
                marked_code += 1

    # Check whether we need to continue recursing.
    if marked_code == 0:
        print(
            '[+] Marked {0} new code sections in {1} iterations'.format(
                len(new_code_sections),
                iterations
            )
        )
        break

# Next up, ensure that all NULL terminated strings known to IDA are properly
# marked as string literals.
print('[-] Attempting to mark NULL terminated strings as string literals')
string_literals = create_string_literals()
print('[+] Created {0} string literals'.format(len(string_literals)))

# Attempt to create data references for any strings which are referenced as
# part of LDR instructions.
data_references = set()
print('[-] Attempting to patch-up data references for LDR pseudo instructions')

ldr_addrs = get_ldr_psudo_instructions(ROM_ADDR_BEGIN, ROM_ADDR_END)
for string in idautils.Strings():
    for addr, immediate in ldr_addrs.items():
        # Ignore the address of the string itself.
        if addr == string.ea:
            continue

        if string.ea == immediate:
            if add_dref(addr, string.ea, dr_R):
                data_references.add(addr)

print('[+] Created {0} data references'.format(len(data_references)))
