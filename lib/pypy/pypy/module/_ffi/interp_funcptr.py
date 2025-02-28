from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, wrap_oserror, \
    operationerrfmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module._ffi.interp_ffitype import W_FFIType
#
from rpython.rtyper.lltypesystem import lltype, rffi
#
from rpython.rlib import jit
from rpython.rlib import libffi
from rpython.rlib.clibffi import get_libc_name, StackCheckError, LibFFIError
from rpython.rlib.rdynload import DLOpenError
from rpython.rlib.rarithmetic import r_uint
from rpython.rlib.objectmodel import we_are_translated
from pypy.module._ffi.type_converter import FromAppLevelConverter, ToAppLevelConverter
from pypy.module._rawffi.interp_rawffi import got_libffi_error

import os
if os.name == 'nt':
    def _getfunc(space, CDLL, w_name, w_argtypes, w_restype):
        argtypes_w, argtypes, w_restype, restype = unpack_argtypes(
            space, w_argtypes, w_restype)
        if space.isinstance_w(w_name, space.w_str):
            name = space.str_w(w_name)
            try:
                func = CDLL.cdll.getpointer(name, argtypes, restype,
                                            flags = CDLL.flags)
            except KeyError:
                raise operationerrfmt(
                    space.w_AttributeError,
                    "No symbol %s found in library %s", name, CDLL.name)
            except LibFFIError:
                raise got_libffi_error(space)

            return W_FuncPtr(func, argtypes_w, w_restype)
        elif space.isinstance_w(w_name, space.w_int):
            ordinal = space.int_w(w_name)
            try:
                func = CDLL.cdll.getpointer_by_ordinal(
                    ordinal, argtypes, restype,
                    flags = CDLL.flags)
            except KeyError:
                raise operationerrfmt(
                    space.w_AttributeError,
                    "No ordinal %d found in library %s", ordinal, CDLL.name)
            except LibFFIError:
                raise got_libffi_error(space)

            return W_FuncPtr(func, argtypes_w, w_restype)
        else:
            raise OperationError(space.w_TypeError, space.wrap(
                    'function name must be a string or integer'))
else:
    @unwrap_spec(name=str)
    def _getfunc(space, CDLL, w_name, w_argtypes, w_restype):
        name = space.str_w(w_name)
        argtypes_w, argtypes, w_restype, restype = unpack_argtypes(
            space, w_argtypes, w_restype)
        try:
            func = CDLL.cdll.getpointer(name, argtypes, restype,
                                        flags = CDLL.flags)
        except KeyError:
            raise operationerrfmt(
                space.w_AttributeError,
                "No symbol %s found in library %s", name, CDLL.name)
        except LibFFIError:
            raise got_libffi_error(space)

        return W_FuncPtr(func, argtypes_w, w_restype)

def unwrap_ffitype(space, w_argtype, allow_void=False):
    res = w_argtype.get_ffitype()
    if res is libffi.types.void and not allow_void:
        msg = 'void is not a valid argument type'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return res


# ========================================================================

class W_FuncPtr(W_Root):

    _immutable_fields_ = ['func', 'argtypes_w[*]', 'w_restype']

    def __init__(self, func, argtypes_w, w_restype):
        self.func = func
        self.argtypes_w = argtypes_w
        self.w_restype = w_restype
        self.to_free = []

    @jit.unroll_safe
    def build_argchain(self, space, args_w):
        expected = len(self.argtypes_w)
        given = len(args_w)
        if given != expected:
            arg = 'arguments'
            if len(self.argtypes_w) == 1:
                arg = 'argument'
            raise operationerrfmt(space.w_TypeError,
                                  '%s() takes exactly %d %s (%d given)',
                                  self.func.name, expected, arg, given)
        #
        argchain = libffi.ArgChain()
        argpusher = PushArgumentConverter(space, argchain, self)
        for i in range(expected):
            w_argtype = self.argtypes_w[i]
            w_arg = args_w[i]
            argpusher.unwrap_and_do(w_argtype, w_arg)
        return argchain

    def call(self, space, args_w):
        self = jit.promote(self)
        argchain = self.build_argchain(space, args_w)
        func_caller = CallFunctionConverter(space, self.func, argchain)
        try:
            return func_caller.do_and_wrap(self.w_restype)
        except StackCheckError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.message))
        #return self._do_call(space, argchain)

    def free_temp_buffers(self, space):
        for buf in self.to_free:
            if not we_are_translated():
                buf[0] = '\00' # invalidate the buffer, so that
                               # test_keepalive_temp_buffer can fail
            lltype.free(buf, flavor='raw')
        self.to_free = []

    def getaddr(self, space):
        """
        Return the physical address in memory of the function
        """
        return space.wrap(rffi.cast(rffi.LONG, self.func.funcsym))


