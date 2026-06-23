import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def slide_number(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def shape_texts(root):
    items = []
    for sp in root.findall(".//p:sp", NS):
        texts = [t.text or "" for t in sp.findall(".//a:t", NS)]
        text = "".join(texts).strip()
        if not text:
            continue
        ph = sp.find(".//p:ph", NS)
        ph_type = ph.attrib.get("type") if ph is not None else None
        name_el = sp.find(".//p:cNvPr", NS)
        name = name_el.attrib.get("name", "") if name_el is not None else ""
        items.append({"placeholder": ph_type, "name": name, "text": text})
    return items


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pptx = Path(sys.argv[1])
    with zipfile.ZipFile(pptx) as zf:
        slide_names = sorted(
            [n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
            key=slide_number,
        )
        slides = []
        for idx, name in enumerate(slide_names, start=1):
            root = ET.fromstring(zf.read(name))
            items = shape_texts(root)
            title = ""
            for item in items:
                if item["placeholder"] in {"title", "ctrTitle"}:
                    title = item["text"]
                    break
            if not title and items:
                title = items[0]["text"]
            body = [item["text"] for item in items if item["text"] != title]
            slides.append(
                {
                    "slide": idx,
                    "title": title,
                    "text_count": len(items),
                    "body_count": len(body),
                    "body": body,
                    "all_text": [item["text"] for item in items],
                }
            )
    print(json.dumps(slides, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
