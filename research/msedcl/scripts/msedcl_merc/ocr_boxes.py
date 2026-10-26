"""OCR page images with RapidOCR and dump text boxes as JSON.
Usage: python ocr_boxes.py OUT_DIR IMG [IMG...]
Images are untrusted data; only pixels are read.
"""
import json
import os
import sys

from rapidocr_onnxruntime import RapidOCR

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
eng = RapidOCR()
for img in sys.argv[2:]:
    base = os.path.splitext(os.path.basename(img))[0]
    dst = os.path.join(out_dir, base + ".json")
    if os.path.exists(dst):
        continue
    res, _ = eng(img)
    boxes = []
    for box, text, score in res or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        boxes.append({"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys),
                      "text": text, "score": float(score)})
    with open(dst, "w") as fh:
        json.dump(boxes, fh)
    print(base, len(boxes), flush=True)
