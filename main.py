from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import re

app = FastAPI()
client = OpenAI(
    base_url="https://api.featherless.ai/v1",
    api_key="rc_948fc6d4e6b6e13cf914448bae5045c3be2a2cd80d499cb0ac8e3e2cbd8cd306",
)

# ── Colours matching the reference image ──────────────────────────────────────
GREEN       = colors.HexColor("#4CAF50")   # header / footer bar
LIGHT_GRAY  = colors.HexColor("#F5F5F5")   # alternating row background
MID_GRAY    = colors.HexColor("#CCCCCC")   # divider lines
DARK_TEXT   = colors.HexColor("#212121")
WHITE       = colors.white

# ── Reusable styles ───────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["header_title"] = ParagraphStyle(
        "header_title",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    styles["header_sub"] = ParagraphStyle(
        "header_sub",
        fontName="Helvetica",
        fontSize=9,
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=13,
    )
    styles["clinic_name"] = ParagraphStyle(
        "clinic_name",
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    styles["clinic_address"] = ParagraphStyle(
        "clinic_address",
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        leading=13,
    )
    styles["patient_label"] = ParagraphStyle(
        "patient_label",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=DARK_TEXT,
    )
    styles["patient_value"] = ParagraphStyle(
        "patient_value",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_TEXT,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK_TEXT,
        spaceBefore=10,
        spaceAfter=4,
        borderPadding=(0, 0, 2, 0),
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=3,
    )
    styles["bold_body"] = ParagraphStyle(
        "bold_body",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=DARK_TEXT,
        leading=14,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=8,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    return styles


# ── Header / Footer drawn on every page ───────────────────────────────────────
def _make_header_footer(canvas, doc, patient_name, dob, record_number, clinic_name, page_label):
    canvas.saveState()
    w, h = letter

    # ── Top green bar ──────────────────────────────────────────────────────────
    bar_h = 24
    canvas.setFillColor(GREEN)
    canvas.rect(0, h - bar_h, w, bar_h, stroke=0, fill=1)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(18, h - 17, "Patient Visit Summary")

    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(w / 2, h - 17, f"{patient_name}  •  DOB: {dob}  •  MRN: {record_number}")

    # ── Bottom green bar ──────────────────────────────────────────────────────
    footer_h = 20
    canvas.setFillColor(GREEN)
    canvas.rect(0, 0, w, footer_h, stroke=0, fill=1)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18, 6, clinic_name)
    canvas.drawRightString(w - 18, 6, page_label.format(doc.page))

    canvas.restoreState()


# ── Section divider helper ────────────────────────────────────────────────────
def _section(story, styles, title, content_paragraphs):
    """Append a labelled section with an underline divider."""
    story.append(Paragraph(title, styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceAfter=4))
    for p in content_paragraphs:
        story.append(p)
    story.append(Spacer(1, 6))


# ── Markdown → ReportLab Paragraph converter ─────────────────────────────────
def _md_inline(text):
    """Convert inline Markdown to ReportLab XML markup."""
    # Escape XML special chars first (except we'll re-add our own tags)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold+italic  ***text***
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold  **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic  *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    # Inline code  `code`
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    return text


def _parse_emr_text(text, styles):
    """
    Full Markdown → list[Paragraph] converter.

    Supported syntax
    ----------------
    # H1  ## H2  ### H3          → section_heading style (smaller per level)
    **bold**  *italic*  `code`   → inline markup
    - item  * item  + item       → bullet list
    1. item  2. item             → numbered list
    ---  ***  ___                → horizontal rule (HRFlowable)
    blank line                   → spacer
    plain paragraph              → body style
    """
    from reportlab.platypus import HRFlowable

    elements = []
    lines = text.split("\n")
    i = 0

    # Heading styles by level
    heading_sizes = {1: 13, 2: 11, 3: 10}

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        i += 1

        # ── Blank line ────────────────────────────────────────────────────────
        if not stripped:
            elements.append(Spacer(1, 4))
            continue

        # ── Horizontal rule  --- / *** / ___ ─────────────────────────────────
        if re.match(r"^[-*_]{3,}$", stripped):
            elements.append(HRFlowable(width="100%", thickness=1,
                                       color=MID_GRAY, spaceAfter=4))
            continue

        # ── ATX Headings  # ## ### ───────────────────────────────────────────
        hm = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if hm:
            level = len(hm.group(1))
            title_text = _md_inline(hm.group(2))
            sz = heading_sizes.get(level, 10)
            h_style = ParagraphStyle(
                f"h{level}",
                fontName="Helvetica-Bold",
                fontSize=sz,
                textColor=DARK_TEXT,
                spaceBefore=8,
                spaceAfter=3,
            )
            elements.append(Paragraph(title_text, h_style))
            elements.append(HRFlowable(width="100%", thickness=0.5,
                                       color=MID_GRAY, spaceAfter=3))
            continue

        # ── Unordered bullet  - / * / + ──────────────────────────────────────
        bm = re.match(r"^[-*+]\s+(.*)", stripped)
        if bm:
            content = _md_inline(bm.group(1))
            bullet_style = ParagraphStyle(
                "bullet",
                parent=styles["body"],
                leftIndent=14,
                firstLineIndent=0,
                bulletIndent=4,
                spaceAfter=2,
            )
            elements.append(Paragraph(f"• {content}", bullet_style))
            continue

        # ── Ordered list  1. 2. ──────────────────────────────────────────────
        nm = re.match(r"^(\d+)[.)]\s+(.*)", stripped)
        if nm:
            num = nm.group(1)
            content = _md_inline(nm.group(2))
            num_style = ParagraphStyle(
                "numbered",
                parent=styles["body"],
                leftIndent=14,
                firstLineIndent=0,
                spaceAfter=2,
            )
            elements.append(Paragraph(f"{num}. {content}", num_style))
            continue

        # ── Plain paragraph (with inline markdown) ────────────────────────────
        content = _md_inline(stripped)
        elements.append(Paragraph(content, styles["body"]))

    return elements


# ── Section keywords to split the LLM blob into named sections ───────────────
SECTION_KEYS = [
    ("Patient Information",        ["patient information", "patient info"]),
    ("Chief Complaint",            ["chief complaint"]),
    ("History of Present Illness", ["history of present illness", "hpi"]),
    ("Symptoms",                   ["symptoms"]),
    ("Duration",                   ["duration"]),
    ("Vital Signs",                ["vital signs", "vitals"]),
    ("Medications",                ["medications mentioned", "medications"]),
    ("Allergies",                  ["allergies"]),
    ("Assessment",                 ["assessment"]),
    ("Plan",                       ["plan"]),
    ("Follow-up Recommendations",  ["follow-up recommendations", "follow-up", "follow up"]),
    ("Discharge Instructions",     ["discharge instructions"]),
]


def _split_into_sections(emr_text):
    """
    Split raw EMR text into ordered dict {section_title: [lines]}.
    Falls back to dumping everything under 'Clinical Notes' if structure absent.
    """
    sections = {title: [] for title, _ in SECTION_KEYS}
    current = "Clinical Notes"
    sections["Clinical Notes"] = []

    for line in emr_text.split("\n"):
        lower = line.lower().strip(" #*:-\n")
        matched = False
        for title, keywords in SECTION_KEYS:
            if any(lower == kw or lower.startswith(kw) for kw in keywords):
                current = title
                matched = True
                break
        if not matched and line.strip():
            sections.setdefault(current, []).append(line)

    return sections


# ── Main PDF builder ──────────────────────────────────────────────────────────
def create_emr_pdf(emr_text, filename="emr_report.pdf",
                   clinic_name="Medical Clinic",
                   clinic_address="123 Health St, Suite 1 | (800) 000-0000"):

    styles = _styles()
    sections = _split_into_sections(emr_text)

    # Strip all Markdown syntax to get plain text
    def _strip_md(text):
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*",     r"\1", text)
        text = re.sub(r"_(.+?)_",       r"\1", text)
        text = re.sub(r"`(.+?)`",       r"\1", text)
        return text.strip(" *_`#-")

    # Pull patient info for header
    patient_lines = sections.get("Patient Information", [])
    def _find(keyword):
        for l in patient_lines:
            if keyword.lower() in l.lower():
                parts = l.split(":", 1)
                return _strip_md(parts[1]) if len(parts) > 1 else ""
        return "—"

    patient_name   = _find("patient name")
    dob            = _find("date of birth")
    record_number  = _find("medical record number")

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.45 * inch,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
    )

    def header_footer(canvas, doc):
        _make_header_footer(canvas, doc, patient_name, dob, record_number,
                            clinic_name, "Page {}")

    story = []

    # ── Clinic info block ─────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(Paragraph(clinic_name, styles["clinic_name"]))
    story.append(Paragraph(clinic_address, styles["clinic_address"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GREEN, spaceAfter=8))

    # ── Patient info table (two-column layout) ────────────────────────────────
    if sections.get("Patient Information"):
        info_items = []
        for line in sections["Patient Information"]:
            if ":" in line:
                parts = line.split(":", 1)
                label = _strip_md(parts[0])
                value = _strip_md(parts[1])
                info_items.append((label, value))

        if info_items:
            # Build a 2-column grid
            row_data = []
            for i in range(0, len(info_items), 2):
                left_label, left_val = info_items[i]
                if i + 1 < len(info_items):
                    right_label, right_val = info_items[i + 1]
                else:
                    right_label, right_val = "", ""
                row_data.append([
                    Paragraph(f"<b>{left_label}:</b>", styles["body"]),
                    Paragraph(left_val, styles["body"]),
                    Paragraph(f"<b>{right_label}:</b>" if right_label else "", styles["body"]),
                    Paragraph(right_val, styles["body"]),
                ])

            col_w = (doc.width) / 4
            t = Table(row_data, colWidths=[col_w * 0.7, col_w * 1.3, col_w * 0.7, col_w * 1.3])
            t.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceAfter=6))

    # ── Remaining sections ────────────────────────────────────────────────────
    skip = {"Patient Information", "Clinical Notes"}
    for title, _ in SECTION_KEYS:
        if title in skip:
            continue
        lines = sections.get(title, [])
        if not lines:
            continue
        paragraphs = _parse_emr_text("\n".join(lines), styles)
        _section(story, styles, title, paragraphs)

    # ── Fallback Clinical Notes ───────────────────────────────────────────────
    if sections.get("Clinical Notes"):
        paragraphs = _parse_emr_text("\n".join(sections["Clinical Notes"]), styles)
        _section(story, styles, "Clinical Notes", paragraphs)

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return filename


