"""Generate LinkedIn carousel assets for the UBS healthcare mapping project."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


W, H = 1080, 1350
BG = "#F7F4ED"
INK = "#171717"
MUTED = "#6C6760"
GRID = "#D8D1C5"
TEAL = "#1F7477"
TEAL_DARK = "#155457"
PURPLE = "#6D5DFC"
RUST = "#B96849"
WHITE = "#FFFDF8"

FONT_REG = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_NARROW = "C:/Windows/Fonts/ARIALN.TTF"
FONT_NARROW_BOLD = "C:/Windows/Fonts/ARIALNB.TTF"


def font(size: int, bold: bool = False, narrow: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_NARROW_BOLD if bold and narrow else FONT_NARROW if narrow else FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size=size)


def fmt_int(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], max_width: int, fnt, fill=INK, line_gap=12):
    words = text.split()
    lines = []
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
        y += fnt.size + line_gap
    return y


def line(draw, xy, fill=GRID, width=2):
    draw.line(xy, fill=fill, width=width)


def draw_page_number(draw, n: int):
    draw.text((880, 1238), f"{n:02d}/08", font=font(24, narrow=True), fill=MUTED)
    line(draw, (80, 1250, 850, 1250), fill=GRID, width=2)


def base_slide(n: int):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((42, 42, W - 42, H - 42), outline=GRID, width=2)
    draw_page_number(draw, n)
    return img, draw


def draw_micro_grid(draw, x0=82, y0=145, cols=24, rows=20, step=34, active=None):
    active = active or set()
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * step
            y = y0 + r * step
            color = TEAL if (r, c) in active else GRID
            radius = 2 if (r, c) not in active else 4
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def draw_big_number(draw, value: str, xy, size=142, fill=INK):
    draw.text(xy, value, font=font(size, bold=True, narrow=True), fill=fill)


def draw_bar(draw, x, y, width, height, pct, fill=TEAL, bg="#E7E1D7"):
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=bg)
    draw.rounded_rectangle((x, y, x + max(2, width * pct), y + height), radius=height // 2, fill=fill)


def draw_rank_chart(draw, rows, x=125, y=360, width=760):
    max_score = max(score for _uf, score, _flag in rows)
    flag_map = {"stable": "ESTÁVEL", "moderate": "MODERADO", "sensitive": "SENSÍVEL"}
    for i, (uf, score, flag) in enumerate(rows):
        yy = y + i * 76
        draw.text((x, yy), uf, font=font(42, bold=True, narrow=True), fill=INK)
        draw_bar(draw, x + 90, yy + 10, width, 22, score / max_score, fill=PURPLE, bg="#E2DDD3")
        draw.text((x + 90 + width + 20, yy - 2), f"{score:.1f}", font=font(28, narrow=True), fill=MUTED)
        draw.text((x + 90, yy + 35), flag_map.get(str(flag), str(flag).upper()), font=font(18, narrow=True), fill=MUTED)


def load_metrics(project_dir: Path) -> dict:
    data = project_dir / "data"
    spatial = pd.read_csv(data / "spatial_validation_by_uf.csv")
    op = pd.read_csv(data / "ubs_operational_status_by_uf.csv")
    idx = pd.read_csv(data / "enriched" / "robust_priority_index_uf.csv")
    territory = pd.read_csv(data / "enriched" / "uf_ubs_territory_summary.csv")
    aps = pd.read_csv(data / "enriched" / "uf_ubs_aps_coverage_summary.csv")

    total = int(territory["ubs_records"].sum())
    inside = int(spatial["inside_declared_municipality"].sum())
    outside = int(spatial["outside_declared_municipality"].sum())
    cnes = int(op["cnes_active_proxy"].sum())
    sia = int(op["recent_sia_production"].sum())
    both = int(op["active_with_recent_sia_production"].sum())
    aps_pop = aps["aps_populacao"].sum()
    aps_cap = aps["aps_capacidade_equipe"].sum()
    aps_cov = aps_cap / aps_pop * 100
    top = [(row.uf_sigla, float(row.robust_priority_balanced), row.priority_stability_flag) for row in idx.head(5).itertuples()]
    return {
        "total": total,
        "inside": inside,
        "outside": outside,
        "inside_pct": inside / total * 100,
        "cnes": cnes,
        "cnes_pct": cnes / total * 100,
        "sia": sia,
        "sia_pct": sia / total * 100,
        "both": both,
        "both_pct": both / total * 100,
        "aps_cov": aps_cov,
        "top": top,
    }


def slide_1(m):
    img, d = base_slide(1)
    d.text((80, 92), "PUBLIC DATA / PRIMARY CARE", font=font(24, bold=True, narrow=True), fill=TEAL)
    draw_micro_grid(d, active={(2, 4), (5, 7), (9, 11), (12, 17), (16, 3), (18, 20)})
    d.rectangle((78, 780, 1002, 1035), fill=BG)
    d.text((78, 745), "Onde", font=font(116, bold=True, narrow=True), fill=INK)
    d.text((78, 850), "investigar", font=font(116, bold=True, narrow=True), fill=INK)
    d.text((78, 955), "primeiro?", font=font(116, bold=True, narrow=True), fill=INK)
    draw_wrapped(
        d,
        "A resposta do projeto: priorizar territórios onde estrutura, atividade recente, cobertura e qualidade do dado entram em tensão.",
        (82, 1110),
        820,
        font(30, narrow=True),
        fill=MUTED,
        line_gap=10,
    )
    return img


def slide_2(m):
    img, d = base_slide(2)
    d.text((80, 92), "A PERGUNTA ERRADA", font=font(24, bold=True, narrow=True), fill=TEAL)
    draw_big_number(d, fmt_int(m["total"]), (78, 210), size=176)
    d.text((86, 390), "registros de UBS", font=font(46, bold=True, narrow=True), fill=INK)
    draw_wrapped(
        d,
        "Esse número responde uma parte pequena da história. Ele não diz se o ponto está correto, se houve produção recente ou onde a pressão territorial pesa mais.",
        (86, 500),
        800,
        font(38, narrow=True),
        fill=MUTED,
        line_gap=14,
    )
    for i, label in enumerate(["CADASTRO", "TERRITÓRIO", "APS", "CNES", "SIA"]):
        x = 92 + i * 176
        d.rectangle((x, 815, x + 132, 880), outline=GRID, width=2)
        d.text((x + 18, 834), label, font=font(23, bold=True, narrow=True), fill=TEAL if i else INK)
    line(d, (92, 960, 988, 960), fill=GRID, width=2)
    d.text((92, 990), "a análise vira resposta quando cada camada reduz uma incerteza", font=font(30, narrow=True), fill=MUTED)
    return img


def slide_3(m):
    img, d = base_slide(3)
    d.text((80, 92), "FILTRO 1 / CONFIAR NO MAPA", font=font(24, bold=True, narrow=True), fill=TEAL)
    draw_big_number(d, fmt_pct(m["inside_pct"]), (78, 205), size=168)
    d.text((86, 382), "caem dentro do município declarado", font=font(42, bold=True, narrow=True), fill=INK)
    draw_bar(d, 90, 500, 850, 34, m["inside_pct"] / 100, fill=TEAL)
    d.text((90, 590), f"{fmt_int(m['inside'])} pontos consistentes", font=font(38, bold=True, narrow=True), fill=TEAL_DARK)
    d.text((90, 650), f"{fmt_int(m['outside'])} fora do polígono municipal", font=font(38, bold=True, narrow=True), fill=RUST)
    draw_wrapped(
        d,
        "Resposta prática: antes de ranquear território, eu separo o que parece espacialmente consistente do que precisa de auditoria cadastral.",
        (90, 780),
        820,
        font(34, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    return img


def slide_4(m):
    img, d = base_slide(4)
    d.text((80, 92), "FILTRO 2 / SINAL OPERACIONAL", font=font(24, bold=True, narrow=True), fill=TEAL)
    d.text((90, 205), "CNES/ST", font=font(42, bold=True, narrow=True), fill=INK)
    draw_big_number(d, fmt_pct(m["cnes_pct"]), (90, 260), size=132, fill=INK)
    draw_bar(d, 90, 430, 820, 30, m["cnes_pct"] / 100, fill="#BDB6AA")
    d.text((90, 525), "SIA/PA em 3 competências", font=font(42, bold=True, narrow=True), fill=INK)
    draw_big_number(d, fmt_pct(m["both_pct"]), (90, 580), size=132, fill=TEAL_DARK)
    draw_bar(d, 90, 750, 820, 30, m["both_pct"] / 100, fill=TEAL)
    draw_wrapped(
        d,
        f"{fmt_int(m['both'])} unidades combinam presença cadastral recente com produção ambulatorial registrada. Ainda não é diagnóstico. É um jeito de separar sinal operacional de cadastro puro.",
        (90, 870),
        800,
        font(34, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    return img


def slide_5(m):
    img, d = base_slide(5)
    d.text((80, 92), "FILTRO 3 / COBERTURA NÃO É ACESSO", font=font(24, bold=True, narrow=True), fill=TEAL)
    draw_big_number(d, fmt_pct(m["aps_cov"]), (78, 220), size=166)
    d.text((86, 395), "APS ponderada por população", font=font(42, bold=True, narrow=True), fill=INK)
    for i in range(12):
        x = 92 + i * 70
        top = 800 - int(180 + 90 * math.sin(i / 1.7))
        d.rectangle((x, top, x + 30, 820), fill=TEAL if i > 6 else "#CFC8BB")
    line(d, (90, 820, 960, 820), fill=GRID, width=2)
    draw_wrapped(
        d,
        "A leitura aqui precisa ser cuidadosa. Cobertura potencial ajuda a priorizar, mas não substitui deslocamento, equipe em campo ou qualidade do cuidado.",
        (90, 920),
        790,
        font(34, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    return img


def slide_6(m):
    img, d = base_slide(6)
    d.text((80, 92), "A RESPOSTA OPERACIONAL", font=font(24, bold=True, narrow=True), fill=TEAL)
    d.text((80, 190), "Índice de", font=font(96, bold=True, narrow=True), fill=INK)
    d.text((80, 285), "prioridade", font=font(96, bold=True, narrow=True), fill=INK)
    labels = [
        "UBS / população",
        "gap APS",
        "atividade recente",
        "qualidade espacial",
        "vulnerabilidade territorial",
    ]
    for i, label in enumerate(labels):
        y = 470 + i * 100
        d.ellipse((88, y + 10, 122, y + 44), fill=TEAL if i in (0, 2) else PURPLE if i == 4 else "#CFC8BB")
        d.text((150, y), label, font=font(36, bold=True, narrow=True), fill=INK)
        d.text((150, y + 42), "componente do score", font=font(22, narrow=True), fill=MUTED)
    draw_wrapped(
        d,
        "O índice não aponta culpados. Ele organiza dados públicos incompletos numa fila defensável de investigação.",
        (90, 1035),
        790,
        font(32, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    return img


def slide_7(m):
    img, d = base_slide(7)
    d.text((80, 92), "RESULTADO", font=font(24, bold=True, narrow=True), fill=TEAL)
    d.text((80, 180), "Onde olhar", font=font(76, bold=True, narrow=True), fill=INK)
    d.text((80, 258), "primeiro", font=font(76, bold=True, narrow=True), fill=INK)
    draw_rank_chart(d, m["top"], x=90, y=350, width=600)
    draw_wrapped(
        d,
        "DF, SP e RJ aparecem no topo do cenário balanceado e continuam altos quando os pesos mudam. A resposta publicável é esta: investigar primeiro os sinais mais estáveis, sem vender certeza falsa.",
        (90, 875),
        820,
        font(34, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    return img


def slide_8(m):
    img, d = base_slide(8)
    d.text((80, 92), "CONCLUSÃO", font=font(24, bold=True, narrow=True), fill=TEAL)
    d.text((80, 190), "A resposta", font=font(88, bold=True, narrow=True), fill=INK)
    d.text((80, 280), "é uma fila", font=font(88, bold=True, narrow=True), fill=INK)
    d.text((80, 370), "de auditoria", font=font(88, bold=True, narrow=True), fill=INK)
    items = [
        "equipe ativa por escala",
        "tempo real de deslocamento",
        "qualidade do cuidado",
        "vulnerabilidade social direta",
    ]
    for i, item in enumerate(items):
        y = 555 + i * 90
        d.rectangle((90, y, 126, y + 36), outline=RUST, width=3)
        d.text((160, y - 8), item, font=font(34, bold=True, narrow=True), fill=INK)
    draw_wrapped(
        d,
        "O projeto não prova falta de acesso. Ele entrega uma resposta acionável: onde o dado público recomenda olhar primeiro e quais limites precisam aparecer na mesa.",
        (90, 965),
        820,
        font(34, narrow=True),
        fill=MUTED,
        line_gap=12,
    )
    d.text((90, 1160), "github.com/luandarodrigues/luandarodrigues", font=font(28, bold=True, narrow=True), fill=TEAL_DARK)
    return img


def main():
    project_dir = Path(__file__).resolve().parents[1]
    out = project_dir / "assets" / "social" / "linkedin_ubs_carousel"
    out.mkdir(parents=True, exist_ok=True)
    m = load_metrics(project_dir)
    slides = [slide_1, slide_2, slide_3, slide_4, slide_5, slide_6, slide_7, slide_8]
    images = []
    for i, slide in enumerate(slides, start=1):
        img = slide(m)
        path = out / f"ubs_carousel_{i:02d}.png"
        img.save(path, quality=95)
        images.append(img.convert("RGB"))
    images[0].save(out / "ubs_healthcare_mapping_carousel.pdf", save_all=True, append_images=images[1:])
    print(f"Saved {len(images)} carousel slides to {out}")


if __name__ == "__main__":
    main()
