import os
import sys
from typing import List

try:
    from supabase import create_client
except Exception as e:
    print("supabase client import failed:", e)
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket = client.storage.from_("avatars")

moved: List[str] = []
failed: List[str] = []


def list_dir(prefix: str):
    try:
        # Some SDKs accept options dict as second param; we keep it minimal
        return bucket.list(prefix)
    except Exception as e:
        print(f"list failed for '{prefix}': {e}")
        return []


def is_file(item: dict) -> bool:
    # Heuristic: presence of '.' in name typically indicates a file with extension
    name = item.get("name") or ""
    return "." in name


def move_or_copy(src: str, dst: str):
    global moved, failed
    try:
        bucket.move(src, dst)
        print(f"moved {src} -> {dst}")
        moved.append(src)
        return
    except Exception:
        # Fallback to download/upload/remove
        try:
            data = bucket.download(src)
            if not data:
                print(f"download returned empty for {src}")
                failed.append(src)
                return
            bucket.upload(dst, data)
            try:
                bucket.remove([src])
            except Exception:
                pass
            print(f"copied {src} -> {dst}")
            moved.append(src)
        except Exception as e2:
            print(f"copy failed for {src}: {e2}")
            failed.append(src)


def fix_nested_avatars():
    # Traverse only under the mistaken top-level 'avatars' directory inside the bucket
    stack = ["avatars"]
    seen = set()
    while stack:
        prefix = stack.pop()
        if prefix in seen:
            continue
        seen.add(prefix)
        items = list_dir(prefix) or []
        for it in items:
            name = it.get("name") or ""
            if not name:
                continue
            path = f"{prefix}/{name}" if prefix else name
            if is_file(it):
                dst = path[len("avatars/"):] if path.startswith("avatars/") else None
                if dst:
                    move_or_copy(path, dst)
            else:
                stack.append(path)


if __name__ == "__main__":
    fix_nested_avatars()
    print("DONE. moved:", len(moved), "failed:", len(failed))


