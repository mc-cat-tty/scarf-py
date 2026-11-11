/*
* File taken from: https://github.com/robotology/event-driven/tree/main/ev2/event-driven/algs | commit caea54e79e1be11ded762ff4f7c78b1f0a58772e
*/


// Reference driver for the ORIGINAL (OpenCV-based) SCARF implementation in
// original_impl.h. It is used by test_equivalence.py to compare the original
// against the Eigen/nanobind port. Built by tests/CMakeLists.txt (standalone,
// not part of the wheel build).
//
// Usage:
//   ref_scarf <events.bin> <out.bin> <width> <height> <every_k> size <rf_size>          <alpha> <C>
//   ref_scarf <events.bin> <out.bin> <width> <height> <every_k> res  <rf_w> <rf_h>      <alpha> <C>
//
//   "size" calls ev::SCARF::initialise(cv::Size(width, height), rf_size, alpha, C)
//   "res"  calls ev::SCARF::initialise(cv::Size(width, height), cv::Size(rf_w, rf_h), alpha, C)
//
// Input  <events.bin>: little-endian int32 triplets (u, v, p), i.e. a C-contiguous
//                      numpy array of shape (n, 3), dtype '<i4'. u = column (x),
//                      v = row (y), p = polarity.
// Output <out.bin>   : the surface dumped at each checkpoint, concatenated; every
//                      checkpoint is height*width native float64 values in row-major
//                      order (numpy shape (height, width), C order). Checkpoints are
//                      taken after every <every_k> events (if every_k > 0) and after
//                      the last event (unless that coincides with the previous one).
//                      With n == 0 events a single (all-zero) checkpoint is written.
// stdout             : one line per checkpoint with the number of events processed.

#include "original_impl.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static int usage()
{
    std::cerr << "usage: ref_scarf <events.bin> <out.bin> <width> <height> <every_k> "
                 "(size <rf_size> | res <rf_w> <rf_h>) <alpha> <C>\n";
    return 2;
}

static void dump(std::ofstream &out, const cv::Mat_<double> &img)
{
    for (int r = 0; r < img.rows; r++)
        out.write(reinterpret_cast<const char *>(img.ptr<double>(r)), sizeof(double) * img.cols);
}

int main(int argc, char **argv)
{
    if (argc < 9) return usage();
    const std::string events_path = argv[1], out_path = argv[2];
    const int width = std::atoi(argv[3]), height = std::atoi(argv[4]);
    const long every_k = std::atol(argv[5]);
    const std::string mode = argv[6];

    ev::SCARF scarf;
    if (mode == "size" && argc == 10) {
        scarf.initialise(cv::Size(width, height), std::atoi(argv[7]), std::atof(argv[8]), std::atof(argv[9]));
    } else if (mode == "res" && argc == 11) {
        scarf.initialise(cv::Size(width, height), cv::Size(std::atoi(argv[7]), std::atoi(argv[8])),
                         std::atof(argv[9]), std::atof(argv[10]));
    } else {
        return usage();
    }

    std::ifstream in(events_path, std::ios::binary | std::ios::ate);
    if (!in) { std::cerr << "cannot open " << events_path << "\n"; return 1; }
    const std::streamoff bytes = in.tellg();
    if (bytes % (3 * sizeof(int32_t))) { std::cerr << "events file size not a multiple of 12\n"; return 1; }
    std::vector<int32_t> ev(bytes / sizeof(int32_t), 0);
    in.seekg(0);
    in.read(reinterpret_cast<char *>(ev.data()), bytes);

    std::ofstream out(out_path, std::ios::binary);
    if (!out) { std::cerr << "cannot open " << out_path << "\n"; return 1; }

    const long n = static_cast<long>(ev.size() / 3);
    long last_dump = -1;
    for (long i = 0; i < n; i++) {
        scarf.update(ev[3 * i], ev[3 * i + 1], ev[3 * i + 2]);
        if (every_k > 0 && (i + 1) % every_k == 0) {
            dump(out, scarf.getSurface());
            last_dump = i + 1;
            std::cout << last_dump << "\n";
        }
    }
    if (last_dump != n) {
        dump(out, scarf.getSurface());
        std::cout << n << "\n";
    }
    return out.good() ? 0 : 1;
}
