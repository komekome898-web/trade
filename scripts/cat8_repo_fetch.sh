#!/bin/sh
# Fetch one GitHub repository for reading only, without downloading blobs over 1 MB
# (cat8 run 10 prompt §2-1; audits 48-49: a plain checkout re-fetches filtered blobs on demand).
# Usage: sh scripts/cat8_repo_fetch.sh <owner/repo> <dest_dir>
# Prints: the downloaded size (.git), the number of files in the tree (N), and the files whose
# blobs were not downloaded (over 1 MB), then checks out only the downloaded files.
# Nothing in the repository is built or executed.
set -eu
repo="$1"; dest="$2"
export GIT_NO_LAZY_FETCH=1
rm -rf "$dest"
git clone -q --depth 1 --filter=blob:limit=1m --no-checkout "https://github.com/$repo.git" "$dest"
cd "$dest"
git rev-list --objects --missing=print HEAD | sed -n 's/^?//p' > ../.missing
git ls-tree -r HEAD | awk 'NR==FNR{m[$1]=1;next} {split($0,a,"\t"); split(a[1],b," "); print ((b[3] in m) ? "SKIPPED\t" : "PRESENT\t") a[2]}' ../.missing - > ../.tree
echo "repo: $repo"
echo "downloaded_bytes: $(du -sb .git | cut -f1)"
echo "files_in_tree(N): $(wc -l < ../.tree)"
echo "blobs_not_downloaded(>1MB): $(grep -c '^SKIPPED' ../.tree || true)"
grep '^SKIPPED' ../.tree | cut -f2 | sed 's/^/  skipped: /' || true
grep '^PRESENT' ../.tree | cut -f2 > ../.present
[ -s ../.present ] && git checkout -q HEAD --pathspec-from-file=../.present
rm -f ../.missing ../.present
