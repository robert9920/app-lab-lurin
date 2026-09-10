from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from errors import AppError


def validate_pdf(content):
    if not content or len(content) > 20 * 1024 * 1024:
        raise AppError(413, "El PDF debe pesar entre 1 byte y 20 MB.")
    if not content.startswith(b"%PDF-"):
        raise AppError(400, "El archivo no es un PDF válido.")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 500:
            raise ValueError("Documento inválido")
        # Reject active actions, attachments and scripts anywhere in the object graph.
        seen = set()

        def inspect(value, depth=0):
            if depth > 100:
                raise ValueError("Estructura excesiva")
            if hasattr(value, "get_object"):
                value = value.get_object()
            if id(value) in seen:
                return
            seen.add(id(value))
            if isinstance(value, dict):
                if any(
                    k in value
                    for k in (
                        "/JavaScript",
                        "/JS",
                        "/OpenAction",
                        "/AA",
                        "/EmbeddedFiles",
                        "/RichMediaContent",
                    )
                ):
                    raise ValueError("Contenido activo")
                if value.get("/S") in ("/Launch", "/JavaScript", "/SubmitForm", "/ImportData", "/GoToR"):
                    raise ValueError("Acción externa")
                for child in value.values():
                    inspect(child, depth + 1)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    inspect(child, depth + 1)

        inspect(reader.trailer)
    except Exception:
        raise AppError(400, "PDF cifrado, dañado o con contenido activo no permitido.") from None


def render(data, kind):
    if kind == "labels":
        return render_labels(data)
    stream = BytesIO()
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12

    def p(value, style="BodyText"):
        return Paragraph(
            escape(str(value if value is not None else "—")).replace("\n", "<br/>"), styles[style]
        )

    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=25, bottomMargin=35)
    logo = Path(__file__).resolve().parents[1] / "data" / "logo.png"
    parts = [Image(str(logo), width=140, height=42, hAlign="LEFT")] if logo.exists() else []
    parts += [
        p("ACTA DE RECEPCIÓN" if kind == "receipt" else "ETIQUETAS DE MUESTRAS", "Heading1"),
        p(data["code"] + " · " + data["project"]["name"]),
        Spacer(1, 12),
    ]
    conditions = {
        "NOT_RECEIVED": "No recibida",
        "OK": "Conforme",
        "OBSERVED": "Observada",
        "DAMAGED": "Dañada",
        "INSUFFICIENT": "Insuficiente",
    }
    from zoneinfo import ZoneInfo

    for s in data["samples"]:
        if not s["received_at"]:
            continue
        parts += [
            p(s["client_code"] + " · " + conditions[s["condition"]], "Heading2"),
            p(
                "Fecha / hora: "
                + s["received_at"].astimezone(ZoneInfo("America/Lima")).strftime("%d/%m/%Y %H:%M")
                + " (Lima)"
            ),
            p("Transporte: " + (s["transport"] or "No indicado")),
            p(
                "Cantidad recibida: "
                + str(s["received_quantity"] if s["received_quantity"] is not None else "No informada")
                + " "
                + s["unit"]
            ),
            p("Observaciones: " + s["reception_notes"]),
            Spacer(1, 10),
        ]
    parts.append(
        p("Estado actual de recepción. Las correcciones se consultan en el historial de la solicitud.")
    )

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(28, 18, "Lara Consulting · Laboratorio Lurín")
        canvas.drawRightString(A4[0] - 28, 18, f"Página {document.page}")

    doc.build(parts, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()


def render_labels(data):
    """Physical dimensions: 95x68 mm, 4 mm gutters, 2 columns x 4 rows on A4."""
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4)
    pdf.setTitle("Etiquetas de muestras · Lara Consulting")
    width, height, gap = 95 * mm, 68 * mm, 4 * mm
    left = (A4[0] - 2 * width - gap) / 2
    top = (A4[1] - 4 * height - 3 * gap) / 2

    def fit(text, x, y, max_width, size=8, font="Helvetica", color="#062a49", right=False):
        text = str(text if text is not None else "—")
        actual = min(size, size * max_width / max(1, stringWidth(text, font, size)))
        pdf.setFillColor(colors.HexColor(color))
        pdf.setFont(font, actual)
        (pdf.drawRightString if right else pdf.drawString)(x, y, text)

    for index, sample in enumerate(data["samples"]):
        if index and index % 8 == 0:
            pdf.showPage()
        row, col = divmod(index % 8, 2)
        x = left + col * (width + gap)
        y = A4[1] - top - (row + 1) * height - row * gap
        pdf.setStrokeColor(colors.HexColor("#64748b"))
        pdf.setLineWidth(0.45)
        pdf.rect(x, y, width, height)
        pad = 3 * mm
        fit("LARA CONSULTING", x + pad, y + height - 5.5 * mm, 46 * mm, color="#b51d2a")
        fit(
            sample["codigo_recepcion"],
            x + width - pad,
            y + height - 5.5 * mm,
            39 * mm,
            color="#b51d2a",
            right=True,
        )
        pdf.setStrokeColor(colors.HexColor("#b51d2a"))
        pdf.line(x + pad, y + height - 8 * mm, x + width - pad, y + height - 8 * mm)
        fit("MUESTRA DE LABORATORIO", x + pad, y + height - 12 * mm, width - 2 * pad, size=7.5)
        code = sample["codigo_laboratorio"]
        size = min(20, 20 * (width - 2 * pad) / max(1, stringWidth(code, "Courier-Bold", 20)))
        pdf.setFont("Courier-Bold", size)
        pdf.drawCentredString(x + width / 2, y + height - 20 * mm, code)
        start = "—" if sample["depth_from"] is None else f"{sample['depth_from']:.2f}"
        end = "—" if sample["depth_to"] is None else f"{sample['depth_to']:.2f}"
        fields = [
            ("Cliente", data["project"]["organization_name"]),
            ("Proyecto", data["project"]["code"]),
            ("ID cliente", sample["client_code"]),
            ("Punto", sample["borehole"] or "—"),
            ("Prof.", f"{start} – {end} m"),
        ]
        for n, (label, value) in enumerate(fields):
            baseline = y + height - (26 + n * 7.6) * mm
            fit(label, x + pad, baseline, 18 * mm, font="Helvetica-Bold")
            # Two wrapped lines at most; shrink very long names within their own row.
            style = getSampleStyleSheet()["BodyText"]
            style.textColor = colors.HexColor("#062a49")
            style.fontSize, style.leading = 8, 9
            paragraph = Paragraph(escape(str(value)), style)
            _, h = paragraph.wrap(70 * mm, 7 * mm)
            while h > 7 * mm and style.fontSize > 4:
                style.fontSize -= 0.25
                style.leading = style.fontSize + 1
                paragraph = Paragraph(escape(str(value)), style)
                _, h = paragraph.wrap(70 * mm, 7 * mm)
            paragraph.drawOn(pdf, x + 22 * mm, baseline + 8 - h)
    pdf.save()
    return stream.getvalue()
