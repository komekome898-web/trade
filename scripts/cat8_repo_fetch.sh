#!/bin/sh
# Fetch one GitHub repository for reading only, without downloading blobs over 1 MB
# (cat8 run 10 prompt §2-1; audits 48-50: a plain checkout re-fetches filtered blobs on demand,
# and the first version silently produced an empty file list when no blob was filtered).
# Usage: sh scripts/cat8_repo_fetch.sh <owner/repo> <dest_dir>
# Prints the downloaded size (.git), the number of files in the tree (N), the files whose blobs
# were not downloaded (over 1 MB), and the checked-out count and size. Exits non-zero if the
# counts do not add up. Nothing in the repository is built or executed.
set -eu
repo="$1"; dest="$2"
export GIT_NO_LAZY_FETCH=1
rm -rf "${dest:?}"
git clone -q --depth 1 --filter=blob:limit=1m --no-checkout "https://github.com/$repo.git" "$dest"
cd "$dest"
git rev-list --objects --missing=print HEAD | sed -n 's/^?//p' > .git/cat8_missing
git ls-tree -r -z HEAD > .git/cat8_tree
python3 - <<'PY'
import sys
missing = set(open(".git/cat8_missing").read().split())
entries = [e for e in open(".git/cat8_tree", "rb").read().split(b"\0") if e]
present, skipped, present_blobs = [], [], []
for e in entries:
    meta, path = e.split(b"\t", 1)
    oid = meta.split()[2].decode()
    (skipped if oid in missing else present).append(path)
    if oid not in missing and meta.split()[1] == b"blob":
        present_blobs.append(oid)
# Object ids have no whitespace, so this list is safe for names with newlines (audit 52).
with open(".git/cat8_present_oids", "w") as f:
    f.write("".join(o + "\n" for o in present_blobs))
with open(".git/cat8_present", "wb") as f:
    for p in present:
        f.write(p + b"\0")
print("files_in_tree(N): %d" % len(entries))
print("blobs_not_downloaded(>1MB): %d" % len(skipped))
for p in skipped:
    print("  skipped: " + p.decode("utf-8", "replace"))
if not entries or len(present) + len(skipped) != len(entries):
    sys.exit("cat8_repo_fetch: counts do not add up (tree %d, present %d, skipped %d)"
             % (len(entries), len(present), len(skipped)))
PY
echo "repo: $repo"
echo "downloaded_bytes: $(du -sb .git | cut -f1)"
# Size of what the checkout would write, from the local blobs only (no lazy fetch).
# Refuse the checkout above CAT8_MAX_CHECKOUT_BYTES (default 500 MB; audit 51).
max_co="${CAT8_MAX_CHECKOUT_BYTES:-524288000}"
git cat-file --batch-check='%(objectsize)' < .git/cat8_present_oids > .git/cat8_sizes
if grep -qv '^[0-9][0-9]*$' .git/cat8_sizes; then
  echo "cat8_repo_fetch: a present blob has no size" >&2; exit 1
fi
exp_co=$(awk '{s+=$1} END{print s+0}' .git/cat8_sizes)
echo "expected_checkout_bytes: $exp_co (limit $max_co)"
if [ "$exp_co" -gt "$max_co" ]; then
  echo "cat8_repo_fetch: checkout would exceed the limit; nothing checked out" >&2
  exit 3
fi
if [ -s .git/cat8_present ]; then
  git checkout -q HEAD --pathspec-from-file=.git/cat8_present --pathspec-file-nul
fi
n_present=$(tr -cd '\0' < .git/cat8_present | wc -c)
n_out=$(git ls-files | wc -l)
echo "checked_out_files: $n_out (expected $n_present)"
echo "checked_out_bytes(without .git): $(du -sb --exclude=.git . | cut -f1)"
[ "$n_out" -eq "$n_present" ] || { echo "cat8_repo_fetch: checked-out count differs" >&2; exit 1; }
