import csv
import html
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "feature_experiments" / "simple_slides"
SLIDES = OUT / "slides"
PPTX = OUT / "nfl-model-findings-simple-summary.pptx"
HTML = OUT / "nfl-model-findings-simple-summary.html"

W, H = 1600, 900
BG = "#F7F9FB"
INK = "#172026"
MUTED = "#5A6872"
LINE = "#D8E0E6"
GREEN = "#13795B"
BLUE = "#2563A7"
GOLD = "#B7791F"
RED = "#B42318"
PANEL = "#FFFFFF"

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"


def f(size, bold=False, black=False):
    return ImageFont.truetype(BLACK if black else BOLD if bold else FONT, size)


def draw_wrapped(draw, text, xy, font, fill=INK, width=900, line_gap=10):
    x, y = xy
    words = text.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= width:
            line = test
        else:
            draw.text((x, y), line, font=font, fill=fill)
            y += font.size + line_gap
            line = word
    if line:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def rounded(draw, box, fill, outline=None, radius=18, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def new_slide(title=None, kicker="NFL Play-Type Model Experiments"):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 18), fill=GREEN)
    draw.text((80, 52), kicker.upper(), font=f(22, bold=True), fill=GREEN)
    if title:
        draw_wrapped(draw, title, (80, 100), f(54, black=True), width=1160, line_gap=8)
    draw.text((80, 820), "Simplified readout from local 2020-2024 experiments", font=f(22), fill=MUTED)
    return img, draw


def metric_card(draw, box, number, label, color=GREEN):
    rounded(draw, box, PANEL, LINE, 18)
    x1, y1, x2, y2 = box
    draw.text((x1 + 32, y1 + 26), number, font=f(54, black=True), fill=color)
    draw_wrapped(draw, label, (x1 + 32, y1 + 98), f(25, bold=True), fill=INK, width=x2 - x1 - 64, line_gap=8)


def bar_chart(draw, data, box, max_value=None, color=BLUE, accent_name=None):
    x1, y1, x2, y2 = box
    max_value = max_value or max(v for _, v in data)
    row_h = (y2 - y1) / len(data)
    for i, (name, value) in enumerate(data):
        y = y1 + i * row_h
        label_font = f(24, bold=name == accent_name)
        draw.text((x1, y + 7), name, font=label_font, fill=INK)
        tx = x1 + 380
        ty = y + 12
        tw = x2 - tx - 115
        draw.rounded_rectangle((tx, ty, tx + tw, ty + 28), radius=8, fill="#E8EDF1")
        fill = GREEN if name == accent_name else color
        draw.rounded_rectangle((tx, ty, tx + max(8, tw * value / max_value), ty + 28), radius=8, fill=fill)
        draw.text((x2 - 95, y + 6), f"{value:.4f}", font=f(23), fill=MUTED)


def slide_1():
    img, draw = new_slide(None, "NFL model findings")
    draw.text((80, 105), "The model is learning", font=f(52, black=True), fill=INK)
    draw.text((80, 170), "football situation", font=f(96, black=True), fill=GREEN)
    draw_wrapped(
        draw,
        "The strongest signals are not fancy: down, field position, shotgun, and red-zone context explain most of the predictions.",
        (84, 300),
        f(36, bold=True),
        fill=INK,
        width=1000,
        line_gap=12,
    )
    metric_card(draw, (86, 475, 450, 660), "0.728", "Best holdout accuracy", GREEN)
    metric_card(draw, (485, 475, 850, 660), "0.823", "Best macro F1", BLUE)
    metric_card(draw, (885, 475, 1250, 660), "0", "Feature mismatches after backfill", GOLD)
    draw.text((1210, 170), "pass", font=f(34, bold=True), fill=BLUE)
    draw.text((1210, 230), "run", font=f(34, bold=True), fill=GREEN)
    draw.text((1210, 290), "punt", font=f(34, bold=True), fill=GOLD)
    draw.text((1210, 350), "field goal", font=f(34, bold=True), fill=RED)
    return img


def slide_2():
    img, draw = new_slide("What we tested")
    tests = [
        ("1", "Current random forest", "The model as designed, but with correct engineered features."),
        ("2", "No yardage buckets", "Remove short/medium/long-yardage flags and keep raw ydstogo."),
        ("3", "Tendency features", "Add simple team and defense tendency rates."),
        ("4", "Staged model", "First split special teams vs offense, then classify play type."),
    ]
    x = 82
    for i, (num, title, body) in enumerate(tests):
        y = 235 + i * 130
        rounded(draw, (x, y, 1470, y + 98), PANEL, LINE, 16)
        draw.ellipse((x + 28, y + 24, x + 78, y + 74), fill=GREEN if i != 2 else GOLD)
        draw.text((x + 45, y + 33), num, font=f(26, black=True), fill="white", anchor="mm")
        draw.text((x + 108, y + 18), title, font=f(31, black=True), fill=INK)
        draw.text((x + 108, y + 58), body, font=f(24), fill=MUTED)
    return img


