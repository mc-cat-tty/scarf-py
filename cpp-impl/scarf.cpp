#include <scarf.h>
#include <type_casters.h>

#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/eigen/dense.h>

namespace nb = nanobind;

using namespace scarf;
using namespace nb::literals;

NB_MODULE(scarf, m) {
    nb::module_::import_("numpy");

    nb::class_<SCARF>(m, "SCARF")
        .def(nb::init<>())
        .def(
            "initialise", nb::overload_cast<scarf::Size, int, double, double>(&SCARF::initialise),
            "img_res"_a, "rf_size"_a, "alpha"_a = 1.0, "C"_a=0.3, "Initialize from receptive field size"
        )
        .def(
            "initialise", nb::overload_cast<scarf::Size, scarf::Size, double, double>(&SCARF::initialise),
            "img_res"_a, "rf_res"_a, "alpha"_a = 1.0, "C"_a=0.3, "Initialize from receptive field resolution"
        )
        .def(
            "update", &SCARF::update, "u"_a, "v"_a, "p"_a,
            "Update the surface with an incoming event: <u, v, polarity>"
        )
        .def(
            "getSurface", &SCARF::getSurface, nb::rv_policy::reference_internal,
            "Get a reference the SCARF surface as a 2D matrix"
        )
        .def(
            "getList", &SCARF::getList, "u"_a, "v"_a,
            "Get a list of active events, in <x, y> format, stored in the receptive at coordinates <u, v>"
        )
        .def(
            "getAll", &SCARF::getAll, "u"_a, "v"_a,
            "Get a list of all events, in <x, y> format, stored in the receptive at coordinates <u, v>"
        )
        .def(
            "getN", &SCARF::getN, "Get receptive field's circular buffer capacity (max num of elements)"
        )
        .def(
            "getScarfParams", &SCARF::getScarfParams,
            "Get SCARF parameters as <count, dims, N, border_shift>:\n"
            "\tcount        : Resolution of SCARF blocks\n"
            "\tdims         : Size of receptive field\n"
            "\tN            : Size of ring buffer in each SCARF block\n"
            "\tborder_shift : (HARD CORDED) pixel values for shift size to match origin of image and origin of scarf"
        );
}