import os

from rpython.jit.metainterp.jitexc import JitException
from rpython.jit.metainterp.optimizeopt.optimizer import Optimization, MODE_ARRAY, LEVEL_KNOWNCLASS
from rpython.jit.metainterp.history import ConstInt, Const
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.rlib.objectmodel import we_are_translated


class CachedField(object):
    def __init__(self):
        # Cache information for a field descr, or for an (array descr, index)
        # pair.  It can be in one of two states:
        #
        #   1. 'cached_fields' is a dict mapping OptValues of structs
        #      to OptValues of fields.  All fields on-heap are
        #      synchronized with the values stored in the cache.
        #
        #   2. we just did one setfield, which is delayed (and thus
        #      not synchronized).  'lazy_setfield' is the delayed
        #      ResOperation.  In this state, 'cached_fields' contains
        #      out-of-date information.  More precisely, the field
        #      value pending in the ResOperation is *not* visible in
        #      'cached_fields'.
        #
        self._cached_fields = {}
        self._cached_fields_getfield_op = {}
        self._lazy_setfield = None
        self._lazy_setfield_registered = False

    def do_setfield(self, optheap, op):
        # Update the state with the SETFIELD_GC/SETARRAYITEM_GC operation 'op'.
        structvalue = optheap.getvalue(op.getarg(0))
        fieldvalue  = optheap.getvalue(op.getarglist()[-1])
        if self.possible_aliasing(optheap, structvalue):
            self.force_lazy_setfield(optheap)
            assert not self.possible_aliasing(optheap, structvalue)
        cached_fieldvalue = self._cached_fields.get(structvalue, None)

        # Hack to ensure constants are imported from the preamble
        if cached_fieldvalue and fieldvalue.is_constant(): 
            optheap.optimizer.ensure_imported(cached_fieldvalue)
            cached_fieldvalue = self._cached_fields.get(structvalue, None)

        if not fieldvalue.same_value(cached_fieldvalue):
            # common case: store the 'op' as lazy_setfield, and register
            # myself in the optheap's _lazy_setfields_and_arrayitems list
            self._lazy_setfield = op
            if not self._lazy_setfield_registered:
                optheap._lazy_setfields_and_arrayitems.append(self)
                self._lazy_setfield_registered = True
            
        else:
            # this is the case where the pending setfield ends up
            # storing precisely the value that is already there,
            # as proved by 'cached_fields'.  In this case, we don't
            # need any _lazy_setfield: the heap value is already right.
            # Note that this may reset to None a non-None lazy_setfield,
            # cancelling its previous effects with no side effect.
            self._lazy_setfield = None

    def possible_aliasing(self, optheap, structvalue):
        # If lazy_setfield is set and contains a setfield on a different
        # structvalue, then we are annoyed, because it may point to either
        # the same or a different structure at runtime.
        return (self._lazy_setfield is not None
                and (optheap.getvalue(self._lazy_setfield.getarg(0))
                     is not structvalue))

    def getfield_from_cache(self, optheap, structvalue):
        # Returns the up-to-date field's value, or None if not cached.
        if self.possible_aliasing(optheap, structvalue):
            self.force_lazy_setfield(optheap)
        if self._lazy_setfield is not None:
            op = self._lazy_setfield
            assert optheap.getvalue(op.getarg(0)) is structvalue
            return optheap.getvalue(op.getarglist()[-1])
        else:
            return self._cached_fields.get(structvalue, None)

    def remember_field_value(self, structvalue, fieldvalue, getfield_op=None):
        assert self._lazy_setfield is None
        self._cached_fields[structvalue] = fieldvalue
        self._cached_fields_getfield_op[structvalue] = getfield_op

    def force_lazy_setfield(self, optheap, can_cache=True):
        op = self._lazy_setfield
        if op is not None:
            # This is the way _lazy_setfield is usually reset to None.
            # Now we clear _cached_fields, because actually doing the
            # setfield might impact any of the stored result (because of
            # possible aliasing).
            self.clear()
            self._lazy_setfield = None
            optheap.next_optimization.propagate_forward(op)
            if not can_cache:
                return
            # Once it is done, we can put at least one piece of information
            # back in the cache: the value of this particular structure's
            # field.
            structvalue = optheap.getvalue(op.getarg(0))
            fieldvalue  = optheap.getvalue(op.getarglist()[-1])
            self.remember_field_value(structvalue, fieldvalue, op)
        elif not can_cache:
            self.clear()

    def clear(self):
        self._cached_fields.clear()
        self._cached_fields_getfield_op.clear()

    def turned_constant(self, newvalue, value):
        if newvalue not in self._cached_fields and value in self._cached_fields:
            self._cached_fields[newvalue] = self._cached_fields[value]
            op = self._cached_fields_getfield_op[value].clone()
            constbox = value.box
            assert isinstance(constbox, Const)
            op.setarg(0, constbox)
            self._cached_fields_getfield_op[newvalue] = op
        for structvalue in self._cached_fields.keys():
            if self._cached_fields[structvalue] is value:
                self._cached_fields[structvalue] = newvalue

    def produce_potential_short_preamble_ops(self, optimizer, shortboxes, descr):
        if self._lazy_setfield is not None:
            return
        for structvalue in self._cached_fields_getfield_op.keys():
            op = self._cached_fields_getfield_op[structvalue]
            if not op:
                continue
            value = optimizer.getvalue(op.getarg(0))
            if value in optimizer.opaque_pointers:
                if value.level < LEVEL_KNOWNCLASS:
                    continue
                if op.getopnum() != rop.SETFIELD_GC and op.getopnum() != rop.GETFIELD_GC:
                    continue
            if structvalue in self._cached_fields:
                if op.getopnum() == rop.SETFIELD_GC:
                    result = op.getarg(1)
                    if isinstance(result, Const):
                        newresult = result.clonebox()
                        optimizer.make_constant(newresult, result)
                        result = newresult
                    getop = ResOperation(rop.GETFIELD_GC, [op.getarg(0)],
                                         result, op.getdescr())
                    shortboxes.add_potential(getop, synthetic=True)
                if op.getopnum() == rop.SETARRAYITEM_GC:
                    result = op.getarg(2)
                    if isinstance(result, Const):
                        newresult = result.clonebox()
                        optimizer.make_constant(newresult, result)
                        result = newresult
                    getop = ResOperation(rop.GETARRAYITEM_GC, [op.getarg(0), op.getarg(1)],
                                         result, op.getdescr())
                    shortboxes.add_potential(getop, synthetic=True)
                elif op.result is not None:
                    shortboxes.add_potential(op)