def slide_3():
    img, draw = new_slide("The scoreboard")
    data = [
        ("Staged RF", 0.7284),
        ("Current RF", 0.7279),
        ("No buckets RF", 0.7271),
        ("Logistic baseline", 0.7172),
        ("Tendency RF", 0.7151),
        ("Dummy baseline", 0.5210),
    ]
    bar_chart(draw, data, (105, 230, 1430, 630), max_value=0.75, color=BLUE, accent_name="Staged RF")
    draw_wrapped(
        draw,
        "Plain English: the staged model won, but only slightly. The current random forest is already strong.",
        (110, 680),
        f(32, bold=True),
        fill=INK,
        width=1120,
        line_gap=10,
    )
    return img


def slide_4():
    img, draw = new_slide("Removing yardage buckets barely changed anything")
    metric_card(draw, (92, 245, 455, 455), "-0.0009", "Accuracy change after removing buckets", RED)
    metric_card(draw, (490, 245, 855, 455), "-0.0001", "Macro F1 change after removing buckets", RED)
    metric_card(draw, (888, 245, 1253, 455), "+0.0013", "Pass F1 change", GREEN)
    draw_wrapped(
        draw,
        "Conclusion: short_yardage, medium_yardage, and long_yardage are mostly redundant because ydstogo already tells the model the same story.",
        (100, 535),
        f(36, bold=True),
        fill=INK,
        width=1220,
        line_gap=14,
    )
    draw_wrapped(
        draw,
        "Recommendation: safe to remove for simplicity, but do not expect a real accuracy gain.",
        (100, 675),
        f(30),
        fill=MUTED,
        width=1180,
        line_gap=10,
    )
    return img


def slide_5():
    img, draw = new_slide("The first tendency features did not help")
    data = [
        ("Current RF", 0.8194),
        ("Tendency RF", 0.7842),
        ("Logistic baseline", 0.7981),
    ]
    bar_chart(draw, data, (110, 250, 1375, 475), max_value=0.84, color=BLUE, accent_name="Current RF")
    draw_wrapped(
        draw,
        "This does not mean tendencies are a bad idea. It means the first version was too blunt.",
        (110, 545),
        f(38, bold=True),
        fill=INK,
        width=1190,
        line_gap=12,
    )
    draw_wrapped(
        draw,
        "Better next attempt: rolling season-to-date tendencies by team, down, distance, red zone, and score state. Avoid broad historical averages that may leak old behavior into a new season.",
        (110, 650),
        f(29),
        fill=MUTED,
        width=1225,
        line_gap=10,
    )
    return img


def slide_6():
    img, draw = new_slide("The staged model is the best idea to keep testing")
    metric_card(draw, (92, 250, 455, 460), "+0.0041", "Macro F1 gain vs current RF", GREEN)
    metric_card(draw, (490, 250, 855, 460), "+0.0005", "Accuracy gain vs current RF", GREEN)
    rounded(draw, (930, 235, 1435, 480), PANEL, LINE, 18)
    draw.text((970, 270), "Why it works", font=f(38, black=True), fill=INK)
    draw_wrapped(
        draw,
        "Punts and field goals are different decisions than pass vs run. Splitting that decision first matches football logic.",
        (970, 330),
        f(27, bold=True),
        fill=MUTED,
        width=390,
        line_gap=10,
    )
    draw_wrapped(
        draw,
        "Next model experiment: make the staged flow the main candidate, then tune each stage separately.",
        (110, 590),
        f(38, bold=True),
        fill=INK,
        width=1200,
        line_gap=12,
    )
    return img


def slide_7():
    img, draw = new_slide("We found and fixed an app data problem")
    before = [
        ("posteam_type", "100% wrong"),
        ("defteam", "100% wrong"),
        ("season", "100% missing"),
        ("quarter_half", "100% missing"),
        ("long_yardage", "65.5% wrong"),
    ]
    rounded(draw, (85, 270, 725, 720), PANEL, LINE, 18)
    draw.text((125, 305), "Before", font=f(42, black=True), fill=RED)
    for i, (name, value) in enumerate(before):
        y = 385 + i * 58
        draw.text((125, y), name, font=f(27, bold=True), fill=INK)
        draw.text((535, y), value, font=f(27, bold=True), fill=RED)
    rounded(draw, (810, 270, 1450, 720), PANEL, LINE, 18)
    draw.text((850, 305), "After", font=f(42, black=True), fill=GREEN)
    checks = ["seed.py fills fields", "predict_play recomputes fields", "backfill corrected SQLite", "verification now shows 0 mismatches"]
    for i, text in enumerate(checks):
        y = 395 + i * 66
        draw.text((850, y), "OK", font=f(28, black=True), fill=GREEN)
        draw.text((915, y), text, font=f(29, bold=True), fill=INK)
    return img


