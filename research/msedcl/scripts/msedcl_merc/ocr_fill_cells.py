"""Second OCR pass: for every table row (anchored on a text box in the label/source columns)
re-recognise each of the 4 numeric cells that the first pass left empty, using a tight crop.
Adds synthetic boxes (flag 'cellpass': true) to the JSON so the parser can use them.
Usage: python ocr_fill_cells.py OCR_DIR IMG_DIR
"""
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

ocr_dir, img_dir = sys.argv[1:3]
eng = RapidOCR()
NUM = re.compile(r"^-?[\d,]+[.'][\d]{1,2}$")

for jp in sorted(glob.glob(os.path.join(ocr_dir, "*.json"))):
    boxes = json.load(open(jp))
    if any(b.get("cellpass") for b in boxes):
        continue
    img = Image.open(os.path.join(img_dir, os.path.basename(jp)[:-5] + ".png")).convert("RGB")
    hdr = sorted([b for b in boxes if b["text"].strip().upper() in ("MYT", "ACTUAL") and b["y1"] < 650],
                 key=lambda b: b["x0"])
    if len(hdr) != 4:
        print("skip", jp)
        continue
    hgt = sorted(b["y1"] - b["y0"] for b in boxes)[len(boxes) // 2]
    cent = [(b["x0"] + b["x1"]) / 2 for b in hdr]
    w = cent[1] - cent[0]
    hdr_y = max(b["y1"] for b in hdr) + 1.1 * hgt
    anchors = [b for b in boxes if b["x1"] < cent[0] - 0.5 * w and (b["y0"] + b["y1"]) / 2 > hdr_y
               and not re.match(r"^[IVX]+$|^\d+$|^[A-D]$", b["text"].strip())]
    rows = []
    for a in sorted(anchors, key=lambda b: (b["y0"] + b["y1"]) / 2):
        yc = (a["y0"] + a["y1"]) / 2
        if rows and abs(rows[-1] - yc) < 0.45 * hgt:
            continue
        rows.append(yc)
    added = 0
    for yc in rows:
        for ci, c in enumerate(cent):
            x0, x1 = c - 0.5 * w + 3, c + 0.5 * w - 3
            have = [b for b in boxes if abs((b["y0"] + b["y1"]) / 2 - yc) < 0.45 * hgt
                    and x0 <= (b["x0"] + b["x1"]) / 2 <= x1]
            if have:
                continue
            crop = img.crop((int(x0), int(yc - 0.75 * hgt), int(x1), int(yc + 0.75 * hgt)))
            # pad with white for the recogniser
            pad = Image.new("RGB", (crop.width + 40, crop.height + 20), "white")
            pad.paste(crop, (20, 10))
            res, _ = eng(np.array(pad), use_det=False, use_cls=False, use_rec=True)
            if not res:
                continue
            item = res[0]
            while isinstance(item, (list, tuple)) and item and isinstance(item[0], (list, tuple)):
                item = item[0]
            text, score = str(item[0]), float(item[1])
            t = text.strip().replace(" ", "")
            if NUM.match(t) and score > 0.5:
                boxes.append({"x0": x1 - 50, "x1": x1 - 2, "y0": yc - hgt / 2, "y1": yc + hgt / 2,
                              "text": t.replace("'", "."), "score": score, "cellpass": True})
                added += 1
    boxes.append({"x0": 0, "x1": 0, "y0": 0, "y1": 0, "text": "", "score": 0, "cellpass": True})
    json.dump(boxes, open(jp, "w"))
    print(os.path.basename(jp), "added", added, flush=True)