# ── Request Body ──────────────────────────────────────────────────────────────
class ConversationRequest(BaseModel):
    conversation: str


# ── Endpoint 1 — FULL EMR DOCUMENT ───────────────────────────────────────────
@app.post("/generate-emr")
def generate_emr(request: ConversationRequest):
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[
            {
                "role": "system",
                "content": "You are a clinical documentation assistant generating professional EMR notes."
            },
            {
                "role": "user",
                "content": f"""
Generate a complete Electronic Medical Record (EMR) summary.
Conversation:
{request.conversation}

Include ALL relevant sections:
- Patient Information (if available)
- Chief Complaint
- History of Present Illness (HPI)
- Symptoms
- Duration
- Vital Signs
- Medications Mentioned
- Allergies (if mentioned)
- Assessment
- Plan
- Follow-up Recommendations
- Discharge Instructions

Use professional clinical language.
Format the output in clean Markdown:
- Use ## for section headings (e.g. ## Chief Complaint)
- Use **label:** value for key-value fields (e.g. **Patient Name:** John Doe)
- Use bullet lists (- item) for symptoms, medications, plan steps, etc.
- Use numbered lists (1. step) for ordered instructions
- Separate major sections with a blank line
"""
            }
        ],
    )
    emr_text = response.model_dump()['choices'][0]['message']['content']
    pdf_path = create_emr_pdf(emr_text)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="EMR_Report.pdf"
    )


# ── Endpoint 2 — STRUCTURED JSON ─────────────────────────────────────────────
@app.post("/generate-json")
def generate_json(request: ConversationRequest):
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[
            {
                "role": "system",
                "content": "You are a medical data extraction assistant."
            },
            {
                "role": "user",
                "content": f"""
Convert this doctor-patient conversation into VALID JSON.
Conversation:
{request.conversation}

Return ONLY valid JSON.
Fields:
- chief_complaint
- symptoms
- duration
- medications
- allergies
- assessment
- plan
- follow_up

Do not include explanations.
Do not include extra text.
"""
            }
        ],
    )
    return {
        "structured_data": response.model_dump()['choices'][0]['message']['content']
    }