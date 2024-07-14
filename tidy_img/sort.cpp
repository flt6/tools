#include <iostream>
#include <fstream>
#include <filesystem>
#include <regex>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <iomanip>
#include <array>

namespace fs = std::filesystem;

// 手动实现SHA-256哈希函数
std::array<uint32_t, 8> sha256(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) return {};

    static const uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    auto rotr = [](uint32_t x, uint32_t n) {
        return (x >> n) | (x << (32 - n));
    };

    auto ch = [](uint32_t x, uint32_t y, uint32_t z) {
        return (x & y) ^ (~x & z);
    };

    auto maj = [](uint32_t x, uint32_t y, uint32_t z) {
        return (x & y) ^ (x & z) ^ (y & z);
    };

    auto bsig0 = [&rotr](uint32_t x) {
        return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
    };

    auto bsig1 = [&rotr](uint32_t x) {
        return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
    };

    auto ssig0 = [&rotr](uint32_t x) {
        return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
    };

    auto ssig1 = [&rotr](uint32_t x) {
        return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
    };

    std::array<uint32_t, 8> h = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    size_t original_size = data.size();
    data.push_back(0x80);
    while ((data.size() % 64) != 56) {
        data.push_back(0x00);
    }

    uint64_t bit_len = original_size * 8;
    for (int i = 7; i >= 0; --i) {
        data.push_back(bit_len >> (i * 8));
    }

    for (size_t chunk = 0; chunk < data.size() / 64; ++chunk) {
        uint32_t w[64];
        for (size_t i = 0; i < 16; ++i) {
            w[i] = (data[chunk * 64 + i * 4 + 0] << 24) |
                   (data[chunk * 64 + i * 4 + 1] << 16) |
                   (data[chunk * 64 + i * 4 + 2] << 8) |
                   (data[chunk * 64 + i * 4 + 3] << 0);
        }

        for (size_t i = 16; i < 64; ++i) {
            w[i] = ssig1(w[i - 2]) + w[i - 7] + ssig0(w[i - 15]) + w[i - 16];
        }

        uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
        uint32_t e = h[4], f = h[5], g = h[6], h_val = h[7];

        for (size_t i = 0; i < 64; ++i) {
            uint32_t temp1 = h_val + bsig1(e) + ch(e, f, g) + k[i] + w[i];
            uint32_t temp2 = bsig0(a) + maj(a, b, c);
            h_val = g;
            g = f;
            f = e;
            e = d + temp1;
            d = c;
            c = b;
            b = a;
            a = temp1 + temp2;
        }

        h[0] += a;
        h[1] += b;
        h[2] += c;
        h[3] += d;
        h[4] += e;
        h[5] += f;
        h[6] += g;
        h[7] += h_val;
    }

    return h;
}

std::string to_hex_string(const std::array<uint32_t, 8>& hash) {
    std::ostringstream oss;
    for (uint32_t part : hash) {
        oss << std::hex << std::setw(8) << std::setfill('0') << part;
    }
    return oss.str();
}

void process_files(const fs::path& root) {
    std::vector<fs::path> sameFiles;
    std::regex pattern(R"((IMG|VID)_(\d{4})(\d{2})(\d{2})_(\d{6})(_.+)?\.(jpg|mp4))");
    std::regex yearCheck("\\/?20\\d{2}\\/");

    for (const auto& p : fs::recursive_directory_iterator(root)) {
        if (!p.is_regular_file()) continue;

        std::smatch match;
        std::string filename = p.path().filename().string();
        if (!std::regex_search(filename, match, pattern)) continue;

        std::string absPath = p.path().string();
        std::cout<<absPath<<std::endl;
        std::smatch matchtmp;
        std::regex_search(absPath, matchtmp,yearCheck);
        if (!matchtmp.empty()) continue;
        std::cout<<matchtmp[0].length()<<std::endl;

        std::cout << match[2] << std::endl;
        fs::path target_dir = root / match[2].str();
        fs::create_directories(target_dir);
        fs::path target = target_dir / p.path().filename();

        if (fs::exists(target)) {
            std::string fileHash = to_hex_string(sha256(p.path().string()));
            if (fs::file_size(target) == fs::file_size(p.path())) {
                std::string targetHash = to_hex_string(sha256(target.string()));
                if (fileHash == targetHash) {
                    sameFiles.push_back(p.path());
                    continue;
                }
            }
            target_dir = root / "conflict" / match[2].str();
            fs::create_directories(target_dir);
            target = target_dir / (p.path().stem().string() + "_" + fileHash.substr(0, 5) + p.path().extension().string());
        }
        fs::rename(p.path(), target);
    }

    if (!sameFiles.empty()) {
        std::cout << "Detected same files: \n";
        for (const auto& file : sameFiles) {
            std::cout << file << "\n";
        }
        std::cout << "Delete Y/n: ";
        char input;
        std::cin >> input;
        if (input == 'n' || input == 'N') {
            return;
        }
        for (const auto& file : sameFiles) {
            fs::remove(file);
        }
    }
}

int main() {
    fs::path root = fs::absolute("test");
    process_files(root);
    return 0;
}