from subprocess import run

proxies = [
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
    "",    
]

cmd = [
    "aria2c",
    "--auto-file-renaming=false",
    "--retry-wait=2",
    "--max-tries=0",
    "--timeout=10",
    "--connect-timeout=5",
    "--lowest-speed-limit=100K",
    "-x","4","-s","24","-k","1M",
]

try:
    run("aria2c --version", check=True, capture_output=True)
except Exception:
    print("请先安装aria2")
    exit(1)

input_url = input("请输入GitHub文件链接: ").strip()
cmd.extend(
    [f"{proxy}{input_url}" for proxy in proxies]
)
run(cmd)
