#pragma once

#include <scarf.h>
#include <nanobind/nanobind.h>

namespace nanobind::detail {
    template <> struct type_caster<scarf::Size> {
    NB_TYPE_CASTER(scarf::Size, const_name("tuple[int, int]"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept {
        bool isListOrTuple = isinstance<nanobind::tuple>(src) || isinstance<nanobind::list>(src);
        if (!isListOrTuple || PySequence_Size(src.ptr()) != 2)
            return false;

        int v[2];
        for (int i = 0; i < 2; ++i) {
            object item = steal(PySequence_GetItem(src.ptr(), i));
            if (!item.is_valid())
                return false;

            make_caster<int> c;
            if (!c.from_python(item, flags, cleanup))
                return false;
            v[i] = c.operator int &();
        }
        value = scarf::Size{v[0], v[1]};   // (width, height)
        return true;
    }

    static handle from_cpp(const scarf::Size &s, rv_policy, cleanup_list *) noexcept {
        return make_tuple(s.width, s.height).release();
    }
};
}