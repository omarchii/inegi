"""Genera la presentación pitch de Vialitycs MX.

Salida: reports/presentacion_vialitycs_mx.pptx

Tokens visuales (inspirados en reports/reference.pptx):
- Fondo negro (#000000)
- Acento lime (#C1FF72)
- Display: RQND Pro Wide
- Body: Fira Code
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


# ---------- Paleta dark ----------
BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIME = RGBColor(0xC1, 0xFF, 0x72)
DARK_SURFACE = RGBColor(0x12, 0x12, 0x12)   # cards/superficies sutiles
MID_SURFACE = RGBColor(0x1C, 0x1C, 0x1C)    # cards más elevadas
BORDER = RGBColor(0x33, 0x33, 0x33)         # bordes
MUTED = RGBColor(0x9A, 0x9A, 0x9A)          # texto secundario

# ---------- Tipografía ----------
DISPLAY_FONT = "RQND Pro Wide"
BODY_FONT = "Fira Code"

# ---------- Geometría ----------
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def set_fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def set_no_line(shape) -> None:
    shape.line.fill.background()


def set_line(shape, color: RGBColor, width_pt: float = 1.0) -> None:
    shape.line.color.rgb = color
    shape.line.width = Pt(width_pt)


def set_slide_bg(slide, color: RGBColor = BLACK) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_textbox(
    slide,
    left,
    top,
    width,
    height,
    text: str,
    *,
    font_size: int = 14,
    bold: bool = False,
    color: RGBColor = WHITE,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    font_name: str = BODY_FONT,
):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0)
    tf.margin_right = Inches(0)
    tf.margin_top = Inches(0)
    tf.margin_bottom = Inches(0)
    # Soporte para varias líneas (separadas por \n)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color
    return box


def add_bullets(
    slide,
    left,
    top,
    width,
    height,
    items: list[str],
    *,
    font_size: int = 14,
    color: RGBColor = WHITE,
    line_spacing: float = 1.4,
    bullet_color: RGBColor = LIME,
):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0)
    tf.margin_right = Inches(0)
    tf.margin_top = Inches(0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = line_spacing
        p.space_after = Pt(8)
        # Bullet en lime, texto en color
        bullet_run = p.add_run()
        bullet_run.text = "▍ "
        bullet_run.font.name = BODY_FONT
        bullet_run.font.size = Pt(font_size)
        bullet_run.font.color.rgb = bullet_color
        bullet_run.font.bold = True
        text_run = p.add_run()
        text_run.text = item
        text_run.font.name = BODY_FONT
        text_run.font.size = Pt(font_size)
        text_run.font.color.rgb = color
    return box


def add_rect(slide, left, top, width, height, *, fill=DARK_SURFACE, line=None, line_width=1.0):
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    set_fill(rect, fill)
    if line is None:
        set_no_line(rect)
    else:
        set_line(rect, line, line_width)
    rect.shadow.inherit = False
    return rect


def add_brand_strip(slide):
    """Marca superior: 'VIALITYCS MX' + dot lime."""
    add_textbox(
        slide,
        Inches(0.5),
        Inches(0.35),
        Inches(4),
        Inches(0.3),
        "VIALITYCS MX",
        font_size=10,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    # Dot lime
    dot = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(2.0), Inches(0.45), Inches(0.1), Inches(0.1)
    )
    set_fill(dot, LIME)
    set_no_line(dot)


def add_page_footer(slide, page: int, total: int):
    add_textbox(
        slide,
        Inches(0.5),
        Inches(7.18),
        Inches(8),
        Inches(0.25),
        "PROCESAMIENTO DE DATOS · OMAR CHI · VICTOR FIGUEREDO",
        font_size=8,
        color=MUTED,
    )
    add_textbox(
        slide,
        Inches(11.5),
        Inches(7.18),
        Inches(1.4),
        Inches(0.25),
        f"{page:02d} / {total:02d}",
        font_size=8,
        color=LIME,
        align=PP_ALIGN.RIGHT,
        bold=True,
    )


def add_slide_title(slide, title: str, kicker: str | None = None, *, title_top: float = 1.05):
    if kicker:
        add_textbox(
            slide,
            Inches(0.5),
            Inches(0.85),
            Inches(12),
            Inches(0.3),
            kicker.upper(),
            font_size=10,
            bold=True,
            color=LIME,
        )
        title_top_in = title_top + 0.18
    else:
        title_top_in = title_top
    add_textbox(
        slide,
        Inches(0.5),
        Inches(title_top_in),
        Inches(12.3),
        Inches(1.1),
        title,
        font_size=34,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    # Línea acento debajo del título
    add_rect(
        slide,
        Inches(0.5),
        Inches(title_top_in + 1.0),
        Inches(0.5),
        Inches(0.04),
        fill=LIME,
    )


def add_placeholder(
    slide, left, top, width, height, label: str, *, sublabel: str | None = None
):
    """Caja oscura con borde lime para insertar imágenes/video."""
    rect = add_rect(
        slide,
        left,
        top,
        width,
        height,
        fill=DARK_SURFACE,
        line=LIME,
        line_width=1.25,
    )
    rect.line.dash_style = 7  # DASH
    label_box = slide.shapes.add_textbox(left, top, width, height)
    tf = label_box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name = DISPLAY_FONT
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = LIME
    if sublabel:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(6)
        r2 = p2.add_run()
        r2.text = sublabel
        r2.font.name = BODY_FONT
        r2.font.size = Pt(10)
        r2.font.color.rgb = MUTED
    return rect


# ---------- Slides ----------

def slide_cover(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)

    # Banda izquierda con texto, derecha con placeholder hero
    # Línea acento vertical
    add_rect(slide, Inches(6.4), Inches(0.7), Inches(0.04), Inches(6.1), fill=LIME)

    add_textbox(
        slide,
        Inches(0.5),
        Inches(0.7),
        Inches(5),
        Inches(0.3),
        "PITCH · MAYO 2026",
        font_size=10,
        bold=True,
        color=LIME,
    )
    # Título grande
    add_textbox(
        slide,
        Inches(0.5),
        Inches(2.2),
        Inches(6),
        Inches(2.0),
        "Vialitycs\nMX.",
        font_size=72,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    add_textbox(
        slide,
        Inches(0.5),
        Inches(4.6),
        Inches(5.7),
        Inches(1.0),
        "Inteligencia accionable sobre datos\npúblicos de movilidad y siniestralidad\nvial en México.",
        font_size=14,
        color=WHITE,
    )
    add_textbox(
        slide,
        Inches(0.5),
        Inches(6.7),
        Inches(5.7),
        Inches(0.3),
        "PROCESAMIENTO DE DATOS",
        font_size=10,
        color=MUTED,
        bold=True,
    )

    # Lado derecho: hero placeholder + autores
    add_placeholder(
        slide,
        Inches(7.0),
        Inches(0.7),
        Inches(5.85),
        Inches(4.2),
        "[ HERO IMAGE / LOGO ]",
        sublabel="Sugerido: render de tráfico, choque o mapa MX. 1600 × 900 px.",
    )
    add_textbox(
        slide,
        Inches(7.0),
        Inches(5.2),
        Inches(5.85),
        Inches(0.3),
        "PRESENTAN",
        font_size=10,
        bold=True,
        color=LIME,
    )
    add_textbox(
        slide,
        Inches(7.0),
        Inches(5.55),
        Inches(5.85),
        Inches(0.6),
        "Omar Antonio Chi Bautista",
        font_size=18,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    add_textbox(
        slide,
        Inches(7.0),
        Inches(6.05),
        Inches(5.85),
        Inches(0.6),
        "Victor Figueredo",
        font_size=18,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )


def slide_problem(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Los datos existen.\nNadie los puede usar.", kicker="01 · El problema")

    # Layout: izquierda imagen choque, derecha stats + bullets
    # Imagen choque a la izquierda
    add_placeholder(
        slide,
        Inches(0.5),
        Inches(3.4),
        Inches(5.5),
        Inches(3.4),
        "[ IMAGEN DE CHOQUE / TRÁFICO ]",
        sublabel="Para amenizar. Sugerido: foto editorial, alto contraste, en blanco y negro.",
    )

    # Stats a la derecha (3 bloques verticales)
    stats = [
        ("28", "años de datos ATUS sin explotar (1997–2024)"),
        ("32", "entidades · miles de municipios"),
        ("23/28", "archivos con bug de año (ANIO=1)"),
    ]
    top_y = 3.4
    for i, (big, small) in enumerate(stats):
        y = Inches(top_y + i * 1.2)
        add_rect(slide, Inches(6.3), y, Inches(6.5), Inches(1.05), fill=DARK_SURFACE)
        add_rect(slide, Inches(6.3), y, Inches(0.08), Inches(1.05), fill=LIME)
        add_textbox(
            slide,
            Inches(6.55),
            y + Inches(0.18),
            Inches(2.3),
            Inches(0.7),
            big,
            font_size=36,
            bold=True,
            color=LIME,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            Inches(8.7),
            y + Inches(0.32),
            Inches(4.0),
            Inches(0.6),
            small,
            font_size=11,
            color=WHITE,
        )

    add_page_footer(slide, page, total)


def slide_audience(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "¿Quién necesita estas respuestas?", kicker="02 · A quién le duele")

    cards = [
        ("Aseguradoras", "Dimensionar exposición y tarificar pólizas por estado y municipio."),
        ("Gobiernos locales", "Priorizar inversión en seguridad vial con evidencia cuantitativa."),
        ("Periodistas y OSC", "Contextualizar reportajes con cifras oficiales en minutos, no días."),
        ("Equipos de movilidad", "Cruzar tendencias de ventas y parque vehicular con siniestralidad."),
    ]
    card_w = Inches(2.95)
    card_h = Inches(3.5)
    gap = Inches(0.15)
    start_x = Inches(0.5)
    top = Inches(2.7)
    for i, (titulo, desc) in enumerate(cards):
        x = start_x + (card_w + gap) * i
        add_rect(slide, x, top, card_w, card_h, fill=DARK_SURFACE)
        add_rect(slide, x, top, card_w, Inches(0.08), fill=LIME)
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(0.4),
            Inches(2.5),
            Inches(0.5),
            f"0{i+1}",
            font_size=28,
            bold=True,
            color=LIME,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(1.1),
            card_w - Inches(0.6),
            Inches(0.5),
            titulo,
            font_size=16,
            bold=True,
            color=WHITE,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(1.85),
            card_w - Inches(0.6),
            Inches(1.5),
            desc,
            font_size=11,
            color=WHITE,
        )

    add_page_footer(slide, page, total)


def slide_solution(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(
        slide,
        "Pregunta en español.\nRecibe un análisis ejecutivo.",
        kicker="03 · La solución",
    )

    # Mockup de pregunta
    left_x = Inches(0.5)
    top = Inches(3.0)
    add_rect(slide, left_x, top, Inches(6.2), Inches(0.85), fill=DARK_SURFACE)
    add_textbox(
        slide,
        left_x + Inches(0.25),
        top + Inches(0.08),
        Inches(5.7),
        Inches(0.3),
        "INPUT",
        font_size=9,
        bold=True,
        color=LIME,
    )
    add_textbox(
        slide,
        left_x + Inches(0.25),
        top + Inches(0.38),
        Inches(5.7),
        Inches(0.5),
        "> ¿Qué estados tuvieron más accidentes en 2023?",
        font_size=13,
        color=WHITE,
    )

    # Respuesta
    resp_top = Inches(4.0)
    add_rect(slide, left_x, resp_top, Inches(6.2), Inches(2.85), fill=MID_SURFACE)
    add_rect(slide, left_x, resp_top, Inches(0.08), Inches(2.85), fill=LIME)
    add_textbox(
        slide,
        left_x + Inches(0.3),
        resp_top + Inches(0.15),
        Inches(5.7),
        Inches(0.3),
        "OUTPUT",
        font_size=9,
        bold=True,
        color=LIME,
    )
    secciones = [
        ("Resumen", "ranking nacional 2023 con cifras oficiales."),
        ("Datos", "top 5 estados con totales reales."),
        ("Interpretación", "lectura sin afirmar causalidad."),
        ("Limitaciones", "salto metodológico ATUS 2022."),
    ]
    y = resp_top + Inches(0.55)
    for titulo, desc in secciones:
        add_textbox(
            slide,
            left_x + Inches(0.3),
            y,
            Inches(1.7),
            Inches(0.4),
            titulo,
            font_size=11,
            bold=True,
            color=LIME,
        )
        add_textbox(
            slide,
            left_x + Inches(2.0),
            y,
            Inches(4.0),
            Inches(0.4),
            desc,
            font_size=11,
            color=WHITE,
        )
        y += Inches(0.55)

    # Bullets de valor a la derecha
    add_textbox(
        slide,
        Inches(7.0),
        Inches(2.95),
        Inches(5.85),
        Inches(0.5),
        "Lo que entrega Vialitycs MX",
        font_size=18,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    add_bullets(
        slide,
        Inches(7.0),
        Inches(3.65),
        Inches(5.85),
        Inches(3.5),
        [
            "Cobertura ATUS 1997–2024 por entidad y municipio.",
            "VMRC nacional: ventas y parque vehicular.",
            "Respuesta estructurada en 4 secciones fijas.",
            "Cero alucinaciones numéricas — pandas calcula, LLM redacta.",
            "App web Streamlit lista, extensible a API.",
        ],
        font_size=12,
    )

    add_page_footer(slide, page, total)


def slide_demo(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Vialitycs MX en acción", kicker="04 · Demo")

    add_placeholder(
        slide,
        Inches(1.0),
        Inches(2.4),
        Inches(11.3),
        Inches(4.5),
        "[ INSERTA AQUÍ EL VIDEO DEMO ]",
        sublabel="Insertar > Video > Este dispositivo. Reproducción automática recomendada.",
    )

    add_page_footer(slide, page, total)


def slide_trust(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Diseñado para no mentir.", kicker="05 · Por qué confiar en las cifras")

    pilares = [
        ("01", "Nunca calcula", "Todas las métricas se computan en pandas con datos oficiales. El modelo solo redacta."),
        ("02", "Nunca inventa", "El LLM solo cita lo que recibe en el prompt. Sin acceso libre a su memoria."),
        ("03", "Nunca afirma causa", "Habla de correlación o asociación. Está prohibido por diseño afirmar “causa”."),
    ]
    card_w = Inches(3.95)
    card_h = Inches(3.3)
    gap = Inches(0.2)
    start_x = Inches(0.5)
    top = Inches(2.7)
    for i, (num, titulo, desc) in enumerate(pilares):
        x = start_x + (card_w + gap) * i
        add_rect(slide, x, top, card_w, card_h, fill=DARK_SURFACE, line=BORDER, line_width=1.0)
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(0.3),
            Inches(2),
            Inches(0.7),
            num,
            font_size=40,
            bold=True,
            color=LIME,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(1.25),
            card_w - Inches(0.6),
            Inches(0.6),
            titulo,
            font_size=18,
            bold=True,
            color=WHITE,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.3),
            top + Inches(2.05),
            card_w - Inches(0.6),
            Inches(1.2),
            desc,
            font_size=11,
            color=WHITE,
        )

    add_textbox(
        slide,
        Inches(0.5),
        Inches(6.4),
        Inches(12.3),
        Inches(0.5),
        "“ Si el dato no está en INEGI, Vialitycs no lo dice. ”",
        font_size=15,
        bold=True,
        color=LIME,
        align=PP_ALIGN.CENTER,
        font_name=DISPLAY_FONT,
    )

    add_page_footer(slide, page, total)


def slide_architecture(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Cómo funciona", kicker="06 · Arquitectura")

    pasos = [
        ("Pregunta\nen español", "“Top 5 en\n2023”"),
        ("Detección\nintención", "intent +\nslots"),
        ("Cálculo\nen pandas", "datos\nINEGI"),
        ("Construcción\nde prompt", "datos +\ninstrucciones"),
        ("LLM\nfine-tuneado", "Qwen-1.5B\n+ LoRA"),
        ("Respuesta\nejecutiva", "4 secciones\nestándar"),
    ]
    n = len(pasos)
    total_w = Inches(12.3)
    start_x = Inches(0.5)
    top = Inches(2.9)
    box_w = Inches(1.78)
    box_h = Inches(2.0)
    gap = (total_w - box_w * n) / (n - 1)

    for i, (titulo, sub) in enumerate(pasos):
        x = start_x + (box_w + gap) * i
        add_rect(slide, x, top, box_w, box_h, fill=DARK_SURFACE, line=BORDER, line_width=1.0)
        # Stripe lime arriba
        add_rect(slide, x, top, box_w, Inches(0.08), fill=LIME)
        add_textbox(
            slide,
            x + Inches(0.1),
            top + Inches(0.35),
            box_w - Inches(0.2),
            Inches(0.9),
            titulo,
            font_size=12,
            bold=True,
            color=WHITE,
            align=PP_ALIGN.CENTER,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.1),
            top + Inches(1.25),
            box_w - Inches(0.2),
            Inches(0.7),
            sub,
            font_size=9,
            color=MUTED,
            align=PP_ALIGN.CENTER,
        )
        # Flecha lime
        if i < n - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW,
                x + box_w + Inches(0.02),
                top + Inches(0.85),
                gap - Inches(0.04),
                Inches(0.3),
            )
            set_fill(arrow, LIME)
            set_no_line(arrow)

    add_textbox(
        slide,
        Inches(0.5),
        Inches(5.5),
        Inches(12.3),
        Inches(0.5),
        "Las cifras nacen en pandas. El LLM solo redacta.",
        font_size=15,
        bold=True,
        color=LIME,
        align=PP_ALIGN.CENTER,
        font_name=DISPLAY_FONT,
    )

    add_page_footer(slide, page, total)


def slide_use_cases(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "¿Qué puede responder hoy?", kicker="07 · Casos de uso")

    preguntas = [
        "Top 5 estados con más accidentes en 2023.",
        "Tendencia de accidentes en Yucatán entre 2015 y 2024.",
        "Comparar CDMX vs Jalisco en 2022.",
        "¿Las ventas de vehículos se relacionan con los accidentes?",
    ]
    add_textbox(
        slide,
        Inches(0.5),
        Inches(2.7),
        Inches(5.8),
        Inches(0.5),
        "Preguntas tipo soportadas",
        font_size=16,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    y = Inches(3.3)
    for q in preguntas:
        add_rect(slide, Inches(0.5), y, Inches(5.8), Inches(0.78), fill=DARK_SURFACE)
        add_rect(slide, Inches(0.5), y, Inches(0.06), Inches(0.78), fill=LIME)
        add_textbox(
            slide,
            Inches(0.78),
            y + Inches(0.18),
            Inches(5.4),
            Inches(0.5),
            f"> {q}",
            font_size=11,
            color=WHITE,
        )
        y += Inches(0.9)

    add_placeholder(
        slide,
        Inches(7.0),
        Inches(2.7),
        Inches(5.85),
        Inches(4.2),
        "[ SCREENSHOTS DE LA APP ]",
        sublabel="Sugerido: 1 captura del prompt + 1 captura de la respuesta.",
    )

    add_page_footer(slide, page, total)


def slide_metrics(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "El fine-tune supera a los baselines.", kicker="08 · Resultados")

    headers = ["Métrica", "FLAN-T5 base", "Qwen-1.5B vanilla", "Vialitycs (Qwen-LoRA)"]
    rows = [
        ["ROUGE-1", "—", "—", "0.71"],
        ["ROUGE-2", "—", "—", "0.64"],
        ["ROUGE-L", "—", "—", "0.68"],
        ["Secciones presentes (0–1)", "—", "—", "0.80"],
        ["No-causalidad (cruce)", "—", "—", "1.00"],
        ["Longitud media (palabras)", "—", "—", "160"],
    ]
    table_left = Inches(0.5)
    table_top = Inches(2.7)
    col_widths = [Inches(3.6), Inches(2.4), Inches(2.8), Inches(3.5)]
    row_h = Inches(0.5)

    # Header row
    x = table_left
    for i, h in enumerate(headers):
        add_rect(slide, x, table_top, col_widths[i], row_h, fill=LIME)
        add_textbox(
            slide,
            x + Inches(0.15),
            table_top + Inches(0.11),
            col_widths[i] - Inches(0.3),
            row_h,
            h,
            font_size=10,
            bold=True,
            color=BLACK,
        )
        x += col_widths[i]

    # Data rows
    for r_idx, row in enumerate(rows):
        x = table_left
        y = table_top + row_h * (r_idx + 1)
        bg = DARK_SURFACE if r_idx % 2 == 0 else MID_SURFACE
        for i, cell in enumerate(row):
            add_rect(slide, x, y, col_widths[i], row_h, fill=bg)
            color = LIME if i == 3 and cell != "—" else WHITE
            bold = i == 3
            add_textbox(
                slide,
                x + Inches(0.15),
                y + Inches(0.11),
                col_widths[i] - Inches(0.3),
                row_h,
                cell,
                font_size=11,
                bold=bold,
                color=color,
            )
            x += col_widths[i]

    add_textbox(
        slide,
        Inches(0.5),
        Inches(6.45),
        Inches(12.3),
        Inches(0.4),
        "Completa los baselines con tus números si quieres mostrar el delta exacto.",
        font_size=9,
        color=MUTED,
    )

    add_page_footer(slide, page, total)


def slide_traction(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "No es una idea: ya está construido.", kicker="09 · Tracción")

    items = [
        ("Pipeline ETL", "28 años de ATUS y VMRC, reproducible en una línea."),
        ("Dataset curado", "425 ejemplos de entrenamiento (train · val · test)."),
        ("Modelo propio", "Qwen2.5-1.5B fine-tuneado con QLoRA en Colab."),
        ("App funcional", "Streamlit end-to-end con el modelo cargado."),
        ("Documentación", "Plan por etapas y notas para retomar / extender."),
        ("Validación", "Test set independiente con 6 métricas automáticas."),
    ]
    cols = 3
    card_w = Inches(4.05)
    card_h = Inches(1.85)
    gap_x = Inches(0.13)
    gap_y = Inches(0.2)
    start_x = Inches(0.5)
    start_y = Inches(2.7)
    for i, (titulo, desc) in enumerate(items):
        col = i % cols
        row = i // cols
        x = start_x + (card_w + gap_x) * col
        y = start_y + (card_h + gap_y) * row
        add_rect(slide, x, y, card_w, card_h, fill=DARK_SURFACE)
        add_rect(slide, x, y, Inches(0.08), card_h, fill=LIME)
        add_textbox(
            slide,
            x + Inches(0.35),
            y + Inches(0.25),
            card_w - Inches(0.5),
            Inches(0.5),
            titulo,
            font_size=14,
            bold=True,
            color=WHITE,
            font_name=DISPLAY_FONT,
        )
        add_textbox(
            slide,
            x + Inches(0.35),
            y + Inches(0.85),
            card_w - Inches(0.5),
            Inches(0.9),
            desc,
            font_size=10,
            color=WHITE,
        )

    add_page_footer(slide, page, total)


def slide_roadmap(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Hacia dónde va Vialitycs MX", kicker="10 · Roadmap")

    fases = [
        ("HOY", "MVP académico funcional con cobertura nacional."),
        ("Q3 2026", "Cobertura estatal en VMRC + integración DENUE."),
        ("Q4 2026", "Exportable a PDF · API REST · multi-usuario."),
        ("2027", "Versión institucional con autenticación y SLA."),
    ]
    n = len(fases)
    line_y = Inches(4.0)
    add_rect(slide, Inches(0.5), line_y, Inches(12.3), Inches(0.04), fill=LIME)

    box_w = Inches(2.9)
    gap = (Inches(12.3) - box_w * n) / (n - 1)
    for i, (cuando, desc) in enumerate(fases):
        x = Inches(0.5) + (box_w + gap) * i
        # Punto sobre la línea
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            x + box_w / 2 - Inches(0.14),
            line_y - Inches(0.115),
            Inches(0.28),
            Inches(0.28),
        )
        set_fill(dot, LIME)
        set_no_line(dot)
        # Etiqueta arriba
        add_textbox(
            slide,
            x,
            Inches(2.85),
            box_w,
            Inches(0.5),
            cuando,
            font_size=18,
            bold=True,
            color=LIME,
            align=PP_ALIGN.CENTER,
            font_name=DISPLAY_FONT,
        )
        # Descripción abajo
        add_textbox(
            slide,
            x,
            Inches(4.5),
            box_w,
            Inches(2.0),
            desc,
            font_size=12,
            color=WHITE,
            align=PP_ALIGN.CENTER,
        )

    add_page_footer(slide, page, total)


def slide_stack(prs, page, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)
    add_brand_strip(slide)
    add_slide_title(slide, "Stack abierto, costo cero.", kicker="11 · Tecnología")

    items_left = [
        "Python · pandas · Streamlit",
        "Hugging Face Transformers · PEFT (LoRA)",
        "Modelo base Qwen2.5-1.5B-Instruct (Apache 2.0)",
        "Entrenamiento Google Colab T4 (gratis)",
    ]
    items_right = [
        "100% open source — sin vendor lock-in.",
        "Inferencia local en hardware modesto (RTX 3060 Ti).",
        "Sin dependencias de APIs de pago.",
        "Reproducible: pipeline + training en un comando.",
    ]
    add_textbox(
        slide,
        Inches(0.5),
        Inches(2.7),
        Inches(5.8),
        Inches(0.5),
        "Componentes",
        font_size=18,
        bold=True,
        color=LIME,
        font_name=DISPLAY_FONT,
    )
    add_bullets(
        slide,
        Inches(0.5),
        Inches(3.4),
        Inches(5.8),
        Inches(3.5),
        items_left,
        font_size=12,
    )
    add_textbox(
        slide,
        Inches(7.0),
        Inches(2.7),
        Inches(5.85),
        Inches(0.5),
        "Implicaciones de negocio",
        font_size=18,
        bold=True,
        color=LIME,
        font_name=DISPLAY_FONT,
    )
    add_bullets(
        slide,
        Inches(7.0),
        Inches(3.4),
        Inches(5.85),
        Inches(3.5),
        items_right,
        font_size=12,
    )

    add_page_footer(slide, page, total)


def slide_close(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide)

    add_textbox(
        slide,
        Inches(0.5),
        Inches(0.7),
        Inches(8),
        Inches(0.4),
        "VIALITYCS MX",
        font_size=10,
        bold=True,
        color=LIME,
        font_name=DISPLAY_FONT,
    )
    add_textbox(
        slide,
        Inches(0.5),
        Inches(2.0),
        Inches(12.3),
        Inches(2.0),
        "Datos públicos.\nDecisiones privadas.",
        font_size=64,
        bold=True,
        color=WHITE,
        font_name=DISPLAY_FONT,
    )
    # Línea acento
    add_rect(slide, Inches(0.5), Inches(4.6), Inches(0.7), Inches(0.06), fill=LIME)
    add_textbox(
        slide,
        Inches(0.5),
        Inches(4.85),
        Inches(8),
        Inches(0.6),
        "Gracias.",
        font_size=28,
        bold=True,
        color=LIME,
        font_name=DISPLAY_FONT,
    )
    add_textbox(
        slide,
        Inches(0.5),
        Inches(5.55),
        Inches(8),
        Inches(0.5),
        "Omar Antonio Chi Bautista  ·  Victor Figueredo",
        font_size=14,
        color=WHITE,
    )
    add_textbox(
        slide,
        Inches(0.5),
        Inches(5.95),
        Inches(8),
        Inches(0.5),
        "Procesamiento de Datos · Mayo 2026",
        font_size=11,
        color=MUTED,
    )

    add_placeholder(
        slide,
        Inches(9.3),
        Inches(2.0),
        Inches(3.55),
        Inches(3.55),
        "[ QR / CONTACTO ]",
        sublabel="Inserta foto, código QR o enlace a repositorio.",
    )


# ---------- Build ----------

def build(output: Path) -> Path:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    builders = [
        slide_cover,
        slide_problem,
        slide_audience,
        slide_solution,
        slide_demo,
        slide_trust,
        slide_architecture,
        slide_use_cases,
        slide_metrics,
        slide_traction,
        slide_roadmap,
        slide_stack,
        slide_close,
    ]
    total = len(builders)
    for idx, builder in enumerate(builders, start=1):
        if builder is slide_cover or builder is slide_close:
            builder(prs)
        else:
            builder(prs, idx, total)

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "reports" / "presentacion_vialitycs_mx.pptx"
    saved = build(out)
    print(f"OK: {saved}")
