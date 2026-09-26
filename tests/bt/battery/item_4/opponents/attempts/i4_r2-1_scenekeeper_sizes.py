"""Sum the download sizes of the files pip resolved (report_<pkg>.json) from the PyPI JSON metadata (read only)."""
import json, sys, urllib.request
for pkg in sys.argv[1:]:
    rep = json.load(open(f"report_{pkg}.json"))
    items = rep["install"]
    tot, unknown, big = 0, [], []
    for it in items:
        md = it["metadata"]; name, ver = md["name"], md["version"]
        url = it["download_info"]["url"]
        fn = url.rsplit("/", 1)[-1]
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{ver}/json", timeout=30) as r:
                j = json.load(r)
            size = next((u["size"] for u in j["urls"] if u["filename"] == fn), None)
        except Exception as e:  # noqa: BLE001
            size = None
        if size is None:
            unknown.append(fn)
        else:
            tot += size; big.append((size, fn))
    big.sort(reverse=True)
    print(f"{pkg}: {len(items)} files, download bytes {tot} ({tot/2**20:.1f} MiB), unknown sizes {len(unknown)}")
    for s, fn in big[:8]:
        print(f"   {s/2**20:8.1f} MiB  {fn}")
