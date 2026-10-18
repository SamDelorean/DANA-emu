"""Run bounded Lua logic checks through the installed Lua 5.4 C API (no emulator)."""
import ctypes
import ctypes.util
import os


def check_lua(source):
    name = os.environ.get('DANA_TEST_LUA54_LIBRARY') or ctypes.util.find_library('lua5.4')
    if not name:
        raise RuntimeError('BLOCKED_LUA54_LIBRARY_MISSING')
    lib = ctypes.CDLL(name)
    lib.luaL_newstate.restype = ctypes.c_void_p
    lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lib.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.luaL_loadstring.restype = ctypes.c_int
    lib.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
    lib.lua_pcallk.restype = ctypes.c_int
    lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    lib.lua_tolstring.restype = ctypes.c_char_p
    lib.lua_close.argtypes = [ctypes.c_void_p]
    state = lib.luaL_newstate()
    if not state:
        raise RuntimeError('Lua allocation failed')
    try:
        lib.luaL_openlibs(state)
        code = lib.luaL_loadstring(state, source.encode())
        if not code:
            code = lib.lua_pcallk(state, 0, 0, 0, 0, None)
        if code:
            raise AssertionError(lib.lua_tolstring(state, -1, None).decode())
    finally:
        lib.lua_close(state)
