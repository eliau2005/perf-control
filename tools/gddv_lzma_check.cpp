// Decompress a GDDV file's payload exactly as thermald does (thd_gddv.cpp handle_compressed_gddv),
// using thermald's own thd_lzma_dec.cpp + LzmaDec.c. Build (after configuring thermal_daemon):
//   g++ -std=c++17 -I$TD -I$TD/src -o gddv_lzma_check tools/gddv_lzma_check.cpp $TD/src/thd_lzma_dec.cpp $TD/src/LzmaDec.c
// Exit 0 = thermald will accept the payload size and decode it.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cstdint>
#include "thd_lzma_dec.h"
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb"); if (!f) return 2;
    std::vector<unsigned char> buf(8192); size_t n = fread(buf.data(), 1, buf.size(), f); fclose(f);
    uint16_t hsize = *(uint16_t*)(buf.data() + 2);
    size_t destlen = 0;
    int r = lzma_decompress(nullptr, &destlen, buf.data() + hsize, n - hsize);
    printf("size query rc=%d destlen=%zu\n", r, destlen);
    if (r) return 1;
    std::vector<unsigned char> out(destlen);
    r = lzma_decompress(out.data(), &destlen, buf.data() + hsize, n - hsize);
    printf("decode rc=%d destlen=%zu first bytes %02x%02x last key tail: %.*s\n", r, destlen, out[0], out[1], 0, "");
    return r;
}
