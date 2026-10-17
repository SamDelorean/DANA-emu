#!/usr/bin/env python3
"""Assemble original D1.2 fixtures with the installed LLVM M68k MC backend.
No package installation and no custom opcode encoder. STOP is emitted with
.short because LLVM 19's M68k parser lacks its immediate syntax; opcode 4e72
is verified in pinned MAME m68000.lst. Decode all resulting instructions with
LLVM's separate disassembler. Generated objects must have no relocations.
"""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
from pathlib import Path
import struct

PIN = 'c4e48388ca620472643110db2941ce70aa5f3c07'
MAIN = [
    'MOVEA.L #$00010000,A0', 'MOVE.B #$A5,1(A0)',
    'MOVE.W #$BEEF,2(A0)', 'MOVE.L #$12345678,4(A0)',
    'MOVE.L #$89ABCDEF,10(A0)', 'MOVE.B 1(A0),D0',
    'MOVE.W 2(A0),D1', 'MOVE.L 4(A0),D2', 'MOVE.L 10(A0),D3',
    'STOP #$2700']
PROGRAMS = {'RAM-01': MAIN,
    'RAM-02': ['MOVEA.L #$80,A0', 'MOVE.L #$12345678,(A0)', 'MOVE.L (A0),D0', 'STOP #$2700'],
    'RAM-03': ['MOVEA.L #$003FFFFE,A0', 'MOVE.W #$BEEF,(A0)', 'MOVE.W (A0),D0', 'STOP #$2700'],
    'RAM-04': ['MOVEA.L #$003FFFFC,A0', 'MOVE.L #$12345678,(A0)', 'MOVE.L (A0),D0', 'STOP #$2700'],
    'RAM-05': ['MOVEA.L #$003FFFFF,A0', 'MOVE.B #$A5,(A0)', 'MOVE.B (A0),D0', 'STOP #$2700'],
    'RAM-06': ['MOVEA.L #$00010000,A0', 'MOVE.W 1(A0),D0', 'STOP #$2700'],
    'RAM-07': ['MOVEA.L #$00010000,A0', 'MOVE.L 1(A0),D0', 'STOP #$2700'],
    'RAM-08': ['MOVEA.L #$00400000,A0', 'MOVE.L #$DEADBEEF,(A0)', 'MOVE.L (A0),D0', 'STOP #$2700']}

def sha(data):
    return hashlib.sha256(data).hexdigest()

class LLVM:
    def __init__(self, library):
        self.lib = C.CDLL(library)
        for part in ('TargetInfo', 'Target', 'TargetMC', 'AsmParser', 'AsmPrinter', 'Disassembler'):
            getattr(self.lib, 'LLVMInitializeM68k' + part)()
        self.ptr, self.string, self.integer = C.c_void_p, C.c_char_p, C.c_int
        self.context = self.call('LLVMContextCreate', self.ptr, [])()
        target = self.ptr(); error = self.string()
        rc = self.call('LLVMGetTargetFromTriple', self.integer,
                       [self.string, C.POINTER(self.ptr), C.POINTER(self.string)])(
                           b'm68k-unknown-linux-gnu', C.byref(target), C.byref(error))
        if rc:
            raise RuntimeError(error.value)
        self.machine = self.call('LLVMCreateTargetMachine', self.ptr,
            [self.ptr, self.string, self.string, self.string, self.integer, self.integer, self.integer])(
                target, b'm68k-unknown-linux-gnu', b'M68000', b'', 0, 0, 0)
        self.dis = self.call('LLVMCreateDisasmCPU', self.ptr,
            [self.string, self.string, self.ptr, self.integer, self.ptr, self.ptr])(
                b'm68k-unknown-linux-gnu', b'M68000', None, 0, None, None)
        if not self.machine or not self.dis:
            raise RuntimeError('BLOCKED: LLVM M68000 backend unavailable')

    def call(self, name, restype, args):
        fun = getattr(self.lib, name); fun.restype = restype; fun.argtypes = args
        return fun

    def assemble(self, source):
        module = self.call('LLVMModuleCreateWithNameInContext', self.ptr, [self.string, self.ptr])(b'fixture', self.context)
        text = ('.text\n' + source + '\n').encode()
        self.call('LLVMSetModuleInlineAsm2', None, [self.ptr, self.string, C.c_size_t])(module, text, len(text))
        self.call('LLVMSetTarget', None, [self.ptr, self.string])(module, b'm68k-unknown-linux-gnu')
        error = self.string(); buf = self.ptr()
        rc = self.call('LLVMTargetMachineEmitToMemoryBuffer', self.integer,
                       [self.ptr, self.ptr, self.integer, C.POINTER(self.string), C.POINTER(self.ptr)])(
                           self.machine, module, 1, C.byref(error), C.byref(buf))
        if rc:
            raise RuntimeError(error.value)
        data = C.string_at(self.call('LLVMGetBufferStart', self.ptr, [self.ptr])(buf),
                           self.call('LLVMGetBufferSize', C.c_size_t, [self.ptr])(buf))
        assert data[:6] == b'\x7fELF\x01\x02', 'Expected big-endian ELF32'
        shoff = struct.unpack_from('>I', data, 32)[0]
        size, count, names = struct.unpack_from('>HHH', data, 46)
        sections = [struct.unpack_from('>IIIIIIIIII', data, shoff + i * size) for i in range(count)]
        strings = data[sections[names][4]:sections[names][4] + sections[names][5]]
        result = None
        for sec in sections:
            assert sec[1] not in (4, 9) or sec[5] == 0, 'Fixture contains relocations'
            if strings[sec[0]:].split(b'\0', 1)[0] == b'.text':
                result = data[sec[4]:sec[4] + sec[5]]
        self.call('LLVMDisposeMemoryBuffer', None, [self.ptr])(buf)
        self.call('LLVMDisposeModule', None, [self.ptr])(module)
        assert result
        return result

    def decode(self, data, pc):
        buf = C.create_string_buffer(data); text = C.create_string_buffer(256)
        size = self.call('LLVMDisasmInstruction', C.c_size_t,
                        [self.ptr, self.ptr, C.c_uint64, C.c_uint64, self.ptr, C.c_size_t])(
                            self.dis, buf, len(data), pc, text, len(text))
        if not size and data == bytes.fromhex('4e722700'):
            # Pinned MAME m68000.lst: 4e72 ffff stop i16u.
            return 4, 'stop #$2700 [pinned MAME opcode-table decode]'
        if not size:
            raise RuntimeError('BLOCKED: LLVM could not disassemble fixture at ' + hex(pc))
        return size, text.value.decode().strip()

