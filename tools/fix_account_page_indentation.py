import io, os, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCOUNT = ROOT / "trackpro" / "ui" / "pages" / "account" / "account_page.py"


def fix_file(path: pathlib.Path):
    src = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = []
    i = 0
    changed = False

    def next_sig(idx):
        # next non-empty, non-comment line index
        j = idx + 1
        while j < len(src):
            line = src[j]
            if line.strip() and not line.strip().startswith("#"):
                return j
            j += 1
        return None

    while i < len(src):
        line = src[i]
        s = line.strip()

        # If/for/while/try/with ending with ":" but the next significant line is dedented or starts with except/finally/elif/else
        if s.endswith(":") and re.match(r"^(if|for|while|try|with|elif|else|except|finally|def|class)\b", s):
            j = next_sig(i)
            if j is None:
                # file ends after a header -> add pass
                out.append(line)
                out.append((" " * (len(line) - len(line.lstrip()))) + "    pass")
                changed = True
                i += 1
                continue
            cur_indent = len(line) - len(line.lstrip())
            nxt = src[j]
            nxt_indent = len(nxt) - len(nxt.lstrip())
            nxt_stripped = nxt.strip().split(" ", 1)[0]

            # Missing body if the next token is an 'except/finally/elif/else' or dedent at same/less indent
            if (nxt_indent <= cur_indent) or nxt_stripped in {"except:", "finally:", "elif", "else:"} or re.match(r"^(except|finally|elif|else)\b", nxt.strip()):
                out.append(line)
                out.append((" " * cur_indent) + "    pass")
                changed = True
                i += 1
                continue

        # Lone "except:" or "finally:" with no preceding try at the same/lower indent -> neutralize
        if re.match(r"^\s*(except\b|finally\b).*:\s*$", line) and "try" not in "".join(src[max(0, i-10):i]):
            out.append("# __auto_fix__ neutralized stray block:\n#" + line)
            changed = True
            i += 1
            continue

        out.append(line)
        i += 1

    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


if __name__ == "__main__":
    ok = fix_file(ACCOUNT)
    print("Patched account_page.py" if ok else "No changes needed")