class BogusPureField(JitException):
    pass


class OptHeap(Optimization):
    """Cache repeated heap accesses"""

    def __init__(self):
        # cached fields:  {descr: CachedField}
        self.cached_fields = {}
        # cached array items:  {array descr: {index: CachedField}}
        self.cached_arrayitems = {}
        #
        self._lazy_setfields_and_arrayitems = []
        self._remove_guard_not_invalidated = False
        self._seen_guard_not_invalidated = False
        self.postponed_op = None

    def force_at_end_of_preamble(self):
        self.force_all_lazy_setfields_and_arrayitems()

    def flush(self):
        self.force_all_lazy_setfields_and_arrayitems()
        if self.postponed_op:
            postponed_op = self.postponed_op
            self.postponed_op = None
            self.next_optimization.propagate_forward(postponed_op)

    def new(self):
        return OptHeap()

    def produce_potential_short_preamble_ops(self, sb):
        descrkeys = self.cached_fields.keys()
        if not we_are_translated():
            # XXX Pure operation of boxes that are cached in several places will
            #     only be removed from the peeled loop when red from the first
            #     place discovered here. This is far from ideal, as it makes
            #     the effectiveness of our optimization a bit random. It should
            #     howevere always generate correct results. For tests we dont
            #     want this randomness.
            descrkeys.sort(key=str, reverse=True)
        for descr in descrkeys:
            d = self.cached_fields[descr]
            d.produce_potential_short_preamble_ops(self.optimizer, sb, descr)

        for descr, submap in self.cached_arrayitems.items():
            for index, d in submap.items():
                d.produce_potential_short_preamble_ops(self.optimizer, sb, descr)

    def clean_caches(self):
        del self._lazy_setfields_and_arrayitems[:]
        self.cached_fields.clear()
        self.cached_arrayitems.clear()

    def field_cache(self, descr):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            cf = self.cached_fields[descr] = CachedField()
        return cf

    def arrayitem_cache(self, descr, index):
        try:
            submap = self.cached_arrayitems[descr]
        except KeyError:
            submap = self.cached_arrayitems[descr] = {}
        try:
            cf = submap[index]
        except KeyError:
            cf = submap[index] = CachedField()
        return cf

    def emit_operation(self, op):
        self.emitting_operation(op)
        if self.postponed_op:
            postponed_op = self.postponed_op
            self.postponed_op = None
            self.next_optimization.propagate_forward(postponed_op)
        if (op.is_comparison() or op.getopnum() == rop.CALL_MAY_FORCE
            or op.is_ovf()):
            self.postponed_op = op
        else:
            Optimization.emit_operation(self, op)

    def emitting_operation(self, op):
        if op.has_no_side_effect():
            return
        if op.is_ovf():
            return
        if op.is_guard():
            self.optimizer.pendingfields = (
                self.force_lazy_setfields_and_arrayitems_for_guard())
            return
        opnum = op.getopnum()
        if (opnum == rop.SETFIELD_GC or          # handled specially
            opnum == rop.SETFIELD_RAW or         # no effect on GC struct/array
            opnum == rop.SETARRAYITEM_GC or      # handled specially
            opnum == rop.SETARRAYITEM_RAW or     # no effect on GC struct
            opnum == rop.SETINTERIORFIELD_RAW or # no effect on GC struct
            opnum == rop.RAW_STORE or            # no effect on GC struct
            opnum == rop.STRSETITEM or           # no effect on GC struct/array
            opnum == rop.UNICODESETITEM or       # no effect on GC struct/array
            opnum == rop.DEBUG_MERGE_POINT or    # no effect whatsoever
            opnum == rop.COPYSTRCONTENT or       # no effect on GC struct/array
            opnum == rop.COPYUNICODECONTENT):    # no effect on GC struct/array
            return
        if (opnum == rop.CALL or
            opnum == rop.CALL_PURE or
            opnum == rop.CALL_MAY_FORCE or
            opnum == rop.CALL_RELEASE_GIL or
            opnum == rop.CALL_ASSEMBLER):
            if opnum == rop.CALL_ASSEMBLER:
                self._seen_guard_not_invalidated = False
            else:
                effectinfo = op.getdescr().get_extra_info()
                if effectinfo.check_can_invalidate():
                    self._seen_guard_not_invalidated = False
                if not effectinfo.has_random_effects():
                    self.force_from_effectinfo(effectinfo)
                    return
        self.force_all_lazy_setfields_and_arrayitems()
        self.clean_caches()

    def force_from_effectinfo(self, effectinfo):
        # XXX we can get the wrong complexity here, if the lists
        # XXX stored on effectinfo are large
        for fielddescr in effectinfo.readonly_descrs_fields:
            self.force_lazy_setfield(fielddescr)
        for arraydescr in effectinfo.readonly_descrs_arrays:
            self.force_lazy_setarrayitem(arraydescr)
        for fielddescr in effectinfo.write_descrs_fields:
            self.force_lazy_setfield(fielddescr, can_cache=False)
        for arraydescr in effectinfo.write_descrs_arrays:
            self.force_lazy_setarrayitem(arraydescr, can_cache=False)
        if effectinfo.check_forces_virtual_or_virtualizable():
            vrefinfo = self.optimizer.metainterp_sd.virtualref_info
            self.force_lazy_setfield(vrefinfo.descr_forced)
            # ^^^ we only need to force this field; the other fields
            # of virtualref_info and virtualizable_info are not gcptrs.

    def turned_constant(self, value):
        assert value.is_constant()
        newvalue = self.getvalue(value.box)
        if value is not newvalue:
            for cf in self.cached_fields.itervalues():
                cf.turned_constant(newvalue, value)
            for submap in self.cached_arrayitems.itervalues():
                for cf in submap.itervalues():
                    cf.turned_constant(newvalue, value)

    def force_lazy_setfield(self, descr, can_cache=True):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            return
        cf.force_lazy_setfield(self, can_cache)

    def force_lazy_setarrayitem(self, arraydescr, indexvalue=None, can_cache=True):
        try:
            submap = self.cached_arrayitems[arraydescr]
        except KeyError:
            return
        for idx, cf in submap.iteritems():
            if indexvalue is None or indexvalue.intbound.contains(idx):
                cf.force_lazy_setfield(self, can_cache)

    def _assert_valid_cf(self, cf):
        # check that 'cf' is in cached_fields or cached_arrayitems
        if not we_are_translated():
            if cf not in self.cached_fields.values():
                for submap in self.cached_arrayitems.values():
                    if cf in submap.values():
                        break
                else:
                    assert 0, "'cf' not in cached_fields/cached_arrayitems"

    def force_all_lazy_setfields_and_arrayitems(self):
        for cf in self._lazy_setfields_and_arrayitems:
            self._assert_valid_cf(cf)
            cf.force_lazy_setfield(self)

    def force_lazy_setfields_and_arrayitems_for_guard(self):
        pendingfields = []
        for cf in self._lazy_setfields_and_arrayitems:
            self._assert_valid_cf(cf)
            op = cf._lazy_setfield
            if op is None:
                continue
            # the only really interesting case that we need to handle in the
            # guards' resume data is that of a virtual object that is stored
            # into a field of a non-virtual object.  Here, 'op' in either
            # SETFIELD_GC or SETARRAYITEM_GC.
            value = self.getvalue(op.getarg(0))
            assert not value.is_virtual()      # it must be a non-virtual
            fieldvalue = self.getvalue(op.getarglist()[-1])
            if fieldvalue.is_virtual():
                # this is the case that we leave to resume.py
                opnum = op.getopnum()
                if opnum == rop.SETFIELD_GC:
                    itemindex = -1
                elif opnum == rop.SETARRAYITEM_GC:
                    indexvalue = self.getvalue(op.getarg(1))
                    assert indexvalue.is_constant()
                    itemindex = indexvalue.box.getint()
                    assert itemindex >= 0
                else:
                    assert 0
                pendingfields.append((op.getdescr(), value.box,
                                      fieldvalue.get_key_box(), itemindex))
            else:
                cf.force_lazy_setfield(self)
        return pendingfields

    def optimize_GETFIELD_GC(self, op):
        structvalue = self.getvalue(op.getarg(0))
        cf = self.field_cache(op.getdescr())
        fieldvalue = cf.getfield_from_cache(self, structvalue)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        # default case: produce the operation
        structvalue.ensure_nonnull()
        self.emit_operation(op)
        # then remember the result of reading the field
        fieldvalue = self.getvalue(op.result)
        cf.remember_field_value(structvalue, fieldvalue, op)

    def optimize_GETFIELD_GC_PURE(self, op):
        structvalue = self.getvalue(op.getarg(0))
        cf = self.field_cache(op.getdescr())
        fieldvalue = cf.getfield_from_cache(self, structvalue)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        # default case: produce the operation
        structvalue.ensure_nonnull()
        self.emit_operation(op)

    def optimize_SETFIELD_GC(self, op):
        if self.has_pure_result(rop.GETFIELD_GC_PURE, [op.getarg(0)],
                                op.getdescr()):
            os.write(2, '[bogus _immutable_field_ declaration: %s]\n' %
                     (op.getdescr().repr_of_descr()))
            raise BogusPureField
        #
        cf = self.field_cache(op.getdescr())
        cf.do_setfield(self, op)
        

    def optimize_GETARRAYITEM_GC(self, op):
        arrayvalue = self.getvalue(op.getarg(0))
        indexvalue = self.getvalue(op.getarg(1))
        cf = None
        if indexvalue.is_constant():
            arrayvalue.make_len_gt(MODE_ARRAY, op.getdescr(), indexvalue.box.getint())
            # use the cache on (arraydescr, index), which is a constant
            cf = self.arrayitem_cache(op.getdescr(), indexvalue.box.getint())
            fieldvalue = cf.getfield_from_cache(self, arrayvalue)
            if fieldvalue is not None:
                self.make_equal_to(op.result, fieldvalue)
                return
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(), indexvalue=indexvalue)
        # default case: produce the operation
        arrayvalue.ensure_nonnull()
        self.emit_operation(op)
        # the remember the result of reading the array item
        if cf is not None:
            fieldvalue = self.getvalue(op.result)
            cf.remember_field_value(arrayvalue, fieldvalue, op)

    def optimize_GETARRAYITEM_GC_PURE(self, op):
        arrayvalue = self.getvalue(op.getarg(0))
        indexvalue = self.getvalue(op.getarg(1))
        cf = None
        if indexvalue.is_constant():
            arrayvalue.make_len_gt(MODE_ARRAY, op.getdescr(), indexvalue.box.getint())
            # use the cache on (arraydescr, index), which is a constant
            cf = self.arrayitem_cache(op.getdescr(), indexvalue.box.getint())
            fieldvalue = cf.getfield_from_cache(self, arrayvalue)
            if fieldvalue is not None:
                self.make_equal_to(op.result, fieldvalue)
                return
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(), indexvalue=indexvalue)
        # default case: produce the operation
        arrayvalue.ensure_nonnull()
        self.emit_operation(op)

    def optimize_SETARRAYITEM_GC(self, op):
        if self.has_pure_result(rop.GETARRAYITEM_GC_PURE, [op.getarg(0),
                                                           op.getarg(1)],
                                op.getdescr()):
            os.write(2, '[bogus immutable array declaration: %s]\n' %
                     (op.getdescr().repr_of_descr()))
            raise BogusPureField
        #
        indexvalue = self.getvalue(op.getarg(1))
        if indexvalue.is_constant():
            arrayvalue = self.getvalue(op.getarg(0))
            arrayvalue.make_len_gt(MODE_ARRAY, op.getdescr(), indexvalue.box.getint())
            # use the cache on (arraydescr, index), which is a constant
            cf = self.arrayitem_cache(op.getdescr(), indexvalue.box.getint())
            cf.do_setfield(self, op)
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(), indexvalue=indexvalue, can_cache=False)
            # and then emit the operation
            self.emit_operation(op)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # Pattern: QUASIIMMUT_FIELD(s, descr=QuasiImmutDescr)
        #          x = GETFIELD_GC(s, descr='inst_x')
        # If 's' is a constant (after optimizations), then we make 's.inst_x'
        # a constant too, and we rely on the rest of the optimizations to
        # constant-fold the following getfield_gc.
        structvalue = self.getvalue(op.getarg(0))
        if not structvalue.is_constant():
            self._remove_guard_not_invalidated = True
            return    # not a constant at all; ignore QUASIIMMUT_FIELD
        #
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        qmutdescr = op.getdescr()
        assert isinstance(qmutdescr, QuasiImmutDescr)
        # check that the value is still correct; it could have changed
        # already between the tracing and now.  In this case, we are
        # simply ignoring the QUASIIMMUT_FIELD hint and compiling it
        # as a regular getfield.
        if not qmutdescr.is_still_valid_for(structvalue.get_key_box()):
            self._remove_guard_not_invalidated = True
            return
        # record as an out-of-line guard
        if self.optimizer.quasi_immutable_deps is None:
            self.optimizer.quasi_immutable_deps = {}
        self.optimizer.quasi_immutable_deps[qmutdescr.qmut] = None
        # perform the replacement in the list of operations
        fieldvalue = self.getvalue(qmutdescr.constantfieldbox)
        cf = self.field_cache(qmutdescr.fielddescr)
        cf.force_lazy_setfield(self)
        cf.remember_field_value(structvalue, fieldvalue)
        self._remove_guard_not_invalidated = False

    def optimize_GUARD_NOT_INVALIDATED(self, op):
        if self._remove_guard_not_invalidated:
            return
        if self._seen_guard_not_invalidated:
            return
        self._seen_guard_not_invalidated = True
        self.emit_operation(op)


dispatch_opt = make_dispatcher_method(OptHeap, 'optimize_',
        default=OptHeap.emit_operation)
OptHeap.propagate_forward = dispatch_opt
