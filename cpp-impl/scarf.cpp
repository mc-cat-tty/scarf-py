#include <scarf.h>
#include <nanobind/nanobind.h>
#include <opencv2/core.hpp>

namespace nb = nanobind;

namespace nanobind::detail {

template <> struct type_caster<cv::Size> {
    NB_TYPE_CASTER(cv::Size, const_name("tuple[int, int]"))

    bool from_python(handle src, uint8_t flags, cleanup_list *cleanup) noexcept {
        bool isListOrTuple = isinstance<nb::tuple>(src) || isinstance<nb::list>(src);
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

} // namespace nanobind::detail

using namespace scarf;
using namespace nb::literals;

NB_MODULE(scarf, m) {
    nb::class_<SCARF>(m, "SCARF")
        .def(nb::init<>())
        .def(
            "initialise", nb::overload_cast<cv::Size, int, double, double>(&SCARF::initialise),
            "img_res"_a, "rf_size"_a, "alpha"_a = 1.0, "C"_a=0.3, "Initialize from receptive field size"
        )
        .def(
            "initialise", nb::overload_cast<cv::Size, cv::Size, double, double>(&SCARF::initialise),
            "img_res"_a, "rf_res"_a, "alpha"_a = 1.0, "C"_a=0.3, "Initialize from receptive field resolution"
        )
        .def(
            "update", &SCARF::update,
            "u"_a, "v"_a, "p"_a, "Update the surface with an incoming event: <u, v, polarity>"
        );
        // .def("getSurface", &SCARF::getSurface)
        // .def("getList", &SCARF::getList)
        // .def("getAll", &SCARF::getAll)
        // .def("getN", &SCARF::getN)
        // .def("getScarfParams", &SCARF::getScarfParams)
}