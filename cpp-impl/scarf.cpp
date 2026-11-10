#include <scarf.h>
#include <cv_type_casters.h>

#include <opencv2/core.hpp>
#include <nanobind/nanobind.h>

namespace nb = nanobind;

using namespace scarf;
using namespace nb::literals;

NB_MODULE(scarf, m) {
    nb::module_::import_("numpy");
    
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
        )
        .def("getSurface", &SCARF::getSurface);
        // .def("getList", &SCARF::getList)
        // .def("getAll", &SCARF::getAll)
        // .def("getN", &SCARF::getN)
        // .def("getScarfParams", &SCARF::getScarfParams)
}