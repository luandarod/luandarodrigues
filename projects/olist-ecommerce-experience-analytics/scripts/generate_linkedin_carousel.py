"""Generate LinkedIn carousel assets for the Olist e-commerce project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1350
BG = "#F4F1EB"
INK = "#090909"
MUTED = "#6D6860"
LINE = "#D7CEC0"
SAGE = "#6F8F79"
SAGE_DARK = "#3F6F58"
WARM = "#C46A2B"
RUST = "#9C5132"
CARD = "#FFFDF7"

FONT_SERIF = "C:/Windows/Fonts/georgia.ttf"
FONT_SERIF_BOLD = "C:/Windows/Fonts/georgiab.ttf"
FONT_SANS = "C:/Windows/Fonts/arial.ttf"
FONT_SANS_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"
FONT_MONO_BOLD = "C:/Windows/Fonts/consolab.ttf"


def font(size: int, family: str = "sans", bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = {
        ("serif", False): FONT_SERIF,
        ("serif", True): FONT_SERIF_BOLD,
        ("sans", False): FONT_SANS,
        ("sans", True): FONT_SANS_BOLD,
        ("mono", False): FONT_MONO,
        ("mono", True): FONT_MONO_BOLD,
    }
    return ImageFont.truetype(paths[(family, bold)], size=size)


def br_int(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def br_pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}%".replace(".", ",")


def br_money(value: float) -> str:
    return "R$ " + f"{value:,.0f}".replace(",", ".")


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy, max_width: int, fnt, fill=MUTED, gap=12):
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + gap
    return y


def base_slide(n: int):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for x in range(78, W - 78, 72):
        draw.line((x, 70, x, H - 110), fill="#E7DED1", width=1)
    for y in range(118, H - 118, 72):
        draw.line((70, y, W - 70, y), fill="#E7DED1", width=1)
    draw.rectangle((42, 42, W - 42, H - 42), outline=LINE, width=2)
    draw.line((80, 1250, 850, 1250), fill=LINE, width=2)
    draw.text((880, 1235), f"{n:02d}/07", font=font(24, "mono"), fill=MUTED)
    return img, draw


def kicker(draw, text: str):
    draw.text((80, 92), text.upper(), font=font(24, "mono", True), fill=SAGE_DARK)


def big_serif(draw, lines: list[str], y: int, size: int = 92):
    for i, line in enumerate(lines):
        draw.text((78, y + i * int(size * 0.98)), line, font=font(size, "serif"), fill=INK)


def stat_box(draw, x, y, value, label, width=280):
    draw.line((x, y, x + width, y), fill=LINE, width=2)
    draw.text((x, y + 24), value, font=font(40, "mono", True), fill=INK)
    draw_wrapped(draw, label, (x, y + 82), width, font(24, "sans"), fill=MUTED, gap=8)


def bar(draw, x, y, width, value, max_value, color=SAGE_DARK, label="", suffix="", digits=1):
    draw.rounded_rectangle((x, y, x + width, y + 26), radius=13, fill="#DED6CA")
    fill_width = max(6, int(width * value / max_value))
    draw.rounded_rectangle((x, y, x + fill_width, y + 26), radius=13, fill=color)
    if label:
        draw.text((x, y - 38), label, font=font(24, "mono", True), fill=INK)
    draw.text((x + width + 20, y - 5), f"{value:.{digits}f}{suffix}".replace(".", ","), font=font(24, "mono"), fill=MUTED)


def load_metrics(project_dir: Path) -> dict:
    data = project_dir / "data"
    executive = pd.read_csv(data / "executive_summary.csv").iloc[0]
    state = pd.read_csv(data / "same_state_vs_cross_state_delivery.csv")
    features = pd.read_csv(data / "feature_importance.csv")
    categories = pd.read_csv(data / "top_categories_summary.csv")
    models = pd.read_csv(data / "model_metrics.csv")

    same = state[state["same_state"].astype(str) == "True"].iloc[0]
    cross = state[state["same_state"].astype(str) == "False"].iloc[0]
    return {
        "orders": executive["orders"],
        "gmv": executive["total_gmv"],
        "avg_review": executive["avg_review"],
        "low_review_rate": executive["low_review_rate_pct"],
        "delay_rate": executive["delay_rate_pct"],
        "avg_delivery": executive["avg_delivery_days"],
        "same_days": same["avg_delivery_days"],
        "cross_days": cross["avg_delivery_days"],
        "same_freight": same["avg_freight"],
        "cross_freight": cross["avg_freight"],
        "same_delay": same["delay_rate_pct"],
        "cross_delay": cross["delay_rate_pct"],
        "features": features.head(6),
        "categories": categories.sort_values("low_review_rate", ascending=False).head(5),
        "rf": models[models["model"] == "Random Forest"].iloc[0],
    }


def slide_1(m):
    img, d = base_slide(1)
    kicker(d, "Marketplace operations")
    big_serif(d, ["Quando a", "entrega vira", "review ruim"], 210, 96)
    draw_wrapped(
        d,
        "Peguei 99.441 pedidos da Olist para olhar uma coisa simples: em que ponto a entrega começa a azedar o review?",
        (84, 690),
        820,
        font(34, "sans"),
        fill=MUTED,
        gap=12,
    )
    stat_box(d, 84, 885, br_int(m["orders"]), "pedidos analisados")
    stat_box(d, 400, 885, br_pct(m["low_review_rate"]), "reviews com nota baixa")
    stat_box(d, 710, 885, br_pct(m["delay_rate"]), "entregas em atraso")
    return img


def slide_2(m):
    img, d = base_slide(2)
    kicker(d, "A pergunta")
    big_serif(d, ["A média", "esconde o", "problema"], 205, 94)
    d.text((84, 595), "4,09", font=font(128, "mono", True), fill=INK)
    d.text((88, 735), "nota média parece saudável", font=font(34, "sans", True), fill=INK)
    draw_wrapped(
        d,
        "Só que média alisa o problema. O incômodo aparece quando o pedido atrasa, cruza estado, pesa no frete e chega com cara de experiência ruim.",
        (88, 815),
        820,
        font(34, "sans"),
        fill=MUTED,
        gap=12,
    )
    return img


def slide_3(m):
    img, d = base_slide(3)
    kicker(d, "O sinal operacional")
    big_serif(d, ["A distância", "aparece", "na conta"], 180, 92)
    d.text((95, 590), "Mesmo estado", font=font(28, "mono", True), fill=INK)
    same_value = f"{m['same_days']:.1f}".replace(".", ",")
    d.text((95, 638), same_value, font=font(92, "mono", True), fill=SAGE_DARK)
    d.text((95 + int(d.textlength(same_value, font=font(92, "mono", True))) + 26, 668), "dias", font=font(32, "sans"), fill=MUTED)
    d.text((95, 760), "Estados diferentes", font=font(28, "mono", True), fill=INK)
    cross_value = f"{m['cross_days']:.1f}".replace(".", ",")
    d.text((95, 808), cross_value, font=font(92, "mono", True), fill=RUST)
    d.text((95 + int(d.textlength(cross_value, font=font(92, "mono", True))) + 26, 838), "dias", font=font(32, "sans"), fill=MUTED)
    draw_wrapped(
        d,
        f"No mesmo estado, o frete médio fica em {br_money(m['same_freight'])}. Entre estados, sobe para {br_money(m['cross_freight'])}.",
        (95, 965),
        800,
        font(32, "sans"),
        fill=MUTED,
        gap=12,
    )
    return img


def slide_4(m):
    img, d = base_slide(4)
    kicker(d, "O modelo confirma")
    big_serif(d, ["O atraso", "aparece", "primeiro"], 165, 96)
    features = list(m["features"].itertuples())
    max_value = max(row.importance for row in features)
    labels = {
        "delay_days": "atraso",
        "delivery_days": "tempo total",
        "items_count": "itens",
        "freight": "frete",
        "product_category_name_english": "categoria",
        "customer_state": "estado cliente",
    }
    for i, row in enumerate(features):
        y = 585 + i * 82
        label = labels.get(row.feature, row.feature)
        bar(d, 95, y, 590, row.importance, max_value, color=SAGE_DARK if i < 2 else WARM, label=label, digits=2)
    draw_wrapped(
        d,
        "Não usei o modelo para decidir pelo cliente. Usei para ver quais sinais aparecem antes da nota baixa.",
        (95, 1100),
        800,
        font(30, "sans"),
        fill=MUTED,
        gap=10,
    )
    return img


def slide_5(m):
    img, d = base_slide(5)
    kicker(d, "Categorias sob pressão")
    big_serif(d, ["Volume alto", "também pode", "carregar atrito"], 155, 86)
    categories = list(m["categories"].itertuples())
    max_rate = max(row.low_review_rate for row in categories)
    names = {
        "furniture_decor": "furniture decor",
        "bed_bath_table": "bed bath table",
        "computers_accessories": "computers",
        "watches_gifts": "watches gifts",
        "garden_tools": "garden tools",
    }
    for i, row in enumerate(categories):
        y = 575 + i * 92
        label = names.get(row.product_category_name_english, row.product_category_name_english)
        bar(d, 95, y, 560, row.low_review_rate * 100, max_rate * 100, color=RUST, label=label, suffix="%")
    draw_wrapped(
        d,
        "Aqui tem uma fila de atenção: categoria com volume alto, expectativa difícil e mais chance de nota baixa.",
        (95, 1075),
        820,
        font(30, "sans"),
        fill=MUTED,
        gap=10,
    )
    return img


def slide_6(m):
    img, d = base_slide(6)
    kicker(d, "Resposta prática")
    big_serif(d, ["O modelo", "não é o", "começo"], 160, 88)
    items = [
        ("01", "ver atraso antes da reclamação"),
        ("02", "separar entregas interestaduais"),
        ("03", "olhar categorias que acumulam atrito"),
        ("04", "criar scorecards de seller"),
    ]
    for i, (num, text) in enumerate(items):
        y = 575 + i * 112
        d.text((92, y), num, font=font(26, "mono", True), fill=SAGE_DARK)
        d.line((150, y + 18, 900, y + 18), fill=LINE, width=2)
        d.text((150, y + 42), text, font=font(34, "sans", True), fill=INK)
    return img


def slide_7(m):
    img, d = base_slide(7)
    kicker(d, "Conclusão")
    big_serif(d, ["A resposta", "passa pela", "logística"], 170, 94)
    draw_wrapped(
        d,
        "O projeto não tenta reduzir o cliente a um score. Ele mostra onde a operação deixa marcas: atraso, distância, frete, categoria e complexidade do pedido.",
        (90, 590),
        820,
        font(36, "sans"),
        fill=MUTED,
        gap=14,
    )
    d.text((90, 890), "Random Forest", font=font(28, "mono", True), fill=INK)
    d.text((90, 945), f"ROC-AUC {m['rf'].roc_auc:.3f}".replace(".", ","), font=font(60, "mono", True), fill=SAGE_DARK)
    draw_wrapped(
        d,
        "O score ajuda, mas não manda. A leitura boa é encontrar risco operacional antes que ele vire insatisfação.",
        (90, 1040),
        820,
        font(30, "sans"),
        fill=MUTED,
        gap=10,
    )
    return img


def main():
    project_dir = Path(__file__).resolve().parents[1]
    out = project_dir / "assets" / "social" / "linkedin_olist_carousel"
    out.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics(project_dir)
    slides = [slide_1, slide_2, slide_3, slide_4, slide_5, slide_6, slide_7]
    images = []
    for index, slide in enumerate(slides, start=1):
        image = slide(metrics)
        image.save(out / f"olist_carousel_{index:02d}.png", quality=95)
        images.append(image.convert("RGB"))
    images[0].save(out / "olist_delivery_experience_carousel.pdf", save_all=True, append_images=images[1:])
    print(f"Saved {len(images)} slides to {out}")


if __name__ == "__main__":
    main()
