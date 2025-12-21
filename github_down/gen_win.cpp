#define NOMINMAX
#include <windows.h>

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <stdexcept>
#include <clocale>

// ---------------- UTF helpers ----------------
static std::wstring utf8_to_wstring(const std::string& s) {
    if (s.empty()) return L"";
    int wlen = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w(wlen, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), wlen);
    return w;
}

static std::string trim_copy(std::string s) {
    auto is_space = [](unsigned char c) { return c==' '||c=='\t'||c=='\n'||c=='\r'; };
    while (!s.empty() && is_space((unsigned char)s.back())) s.pop_back();
    size_t i = 0;
    while (i < s.size() && is_space((unsigned char)s[i])) i++;
    return s.substr(i);
}

// Quote a single arg for CreateProcess command line.
static std::wstring quote_arg_windows(const std::wstring& arg) {
    bool need_quotes = arg.empty();
    for (wchar_t c : arg) {
        if (c == L' ' || c == L'\t' || c == L'\n' || c == L'\v' || c == L'"') {
            need_quotes = true; break;
        }
    }
    if (!need_quotes) return arg;

    std::wstring out = L"\"";
    size_t bs_count = 0;
    for (wchar_t c : arg) {
        if (c == L'\\') {
            bs_count++;
        } else if (c == L'"') {
            out.append(bs_count * 2 + 1, L'\\');
            out.push_back(L'"');
            bs_count = 0;
        } else {
            if (bs_count) out.append(bs_count, L'\\');
            bs_count = 0;
            out.push_back(c);
        }
    }
    if (bs_count) out.append(bs_count * 2, L'\\');
    out.push_back(L'"');
    return out;
}

// ---------------- RAII cleanup guard ----------------
struct TempBundleGuard {
    std::filesystem::path dir;
    std::filesystem::path aria2_path;

    ~TempBundleGuard() {
        // Best-effort cleanup
        try {
            if (!aria2_path.empty() && std::filesystem::exists(aria2_path)) {
                std::error_code ec;
                std::filesystem::remove(aria2_path, ec);
            }
            if (!dir.empty() && std::filesystem::exists(dir)) {
                std::error_code ec;
                std::filesystem::remove_all(dir, ec);
            }
        } catch (...) {
            // swallow
        }
    }
};

// ---------------- Resource extraction ----------------
static bool extract_resource_to_file(
    const wchar_t* res_name,
    const std::filesystem::path& out_path
) {
    HRSRC hrsrc = FindResourceW(nullptr, res_name, RT_RCDATA);
    if (!hrsrc) return false;

    HGLOBAL hglob = LoadResource(nullptr, hrsrc);
    if (!hglob) return false;

    DWORD size = SizeofResource(nullptr, hrsrc);
    void* data = LockResource(hglob);
    if (!data || size == 0) return false;

    std::ofstream ofs(out_path, std::ios::binary);
    ofs.write(reinterpret_cast<const char*>(data), size);
    return ofs.good();
}



// ---------------- Process runner ----------------
static int run_process(const std::wstring& exe_path, const std::vector<std::wstring>& args, bool show) {
    std::wstring cmdline = quote_arg_windows(exe_path);
    for (const auto& a : args) {
        cmdline.push_back(L' ');
        cmdline += quote_arg_windows(a);
    }

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_SHOW;

    PROCESS_INFORMATION pi{};

    // CreateProcessW may modify buffer
    std::vector<wchar_t> buf(cmdline.begin(), cmdline.end());
    buf.push_back(L'\0');

    BOOL ok = CreateProcessW(
        nullptr,
        buf.data(),
        nullptr, nullptr,
        FALSE,
        show ? 0 : CREATE_NO_WINDOW,
        nullptr,
        nullptr,
        &si,
        &pi
    );

    if (!ok) {
        return -1;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);

    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);

    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    return (int)code;
}

// ---------------- Get temp directory ----------------
static std::filesystem::path get_temp_dir() {
    wchar_t buf[MAX_PATH + 1];
    DWORD n = GetTempPathW(MAX_PATH, buf);
    if (n == 0 || n > MAX_PATH) throw std::runtime_error("GetTempPathW failed");
    return std::filesystem::path(buf);
}

static std::filesystem::path make_unique_subdir(const std::filesystem::path& base) {
    // Use PID + tick count for uniqueness
    DWORD pid = GetCurrentProcessId();
    ULONGLONG t = GetTickCount64();

    std::filesystem::path dir = base / L"MyAria2Bundle";
    std::filesystem::path uniq = dir / (L"run_" + std::to_wstring(pid) + L"_" + std::to_wstring(t));

    std::error_code ec;
    std::filesystem::create_directories(uniq, ec);
    if (ec) throw std::runtime_error("create_directories failed");
    return uniq;
}

int main() {
    // Windows console UTF-8
    SetConsoleCP(65001);
    SetConsoleOutputCP(65001);
    std::setlocale(LC_ALL, ".UTF-8");

    // Proxies list (same as your python)
    const std::vector<std::string> proxies = {
        "https://hk.gh-proxy.org/",
        "https://cdn.gh-proxy.org/",
        "https://gh-proxy.org/",
        "https://edgeone.gh-proxy.org/",
        "https://gh-proxy.top/",
        "https://gh-proxy.net/",
        "https://gh-proxy.com/",
        "https://ghfast.top/",
        "https://gh.ddlc.top/",
        "https://gh.llkk.cc/",
        "https://ghproxy.homeboyc.cn/",
        ""
    };

    TempBundleGuard guard;
    try {
        // Extract aria2c.exe to %TEMP%\MyAria2Bundle\run_xxx\aria2c.exe
        auto temp_base = get_temp_dir();
        guard.dir = make_unique_subdir(temp_base);
        guard.aria2_path = guard.dir / L"aria2c.exe";

        if (!extract_resource_to_file(L"ARIA2_BIN", guard.aria2_path)) {
            std::cerr << "释放 aria2c.exe 失败：资源 ARIA2_BIN 不存在或写入失败。\n";
            return 1;
        }


        {
            int rc = run_process(guard.aria2_path, {L"--version"},false);
            if (rc != 0) {
                std::cerr << "aria2c 自检失败（exit=" << rc << "）。\n";
                return 1;
            }
        }

        std::cout << "请输入GitHub文件链接: ";
        std::string input_url;
        std::getline(std::cin, input_url);
        input_url = trim_copy(input_url);
        if (input_url.empty()) {
            std::cerr << "输入为空，退出。\n";
            return 1;
        }

        std::vector<std::wstring> args = {
            L"--auto-file-renaming=false",
            L"--retry-wait=2",
            L"--max-tries=0",
            L"--timeout=10",
            L"--connect-timeout=5",
            L"--lowest-speed-limit=100K",
            L"-x", L"4",
            L"-s", L"24",
            L"-k", L"1M"
        };

        for (const auto& p : proxies) {
            std::string full = p + input_url;    
            args.push_back(utf8_to_wstring(full)); 
        }

        int rc = run_process(guard.aria2_path, args,true);
        if (rc != 0) {
            std::cerr << "aria2c 执行失败（exit=" << rc << "）。\n";
        }
        return rc;

    } catch (const std::exception& e) {
        std::cerr << "异常: " << e.what() << "\n";
        return 1;
    }
}