def slide_8():
    img, draw = new_slide("Simple recommendation")
    steps = [
        ("Keep", "down, yardline_100, shotgun, ydstogo, red_zone"),
        ("Simplify", "remove yardage buckets if you want cleaner features"),
        ("Promote", "staged model to the next serious candidate"),
        ("Retest", "tendencies as rolling season-to-date features, not broad averages"),
        ("Protect", "keep seed, backfill, and inference feature logic synchronized"),
    ]
    for i, (verb, body) in enumerate(steps):
        y = 220 + i * 105
        color = [GREEN, BLUE, GOLD, BLUE, GREEN][i]
        draw.text((105, y), verb, font=f(37, black=True), fill=color)
        draw_wrapped(draw, body, (300, y + 4), f(31, bold=True), fill=INK, width=1050, line_gap=8)
    draw_wrapped(
        draw,
        "Bottom line: the model is not broken. It mostly needs a cleaner feature set, staged structure, and better tendency engineering.",
        (105, 720),
        f(28, bold=True),
        fill=MUTED,
        width=1250,
        line_gap=8,
    )
    return img


def save_slides():
    SLIDES.mkdir(parents=True, exist_ok=True)
    slide_funcs = [slide_1, slide_2, slide_3, slide_4, slide_5, slide_6, slide_7, slide_8]
    paths = []
    for idx, func in enumerate(slide_funcs, start=1):
        path = SLIDES / f"slide_{idx:02d}.png"
        func().save(path)
        paths.append(path)
    return paths


def write(path, text):
    path.write_text(text, encoding="utf-8")


def pptx_xml(slide_count):
    slides = "\n".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i}"/>' for i in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId{slide_count + 1}"/></p:sldMasterIdLst>
  <p:sldIdLst>{slides}</p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''


def slide_xml(idx):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:pic>
        <p:nvPicPr><p:cNvPr id="2" name="Slide {idx}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def rels_xml(slide_count):
    rels = "\n".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, slide_count + 1)
    )
    rels += f'\n<Relationship Id="rId{slide_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'''


def content_types(slide_count):
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
    ]
    overrides += [
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    ]
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  {''.join(overrides)}
</Types>'''


MASTER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>'''

LAYOUT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>'''

THEME = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Simple Findings">
  <a:themeElements><a:clrScheme name="Simple"><a:dk1><a:srgbClr val="172026"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="5A6872"/></a:dk2><a:lt2><a:srgbClr val="F7F9FB"/></a:lt2><a:accent1><a:srgbClr val="13795B"/></a:accent1><a:accent2><a:srgbClr val="2563A7"/></a:accent2><a:accent3><a:srgbClr val="B7791F"/></a:accent3><a:accent4><a:srgbClr val="B42318"/></a:accent4><a:accent5><a:srgbClr val="D8E0E6"/></a:accent5><a:accent6><a:srgbClr val="FFFFFF"/></a:accent6><a:hlink><a:srgbClr val="2563A7"/></a:hlink><a:folHlink><a:srgbClr val="13795B"/></a:folHlink></a:clrScheme><a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/></a:majorFont><a:minorFont><a:latin typeface="Arial"/></a:minorFont></a:fontScheme><a:fmtScheme name="Simple"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements>
</a:theme>'''


def build_pptx(slides):
    with zipfile.ZipFile(PPTX, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types(len(slides)))
        z.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>''')
        z.writestr("ppt/presentation.xml", pptx_xml(len(slides)))
        z.writestr("ppt/_rels/presentation.xml.rels", rels_xml(len(slides)))
        z.writestr("ppt/slideMasters/slideMaster1.xml", MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>''')
        z.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>''')
        z.writestr("ppt/theme/theme1.xml", THEME)
        for i, slide_path in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image{i}.png"/></Relationships>''')
            z.write(slide_path, f"ppt/media/image{i}.png")


def build_html(slides):
    body = "\n".join(
        f'<section><img src="slides/{html.escape(path.name)}" alt="Slide {i}"></section>'
        for i, path in enumerate(slides, start=1)
    )
    write(
        HTML,
        f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NFL Model Findings Simple Summary</title>
  <style>
    body {{ margin: 0; background: #101820; font-family: Arial, sans-serif; }}
    section {{ min-height: 100vh; display: grid; place-items: center; padding: 24px; box-sizing: border-box; }}
    img {{ width: min(1200px, 100%); border-radius: 8px; box-shadow: 0 18px 60px rgba(0,0,0,.35); }}
  </style>
</head>
<body>{body}</body>
</html>''',
    )


def main():
    slides = save_slides()
    build_pptx(slides)
    build_html(slides)
    print(PPTX)
    print(HTML)


if __name__ == "__main__":
    main()