def dialect(line):
    if line == 'STOP #$2700':
        return '.short 0x4e72, 0x2700'
    import re
    line = line.lower().replace('movea.l', 'move.l').replace('$', '0x')
    line = re.sub(r'\b([ad][0-7])\b', r'%\1', line)
    return re.sub(r'(\d+)\((%a[0-7])\)', r'(\1,\2)', line)

def generate(library):
    llvm = LLVM(library); result = {'mame_commit': PIN, 'assembler': 'LLVM M68k MC (M68000)', 'cases': {}}
    for name, program in PROGRAMS.items():
        data = b''; instructions = []
        for source in program:
            code = llvm.assemble(dialect(source))
            length, disassembly = llvm.decode(code, 0x4000 + len(data))
            assert length == len(code), (source, code.hex(), length)
            instructions.append({'pc': 0x4000 + len(data), 'hex': code.hex(),
                                 'source': source, 'disassembly': disassembly})
            data += code
        result['cases'][name] = {'hex': data.hex(), 'length': len(data), 'sha256': sha(data),
                                 'instructions': instructions, 'stop_pc': instructions[-1]['pc'],
                                 'endpoint': 0x5000 if name in ('RAM-06', 'RAM-07') else instructions[-1]['pc']}
    handler = llvm.assemble('.short 0x4e72, 0x2700')
    result['handler'] = {'address': 0x5000, 'hex': handler.hex(), 'sha256': sha(handler),
                         'disassembly': llvm.decode(handler, 0x5000)[1]}
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New fixture directory (must not exist)')
    parser.add_argument('--llvm-library', default=ctypes.util.find_library('LLVM-19') or 'libLLVM.so.19.1')
    opts = parser.parse_args()
    fixtures = generate(opts.llvm_library)
    opts.output.mkdir(parents=True, exist_ok=False)
    for name, case in fixtures['cases'].items():
        (opts.output / (name + '.bin')).write_bytes(bytes.fromhex(case['hex']))
        (opts.output / (name + '.s')).write_text('\n'.join(i['source'] for i in case['instructions']) + '\n')
        (opts.output / (name + '.dis')).write_text('\n'.join(f"{i['pc']:08x} {i['hex']} {i['disassembly']}" for i in case['instructions']) + '\n')
    (opts.output / 'fixtures.json').write_text(json.dumps(fixtures, indent=2) + '\n')
    print(json.dumps({k: {'length': v['length'], 'sha256': v['sha256']} for k, v in fixtures['cases'].items()}, indent=2))