class PushArgumentConverter(FromAppLevelConverter):
    """
    A converter used by W_FuncPtr to unwrap the app-level objects into
    low-level types and push them to the argchain.
    """

    def __init__(self, space, argchain, w_func):
        FromAppLevelConverter.__init__(self, space)
        self.argchain = argchain
        self.w_func = w_func

    def handle_signed(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_unsigned(self, w_ffitype, w_obj, uintval):
        self.argchain.arg(uintval)

    def handle_pointer(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_char(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_unichar(self, w_ffitype, w_obj, intval):
        self.argchain.arg(intval)

    def handle_longlong(self, w_ffitype, w_obj, longlongval):
        self.argchain.arg(longlongval)

    def handle_char_p(self, w_ffitype, w_obj, strval):
        buf = rffi.str2charp(strval)
        self.w_func.to_free.append(rffi.cast(rffi.VOIDP, buf))
        addr = rffi.cast(rffi.ULONG, buf)
        self.argchain.arg(addr)

    def handle_unichar_p(self, w_ffitype, w_obj, unicodeval):
        buf = rffi.unicode2wcharp(unicodeval)
        self.w_func.to_free.append(rffi.cast(rffi.VOIDP, buf))
        addr = rffi.cast(rffi.ULONG, buf)
        self.argchain.arg(addr)

    def handle_float(self, w_ffitype, w_obj, floatval):
        self.argchain.arg(floatval)

    def handle_singlefloat(self, w_ffitype, w_obj, singlefloatval):
        self.argchain.arg(singlefloatval)

    def handle_struct(self, w_ffitype, w_structinstance):
        # arg_raw directly takes value to put inside ll_args
        ptrval = w_structinstance.rawmem
        self.argchain.arg_raw(ptrval)

    def handle_struct_rawffi(self, w_ffitype, w_structinstance):
        # arg_raw directly takes value to put inside ll_args
        ptrval = w_structinstance.ll_buffer
        self.argchain.arg_raw(ptrval)


class CallFunctionConverter(ToAppLevelConverter):
    """
    A converter used by W_FuncPtr to call the function, expect the result of
    a correct low-level type and wrap it to the corresponding app-level type
    """

    def __init__(self, space, func, argchain):
        ToAppLevelConverter.__init__(self, space)
        self.func = func
        self.argchain = argchain

    def get_longlong(self, w_ffitype):
        return self.func.call(self.argchain, rffi.LONGLONG)

    def get_ulonglong(self, w_ffitype):
        return self.func.call(self.argchain, rffi.ULONGLONG)

    def get_signed(self, w_ffitype):
        # if the declared return type of the function is smaller than LONG,
        # the result buffer may contains garbage in its higher bits.  To get
        # the correct value, and to be sure to handle the signed/unsigned case
        # correctly, we need to cast the result to the correct type.  After
        # that, we cast it back to LONG, because this is what we want to pass
        # to space.wrap in order to get a nice applevel <int>.
        #
        restype = w_ffitype.get_ffitype()
        call = self.func.call
        if restype is libffi.types.slong:
            return call(self.argchain, rffi.LONG)
        elif restype is libffi.types.sint:
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.INT))
        elif restype is libffi.types.sshort:
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.SHORT))
        elif restype is libffi.types.schar:
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.SIGNEDCHAR))
        else:
            self.error(w_ffitype)

    def get_unsigned(self, w_ffitype):
        return self.func.call(self.argchain, rffi.ULONG)

    def get_unsigned_which_fits_into_a_signed(self, w_ffitype):
        # the same comment as get_signed apply
        restype = w_ffitype.get_ffitype()
        call = self.func.call
        if restype is libffi.types.uint:
            assert not libffi.IS_32_BIT
            # on 32bit machines, we should never get here, because it's a case
            # which has already been handled by get_unsigned above.
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.UINT))
        elif restype is libffi.types.ushort:
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.USHORT))
        elif restype is libffi.types.uchar:
            return rffi.cast(rffi.LONG, call(self.argchain, rffi.UCHAR))
        else:
            self.error(w_ffitype)


    def get_pointer(self, w_ffitype):
        ptrres = self.func.call(self.argchain, rffi.VOIDP)
        return rffi.cast(rffi.ULONG, ptrres)

    def get_char(self, w_ffitype):
        return self.func.call(self.argchain, rffi.UCHAR)

    def get_unichar(self, w_ffitype):
        return self.func.call(self.argchain, rffi.WCHAR_T)

    def get_float(self, w_ffitype):
        return self.func.call(self.argchain, rffi.DOUBLE)

    def get_singlefloat(self, w_ffitype):
        return self.func.call(self.argchain, rffi.FLOAT)

    def get_struct(self, w_ffitype, w_structdescr):
        addr = self.func.call(self.argchain, rffi.LONG, is_struct=True)
        return w_structdescr.fromaddress(self.space, addr)

    def get_struct_rawffi(self, w_ffitype, w_structdescr):
        uintval = self.func.call(self.argchain, rffi.ULONG, is_struct=True)
        return w_structdescr.fromaddress(self.space, uintval)

    def get_void(self, w_ffitype):
        return self.func.call(self.argchain, lltype.Void)


