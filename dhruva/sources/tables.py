"""Text-table extraction for RPC settlement PDFs (pdftotext -layout output).

RPC accounts are machine-generated PDFs whose tables survive `pdftotext
-layout` as fixed-width text. Every parser here returns rows *and* checks them
against the table's own TOTAL row; a table whose rows do not add up is
reported as a parse error instead of being published.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

NUM = r"-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"
# Not part of a date or code such as 28-09-2026, 04/10/26 or U-7.
NUM_RE = re.compile(rf"(?<![\w./-])({NUM})(?![\w/-]|\.\d)")
# Words that sit beside rows in some layouts and are never part of a name.
NOISE = re.compile(r"^(payable( by)?|receivable( by)?|by tras|tras|provider|providers|-|\(\+\)|\(-\))$", re.I)


PAGE_RE = re.compile(r"\bPage\s+\d+(\s+of\s+\d+)?\s*$", re.I)


class ParseError(ValueError):
    pass


def pdf_text(path: Path) -> str:
    if not shutil.which("pdftotext"):
        raise ParseError("pdftotext (poppler-utils) is not installed")
    out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=120)
    if out.returncode != 0 and not out.stdout:
        raise ParseError(f"pdftotext failed: {out.stderr.decode(errors='replace')[:200]}")
    return out.stdout.decode("utf-8", errors="replace")


def num(tok: str) -> float:
    return float(tok.replace(",", ""))


def numbers(line: str) -> list[tuple[float, int, int]]:
    """Numeric tokens with their character spans."""
    return [(num(m.group(1)), m.start(1), m.end(1)) for m in NUM_RE.finditer(line)]


@dataclass
class Table:
    rows: list[dict] = field(default_factory=list)
    total: list[float] | None = None
    status: str = "ok"          # ok | unvalidated | parse_error
    message: str = ""


def section(lines: list[str], start_pat: str, end_pat: str | None = None, after: int = 0,
            include_end: bool = False) -> list[str]:
    """Lines from the first match of start_pat (at or after `after`) up to end_pat."""
    sre = re.compile(start_pat, re.I)
    for i in range(after, len(lines)):
        if sre.search(lines[i]):
            j = i + 1
            if end_pat:
                ere = re.compile(end_pat, re.I)
                while j < len(lines) and not ere.search(lines[j]):
                    j += 1
                if include_end and j < len(lines):
                    j += 1
            else:
                j = len(lines)
            return lines[i:j]
    return []


TOTAL_ROW = r"^\s*(?:-\s+)?(?:total|grand total)\s+-?\d"


def _is_total(line: str) -> bool:
    """A TOTAL row (the word followed by figures), not a header like 'Total Charges/'."""
    return bool(re.match(TOTAL_ROW, line, re.I)) or line.strip().lower() == "total"


def is_fragment(t: str) -> bool:
    """A wrapped piece of a name ('I&II', '7&8', 'irm'), as opposed to a line of figures or a label."""
    t = t.strip()
    return (bool(t) and len(t) < 40 and not re.search(r"\d\.\d|\d{4,}|\d,\d", t)
            and not NOISE.match(t) and not _is_total(t) and bool(re.search(r"[A-Za-z&]", t)))


def _clean_name(s: str) -> str:
    s = re.sub(r"^\s*\d{1,3}\s+", "", s)            # leading serial number
    return " ".join(s.split()).strip(" -:")


def numbered_rows(lines: list[str], ncols: int, names: list[str] | None = None) -> Table:
    """Rows shaped `[sr] NAME n1 ... nK [trailing words]` with exactly `ncols` numbers.

    Names that wrap onto the lines above/below a row with no name are joined.
    The TOTAL line validates every column.
    """
    tbl = Table()
    parsed: list[tuple[int, str, list[float]]] = []
    for i, line in enumerate(lines):
        if PAGE_RE.search(line):
            continue
        nums = numbers(line)
        if _is_total(line):
            vals = [v for v, *_ in nums]
            if len(vals) >= ncols:
                tbl.total = vals[-ncols:] if len(vals) > ncols else vals
            continue
        if len(nums) < ncols:
            continue
        lead = nums[0][1]
        cut = nums[-ncols][1]
        head = line[:cut]
        sr = re.match(r"^\s*(\d{1,3})\s", head)
        # serial number must precede the name; numbers inside the name stay in it
        name = _clean_name(head)
        if sr is None and lead < cut and not re.search(r"[A-Za-z]", head):
            continue
        parsed.append((i, name, [v for v, *_ in nums[-ncols:]]))
    for k, (i, name, vals) in enumerate(parsed):
        if not name:
            prev_i = parsed[k - 1][0] if k else -1
            next_i = parsed[k + 1][0] if k + 1 < len(parsed) else len(lines)
            frag = []
            for j in list(range(i - 1, prev_i, -1))[:2][::-1] + list(range(i + 1, next_i))[:2]:
                t = lines[j].strip()
                if is_fragment(t):
                    frag.append(t)
            name = " ".join(frag)
        if not name:
            tbl.status, tbl.message = "parse_error", f"row {k + 1} has no provider name"
            return tbl
        tbl.rows.append({"name": name, "values": vals})
    return validate(tbl, ncols)


def validate(tbl: Table, ncols: int, cols: list[int] | None = None, tol_rel: float = 1e-5) -> Table:
    """Each column must add up to the TOTAL row within rounding (half a unit per row)."""
    if not tbl.rows:
        tbl.status, tbl.message = "parse_error", "no rows found"
        return tbl
    if tbl.total is None:
        tbl.status, tbl.message = "unvalidated", "table has no TOTAL row to check against"
        return tbl
    for c in cols if cols is not None else range(ncols):
        s = sum(r["values"][c] or 0 for r in tbl.rows if r["values"][c] is not None)
        t = tbl.total[c] if c < len(tbl.total) else None
        if t is None:
            continue
        if abs(s - t) > max(2.0, 0.5 * len(tbl.rows), abs(t) * tol_rel):
            tbl.status = "parse_error"
            tbl.message = f"column {c + 1}: rows sum to {s:,.2f} but TOTAL says {t:,.2f}"
            return tbl
    return tbl


def find_index(lines: list[str], pat: str, after: int = 0) -> int:
    rx = re.compile(pat, re.I)
    for i in range(after, len(lines)):
        if rx.search(lines[i]):
            return i
    return -1


def positional_rows(lines: list[str], centers: list[int], total_cols: list[int] | None = None,
                    heading_pat: str | None = None) -> Table:
    """Rows whose numbers sit under column headers; blank cells are allowed.

    Each number goes to the column whose header centre is nearest its right
    edge. Category headings are capitalised lines without figures (or lines
    matching `heading_pat` when the layout also prints labels elsewhere).
    A row with a serial number but no name takes its name from the wrapped
    text lines directly above and below it.
    """
    tbl = Table()
    category = None
    hre = re.compile(heading_pat) if heading_pat else None

    def text_only(t: str) -> bool:
        return is_fragment(t) and not re.match(r"^-?\s*(sub ?total|total)\b", t, re.I)

    for i, line in enumerate(lines):
        if PAGE_RE.search(line):
            continue
        nums = numbers(line)
        if nums and re.match(r"^\s*\d{1,3}\s+[^\d\s-]", line):
            nums = nums[1:]                      # leading serial number, not a figure
        t = line.strip()
        if hre is not None:
            heading = bool(hre.match(t)) and not nums
        else:
            heading = bool(t and re.fullmatch(r"[A-Z0-9 .()&/,'-]{4,}", t) and not NOISE.match(t) and not _is_total(t)
                           and all(float(v).is_integer() and abs(v) < 1000 and "," not in line[s:e] and "." not in line[s:e]
                                   for v, s, e in nums))
        if heading:
            category = re.sub(r"^[A-Z]\.\s*", "", t).title()
            continue
        if not nums:
            continue
        if re.search(r"sub ?total", line, re.I):
            continue
        vals: list[float | None] = [None] * len(centers)
        for v, s, e in nums:
            k = min(range(len(centers)), key=lambda c: abs(centers[c] - e))
            vals[k] = v
        head = line[: nums[0][1]]
        if _is_total(line) or _clean_name(head).lower() == "total":
            tbl.total = vals
            continue
        nxt = next((lines[j].strip() for j in range(i + 1, min(len(lines), i + 3)) if lines[j].strip()), "")
        if re.fullmatch(r"(?i)(?:[A-Z&() ]+\s)?sub ?total", nxt):
            continue                             # a subtotal whose label wraps onto the next line
        name = _clean_name(head)
        if not name and re.match(r"^\s*\d{1,3}\s+-?\d", line):
            above = next((lines[j].strip() for j in range(i - 1, max(-1, i - 3), -1) if text_only(lines[j].strip())), "")
            below = next((lines[j].strip() for j in range(i + 1, min(len(lines), i + 3)) if text_only(lines[j].strip())), "")
            if hre is not None and hre.match(below):
                below = ""
            name = above + ("" if below[:1].islower() else " ") + below if below else above
            name = name.strip()
        if not name:
            continue
        tbl.rows.append({"name": name, "category": category, "values": vals})
    return validate(tbl, len(centers), total_cols)


def header_centres(line: str, words: list[str]) -> list[int]:
    """Right edges of successive header words, used as column anchors."""
    out, pos = [], 0
    for w in words:
        i = line.find(w, pos)
        if i < 0:
            raise ParseError(f"header word {w!r} not found")
        out.append(i + len(w))
        pos = i + len(w)
    return out
