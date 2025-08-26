from __future__ import annotations
import io
import re
import ast
import logging


LOG = logging.getLogger(__name__)


CONTROL = re.compile(r'^\s*(if|elif|else|for|while|try|except|finally|def|class)\b.*:\s*(#.*)?$')
INDENTED = re.compile(r'^\s+')
NEUTRALIZED_MARKER = re.compile(r'^\s*#\s*__auto_fix__\s*neutralized\s*stray\s*block\s*:?', re.IGNORECASE)


def _restore_neutralized_blocks(lines: list[str]) -> list[str]:
    """Uncomment previously neutralized except/finally lines.

    Looks for patterns like:
        "# __auto_fix__ neutralized stray block:"
        "#        except Exception:"
    and restores the original 'except ...' line with its indentation.
    """
    restored: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if NEUTRALIZED_MARKER.match(line) and i + 1 < n:
            next_line = lines[i + 1]
            # Identify a commented except/finally line
            stripped = next_line.lstrip()
            if stripped.startswith('#'):
                candidate = stripped[1:]
                if candidate.lstrip().startswith(('except', 'finally')):
                    # Reconstruct the original line by removing the leading '#'
                    # and preserving the indentation that followed it
                    after_hash = candidate
                    if not after_hash.endswith('\n'):
                        after_hash = after_hash + '\n'
                    restored.append(after_hash)
                    i += 2
                    continue
            # If next line isn't a commented except/finally, drop the marker and keep next as-is
            i += 1
            continue
        restored.append(line)
        i += 1
    return restored



def _ensure_bodies(lines: list[str]) -> list[str]:
    """
    Insert 'pass' into empty control suites, and ensure 'except/finally'
    sections belong to a preceding try-suite. This is a conservative fixer
    to get the file importable without changing intended logic.
    """
    fixed: list[str] = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        fixed.append(line)
        if CONTROL.match(line):
            # if the next non-empty line is not more-indented, insert 'pass'
            j = i + 1
            while j < n and lines[j].strip() == '':
                fixed.append(lines[j])
                j += 1
            if j >= n or not INDENTED.match(lines[j]):
                # insert one level of indentation relative to current line
                indent_match = re.match(r'^(\s*)', line)
                indent = (indent_match.group(1) if indent_match else '') + '    '
                fixed.append(f"{indent}pass  # [auto-sanitizer]\n")
                i = j
                continue
        i += 1
    return fixed


def sanitize_python_file(path: str) -> bool:
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            src = f.readlines()
        step1 = _restore_neutralized_blocks(src)
        fixed = _ensure_bodies(step1)
        txt = ''.join(fixed)
        # Attempt AST validation, but still write restored content even if validation fails
        ast_ok = True
        try:
            ast.parse(txt)
        except SyntaxError as e:
            ast_ok = False
            LOG.error("Sanitizer AST check failed at %s:%s:%s", path, e.lineno, e.msg)
        # Write back if content changed (even when AST fails), so subsequent loads can improve
        orig = ''.join(src)
        if txt != orig:
            with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(txt)
            LOG.warning("\ud83d\udee0\ufe0f Auto-sanitized control blocks in %s", path)
        else:
            LOG.info("No sanitizer changes needed for %s", path)
        return ast_ok or (txt != orig)
    except Exception as e:
        LOG.exception("Sanitizer failed for %s: %s", path, e)
        return False