def unpack_argtypes(space, w_argtypes, w_restype):
    argtypes_w = [space.interp_w(W_FFIType, w_argtype)
                  for w_argtype in space.listview(w_argtypes)]
    argtypes = [unwrap_ffitype(space, w_argtype) for w_argtype in
                argtypes_w]
    w_restype = space.interp_w(W_FFIType, w_restype)
    restype = unwrap_ffitype(space, w_restype, allow_void=True)
    return argtypes_w, argtypes, w_restype, restype

@unwrap_spec(addr=r_uint, name=str, flags=int)
def descr_fromaddr(space, w_cls, addr, name, w_argtypes,
                    w_restype, flags=libffi.FUNCFLAG_CDECL):
    argtypes_w, argtypes, w_restype, restype = unpack_argtypes(space,
                                                               w_argtypes,
                                                               w_restype)
    addr = rffi.cast(rffi.VOIDP, addr)
    try:
        func = libffi.Func(name, argtypes, restype, addr, flags)
        return W_FuncPtr(func, argtypes_w, w_restype)
    except LibFFIError:
        raise got_libffi_error(space)


W_FuncPtr.typedef = TypeDef(
    '_ffi.FuncPtr',
    __call__ = interp2app(W_FuncPtr.call),
    getaddr = interp2app(W_FuncPtr.getaddr),
    free_temp_buffers = interp2app(W_FuncPtr.free_temp_buffers),
    fromaddr = interp2app(descr_fromaddr, as_classmethod=True)
    )



# ========================================================================

class W_CDLL(W_Root):
    def __init__(self, space, name, mode):
        self.flags = libffi.FUNCFLAG_CDECL
        self.space = space
        if name is None:
            self.name = "<None>"
        else:
            self.name = name
        try:
            self.cdll = libffi.CDLL(name, mode)
        except DLOpenError, e:
            raise operationerrfmt(space.w_OSError, '%s: %s', self.name,
                                  e.msg or 'unspecified error')

    def getfunc(self, space, w_name, w_argtypes, w_restype):
        return _getfunc(space, self, w_name, w_argtypes, w_restype)

    @unwrap_spec(name=str)
    def getaddressindll(self, space, name):
        try:
            address_as_uint = rffi.cast(lltype.Unsigned,
                                        self.cdll.getaddressindll(name))
        except KeyError:
            raise operationerrfmt(
                space.w_ValueError,
                "No symbol %s found in library %s", name, self.name)
        return space.wrap(address_as_uint)

@unwrap_spec(name='str_or_None', mode=int)
def descr_new_cdll(space, w_type, name, mode=-1):
    return space.wrap(W_CDLL(space, name, mode))


W_CDLL.typedef = TypeDef(
    '_ffi.CDLL',
    __new__     = interp2app(descr_new_cdll),
    getfunc     = interp2app(W_CDLL.getfunc),
    getaddressindll = interp2app(W_CDLL.getaddressindll),
    )

class W_WinDLL(W_CDLL):
    def __init__(self, space, name, mode):
        W_CDLL.__init__(self, space, name, mode)
        self.flags = libffi.FUNCFLAG_STDCALL

@unwrap_spec(name='str_or_None', mode=int)
def descr_new_windll(space, w_type, name, mode=-1):
    return space.wrap(W_WinDLL(space, name, mode))


W_WinDLL.typedef = TypeDef(
    '_ffi.WinDLL',
    __new__     = interp2app(descr_new_windll),
    getfunc     = interp2app(W_WinDLL.getfunc),
    getaddressindll = interp2app(W_WinDLL.getaddressindll),
    )

# ========================================================================

def get_libc(space):
    try:
        return space.wrap(W_CDLL(space, get_libc_name(), -1))
    except OSError, e:
        raise wrap_oserror(space, e)

