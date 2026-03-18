from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.oxml.ns as nsmap
from lxml import etree

# Allianz brand colors
ALLIANZ_BLUE = RGBColor(0x00, 0x3F, 0x8F)      # Deep blue
ALLIANZ_LIGHT_BLUE = RGBColor(0x00, 0x9E, 0xD9) # Light blue
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
DARK_GRAY = RGBColor(0x40, 0x40, 0x40)
ACCENT_TEAL = RGBColor(0x00, 0xB0, 0xA0)

prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)

def add_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_rect(slide, left, top, width, height, color, transparency=0):
    shape = slide.shapes.add_shape(
        pptx.enum.shapes.MSO_SHAPE_TYPE.AUTO_SHAPE if False else 1,  # rectangle = 1
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    if transparency:
        shape.fill.fore_color.theme_color = None
    return shape

def add_text_box(slide, text, left, top, width, height, font_size=18, bold=False,
                  color=WHITE, align=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    return txBox

def add_bullet_slide(prs, title, bullets, subtitle=None):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    add_background(slide, WHITE)

    # Top blue bar
    add_rect(slide, 0, 0, 13.33, 1.4, ALLIANZ_BLUE)
    # Accent stripe
    add_rect(slide, 0, 1.4, 13.33, 0.07, ALLIANZ_LIGHT_BLUE)

    # Title
    add_text_box(slide, title, 0.4, 0.15, 12.5, 1.1, font_size=32, bold=True, color=WHITE)

    if subtitle:
        add_text_box(slide, subtitle, 0.4, 0.85, 12.5, 0.55, font_size=16, color=ALLIANZ_LIGHT_BLUE)

    # Bullets
    y = 1.75
    for bullet in bullets:
        # Bullet dot
        dot = slide.shapes.add_shape(1, Inches(0.4), Inches(y + 0.08), Inches(0.12), Inches(0.12))
        dot.fill.solid()
        dot.fill.fore_color.rgb = ALLIANZ_LIGHT_BLUE
        dot.line.fill.background()

        add_text_box(slide, bullet, 0.65, y, 12.2, 0.55, font_size=18, color=DARK_GRAY)
        y += 0.65

    # Bottom bar
    add_rect(slide, 0, 7.1, 13.33, 0.4, ALLIANZ_BLUE)
    add_text_box(slide, "Allianz Life Insurance Company of North America  |  Confidential", 0.3, 7.12, 12.5, 0.35,
                 font_size=11, color=WHITE, align=PP_ALIGN.CENTER)

    return slide

# ─── SLIDE 1: Title ───────────────────────────────────────────────────────────
slide_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(slide_layout)
add_background(slide, ALLIANZ_BLUE)

# Large diagonal accent shape
shape = slide.shapes.add_shape(1, Inches(7.5), Inches(0), Inches(6), Inches(7.5))
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0x00, 0x32, 0x75)
shape.line.fill.background()

# Light blue accent bar
add_rect(slide, 0, 5.8, 13.33, 0.08, ALLIANZ_LIGHT_BLUE)

add_text_box(slide, "ALLIANZ ANNUITIES", 0.5, 1.5, 9, 1.2, font_size=46, bold=True, color=WHITE, font_name="Calibri")
add_text_box(slide, "Securing Your Financial Future", 0.5, 2.85, 9, 0.8, font_size=26, color=ALLIANZ_LIGHT_BLUE, font_name="Calibri")
add_text_box(slide, "Comprehensive Solutions for Retirement Income", 0.5, 3.7, 9, 0.6, font_size=18, color=WHITE, font_name="Calibri")
add_text_box(slide, "Allianz Life Insurance Company of North America", 0.5, 6.2, 9, 0.5, font_size=14, color=ALLIANZ_LIGHT_BLUE)

# ─── SLIDE 2: What is an Annuity? ─────────────────────────────────────────────
add_bullet_slide(prs,
    "What Is an Annuity?",
    [
        "A contract between you and an insurance company",
        "You make a lump-sum payment or series of payments",
        "In return, the insurer provides regular disbursements beginning either immediately or at some point in the future",
        "Designed to provide a steady income stream — especially during retirement",
        "Offers tax-deferred growth on earnings until withdrawals begin",
    ]
)

# ─── SLIDE 3: Why Allianz? ────────────────────────────────────────────────────
add_bullet_slide(prs,
    "Why Allianz?",
    subtitle="A Global Leader in Financial Security",
    bullets=[
        "Founded in 1890 — over 130 years of financial strength",
        "One of the world's largest financial services companies (Fortune Global 500)",
        "Consistently rated A+ (Superior) by A.M. Best",
        "Over $700 billion in assets under management globally",
        "#1 seller of fixed index annuities in the United States",
        "Serving more than 85 million retail and corporate customers worldwide",
    ]
)

# ─── SLIDE 4: Types of Annuities ──────────────────────────────────────────────
slide_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(slide_layout)
add_background(slide, WHITE)
add_rect(slide, 0, 0, 13.33, 1.4, ALLIANZ_BLUE)
add_rect(slide, 0, 1.4, 13.33, 0.07, ALLIANZ_LIGHT_BLUE)
add_text_box(slide, "Types of Allianz Annuities", 0.4, 0.15, 12.5, 1.1, font_size=32, bold=True, color=WHITE)

# Three cards
cards = [
    ("Fixed Annuities", ALLIANZ_BLUE, [
        "Guaranteed interest rate",
        "Predictable, stable growth",
        "Protected principal",
        "Ideal for conservative investors",
    ]),
    ("Fixed Index Annuities", ALLIANZ_LIGHT_BLUE, [
        "Linked to market index (e.g. S&P 500)",
        "Upside potential with downside protection",
        "No direct market investment",
        "Allianz's flagship product line",
    ]),
    ("Variable Annuities", ACCENT_TEAL, [
        "Invest in sub-accounts (mutual fund-like)",
        "Higher growth potential",
        "Subject to market risk",
        "Optional riders for protection",
    ]),
]

for i, (title, color, points) in enumerate(cards):
    x = 0.3 + i * 4.35
    card = slide.shapes.add_shape(1, Inches(x), Inches(1.65), Inches(4.1), Inches(5.2))
    card.fill.solid()
    card.fill.fore_color.rgb = color
    card.line.fill.background()

    add_text_box(slide, title, x + 0.1, 1.75, 3.9, 0.65, font_size=19, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    y = 2.6
    for point in points:
        add_text_box(slide, f"• {point}", x + 0.15, y, 3.8, 0.6, font_size=15, color=WHITE)
        y += 0.65

add_rect(slide, 0, 7.1, 13.33, 0.4, ALLIANZ_BLUE)
add_text_box(slide, "Allianz Life Insurance Company of North America  |  Confidential", 0.3, 7.12, 12.5, 0.35,
             font_size=11, color=WHITE, align=PP_ALIGN.CENTER)

# ─── SLIDE 5: Fixed Index Annuities Deep Dive ─────────────────────────────────
add_bullet_slide(prs,
    "Fixed Index Annuities (FIA) — A Closer Look",
    subtitle="Allianz's Most Popular Product Category",
    bullets=[
        "Growth tied to a market index without direct market participation",
        "Floor protection: your principal is never reduced by index losses",
        "Participation rates, caps, and spreads determine credited interest",
        "Tax-deferred accumulation — no annual 1099 on gains until withdrawal",
        "Optional income riders provide guaranteed lifetime withdrawal benefits (GLWB)",
        "Available with single premium or flexible premium payment options",
    ]
)

# ─── SLIDE 6: Key Products ────────────────────────────────────────────────────
add_bullet_slide(prs,
    "Flagship Allianz Products",
    subtitle="Designed for Every Stage of Retirement Planning",
    bullets=[
        "Allianz 222 Annuity — Enhanced benefit base doubling for income & death benefits",
        "Allianz 360 Annuity — Multiple index options with strong accumulation potential",
        "Allianz Benefit Control Annuity — Flexible income and accumulation balance",
        "Allianz Core Income 7 Annuity — Guaranteed income with a 7-year surrender period",
        "Allianz Vision Variable Annuity — Broad investment choices with optional protection",
    ]
)

# ─── SLIDE 7: Income Rider Benefits ──────────────────────────────────────────
add_bullet_slide(prs,
    "Income Riders — Lifetime Income You Can't Outlive",
    bullets=[
        "Guaranteed Lifetime Withdrawal Benefit (GLWB) ensures income regardless of account value",
        "Income base grows at a guaranteed rollup rate (e.g., 7–8% annually during deferral)",
        "Withdrawals can begin as early as age 50 or deferred for higher payouts",
        "Spousal continuation option protects surviving partner's income stream",
        "Remaining account value passes to beneficiaries upon death",
        "Riders available for an additional annual fee (typically 0.95%–1.15%)",
    ]
)

# ─── SLIDE 8: Tax Advantages ──────────────────────────────────────────────────
add_bullet_slide(prs,
    "Tax Advantages of Annuities",
    bullets=[
        "Tax-deferred growth: earnings compound without annual taxation",
        "No contribution limits — unlike IRAs or 401(k)s",
        "Qualified annuities (IRA/403(b)) funded with pre-tax dollars",
        "Non-qualified annuities funded with after-tax dollars; only gains taxed on withdrawal",
        "1035 Exchange: transfer existing annuity or life insurance policy tax-free",
        "Estate planning benefit: annuities pass directly to beneficiaries, often avoiding probate",
    ]
)

# ─── SLIDE 9: Who Should Consider an Annuity? ────────────────────────────────
add_bullet_slide(prs,
    "Who Should Consider an Allianz Annuity?",
    bullets=[
        "Individuals within 5–15 years of retirement seeking to protect savings",
        "Retirees who want guaranteed income to cover essential expenses",
        "Investors concerned about outliving their assets (longevity risk)",
        "Those looking to supplement Social Security or pension income",
        "Conservative savers who want market-linked growth with principal protection",
        "High-income earners seeking additional tax-deferred savings vehicles",
    ]
)

# ─── SLIDE 10: Risks & Considerations ────────────────────────────────────────
add_bullet_slide(prs,
    "Risks & Considerations",
    bullets=[
        "Surrender charges apply if funds are withdrawn early (typically 5–10 years)",
        "10% IRS penalty on withdrawals before age 59½ (qualified accounts)",
        "Caps and participation rates may limit upside during strong bull markets",
        "Rider fees reduce overall accumulation value",
        "Annuities are long-term products — not suitable for short-term savings needs",
        "All guarantees backed by the financial strength of Allianz Life Insurance Co.",
    ]
)

# ─── SLIDE 11: The Allianz Advantage ─────────────────────────────────────────
slide_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(slide_layout)
add_background(slide, ALLIANZ_BLUE)
add_rect(slide, 0, 5.8, 13.33, 0.08, ALLIANZ_LIGHT_BLUE)
add_text_box(slide, "The Allianz Advantage", 0.5, 0.5, 12.3, 1.0, font_size=38, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

stats = [
    ("130+", "Years in Business"),
    ("#1", "FIA Provider in the U.S."),
    ("A+", "A.M. Best Rating"),
    ("$700B+", "Assets Under Management"),
]

for i, (stat, label) in enumerate(stats):
    x = 0.5 + i * 3.1
    box = slide.shapes.add_shape(1, Inches(x), Inches(1.8), Inches(2.8), Inches(2.2))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0x00, 0x32, 0x75)
    box.line.fill.background()
    add_text_box(slide, stat, x + 0.05, 1.95, 2.7, 1.1, font_size=36, bold=True, color=ALLIANZ_LIGHT_BLUE, align=PP_ALIGN.CENTER)
    add_text_box(slide, label, x + 0.05, 3.0, 2.7, 0.7, font_size=14, color=WHITE, align=PP_ALIGN.CENTER)

add_text_box(slide, "Partner with confidence. Retire with certainty.", 0.5, 4.3, 12.3, 0.7,
             font_size=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_text_box(slide, "Contact your Allianz-licensed financial professional to learn more.",
             0.5, 5.1, 12.3, 0.55, font_size=16, color=ALLIANZ_LIGHT_BLUE, align=PP_ALIGN.CENTER)

# ─── SLIDE 12: Disclosures ────────────────────────────────────────────────────
slide_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(slide_layout)
add_background(slide, LIGHT_GRAY)
add_rect(slide, 0, 0, 13.33, 0.9, ALLIANZ_BLUE)
add_text_box(slide, "Important Disclosures", 0.4, 0.05, 12.5, 0.75, font_size=28, bold=True, color=WHITE)

disclosures = (
    "Annuities are long-term financial products designed for retirement purposes. Withdrawals prior to age 59½ may be subject to a 10% "
    "federal tax penalty in addition to ordinary income tax. Surrender charges may apply. Guarantees are backed solely by the financial "
    "strength and claims-paying ability of Allianz Life Insurance Company of North America. Product guarantees do not apply to the "
    "performance of variable sub-accounts.\n\n"
    "Fixed index annuities are not a direct investment in the stock market. They are long-term insurance products with guarantees backed "
    "by the issuing company. Index-linked interest is subject to caps, participation rates, and/or spreads.\n\n"
    "This presentation is for informational purposes only and does not constitute an offer to sell or a solicitation to buy any security "
    "or insurance product. Please read the product prospectus or brochure carefully before investing. Not FDIC insured. Not a bank "
    "deposit. May lose value. Not insured by any federal government agency. Not guaranteed by any bank or savings association.\n\n"
    "Allianz Life Insurance Company of North America  |  5701 Golden Hills Drive, Minneapolis, MN 55416-1297"
)

txBox = slide.shapes.add_textbox(Inches(0.4), Inches(1.1), Inches(12.5), Inches(6.0))
tf = txBox.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
run = p.add_run()
run.text = disclosures
run.font.size = Pt(12)
run.font.color.rgb = DARK_GRAY
run.font.name = "Calibri"

prs.save("/home/user/algooo/allianz_annuities_presentation.pptx")
print("Presentation saved successfully!")
