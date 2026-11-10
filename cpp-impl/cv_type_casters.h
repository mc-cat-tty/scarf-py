#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>


namespace nanobind::detail {

template <> struct type_caster<cv::Size> {
    NB_TYPE_CASTER(cv::Size, const_name("tuple[int, int]"))

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
        value = cv::Size(v[0], v[1]);   // (width, height)
        return true;
    }

    static handle from_cpp(const cv::Size &s, rv_policy, cleanup_list *) noexcept {
        return make_tuple(s.width, s.height).release();
    }
};

using cvMatD = cv::Mat_<double>;
template <> struct type_caster<cvMatD> {
    NB_TYPE_CASTER(cvMatD, const_name("numpy.ndarray"))

    static handle from_cpp(const cvMatD &m, rv_policy policy, cleanup_list *cleanup) noexcept {
        if (!m.isContinuous()) {
            PyErr_SetString(PyExc_ValueError, "cv::Mat must be contiguous; use clone()");
            return {};
        }

        auto *heap = new cv::Mat(m);
        object owner = capsule(heap, [](void *p) noexcept { delete (cv::Mat *) p; });

        using Arr = ndarray<nanobind::numpy, double, nanobind::ndim<2>>;
        Arr arr((double *) heap->data,
                { (size_t) m.rows, (size_t) m.cols },
                owner);

        return nanobind::cast(arr, rv_policy::move).release();
    }
};

}  // namespace nanobind::detail