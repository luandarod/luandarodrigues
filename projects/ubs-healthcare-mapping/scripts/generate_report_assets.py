"""Generate PNG charts used in the UBS healthcare mapping README."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#fbfaf7",
            "axes.facecolor": "#fbfaf7",
            "axes.edgecolor": "#d6d0c6",
            "axes.labelcolor": "#25211d",
            "xtick.color": "#5d574e",
            "ytick.color": "#25211d",
            "font.family": "DejaVu Sans",
            "font.size": 11,
        }
    )


def finish(ax, title: str, subtitle: str, source: str) -> None:
    ax.set_title(title, loc="left", fontsize=17, fontweight="bold", pad=34, color="#16120f")
    ax.text(0, 1.025, subtitle, transform=ax.transAxes, fontsize=10, color="#655f57")
    ax.text(0, -0.15, source, transform=ax.transAxes, fontsize=9, color="#77716a")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#ddd7ce", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def br_int(value, _position) -> str:
    return f"{int(value):,}".replace(",", ".")


def save_charts(project_dir: Path) -> None:
    base = project_dir / "data" / "enriched"
    out = project_dir / "assets"
    out.mkdir(parents=True, exist_ok=True)

    uf = pd.read_csv(base / "uf_ubs_territory_summary.csv")
    aps = pd.read_csv(base / "uf_ubs_aps_coverage_summary.csv")
    region = pd.read_csv(base / "region_ubs_territory_summary.csv")
    sensitivity_path = base / "priority_sensitivity_uf_scores.csv"
    sensitivity = pd.read_csv(sensitivity_path) if sensitivity_path.exists() else pd.DataFrame()

    uf = uf.merge(
        aps[
            [
                "uf_sigla",
                "aps_populacao",
                "aps_capacidade_equipe",
                "cobertura_aps_ponderada_pct",
                "cobertura_aps_ponderada_capped_pct",
                "coverage_gap_media_pct",
                "aps_priority_score",
            ]
        ],
        on="uf_sigla",
        how="left",
    )
    uf["ubs_per_100k_population"] = uf["ubs_per_10k_population"] * 10

    setup_style()
    colors = ["#1f6f78", "#b35c37", "#6d5dfc", "#2f855a"]

    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=180)
    plot = region.sort_values("ubs_records")
    ax.barh(plot["region"], plot["ubs_records"], color=colors[0], alpha=0.92)
    for y, value, share in zip(plot["region"], plot["ubs_records"], plot["share_pct"]):
        label = f"{value:,.0f}".replace(",", ".") + f" ({share:.1f}%)"
        ax.text(value + 180, y, label, va="center", fontsize=10, color="#3b352f")
    ax.xaxis.set_major_formatter(FuncFormatter(br_int))
    ax.set_xlabel("UBS registradas")
    finish(
        ax,
        "Distribuicao de UBS por regiao",
        "Nordeste e Sudeste concentram a maior parte dos registros nacionais.",
        "Fonte: Cadastro UBS; processamento proprio em Python.",
    )
    fig.tight_layout(pad=2.4)
    fig.savefig(out / "01_ubs_distribution_by_region.png", bbox_inches="tight")
    plt.close(fig)

    plot = pd.concat(
        [uf.nsmallest(7, "ubs_per_100k_population"), uf.nlargest(7, "ubs_per_100k_population")]
    ).drop_duplicates("uf_sigla").sort_values("ubs_per_100k_population")
    fig, ax = plt.subplots(figsize=(10.5, 7), dpi=180)
    bar_colors = ["#b35c37" if x < uf["ubs_per_100k_population"].median() else "#1f6f78" for x in plot["ubs_per_100k_population"]]
    ax.barh(plot["uf_sigla"], plot["ubs_per_100k_population"], color=bar_colors, alpha=0.92)
    ax.axvline(uf["ubs_per_100k_population"].median(), color="#3b352f", linestyle="--", linewidth=1)
    ax.set_xlabel("UBS por 100 mil habitantes")
    finish(
        ax,
        "Disponibilidade relativa muda a leitura",
        "Estados com grande volume absoluto podem cair quando a populacao entra no denominador.",
        "Fonte: Cadastro UBS + IBGE/SIDRA; indicador calculado como UBS/populacao x 100.000.",
    )
    fig.tight_layout(pad=2.4)
    fig.savefig(out / "02_ubs_per_population_extremes.png", bbox_inches="tight")
    plt.close(fig)

    plot = uf.sort_values("cobertura_aps_ponderada_pct")
    fig, ax = plt.subplots(figsize=(10.5, 8), dpi=180)
    ax.barh(plot["uf_sigla"], plot["cobertura_aps_ponderada_pct"], color=colors[3], alpha=0.9, label="Cobertura nominal ponderada")
    ax.scatter(plot["cobertura_aps_ponderada_capped_pct"], plot["uf_sigla"], color="#16120f", s=22, label="Cobertura capada em 100%")
    ax.axvline(100, color="#b35c37", linestyle="--", linewidth=1)
    ax.set_xlabel("Cobertura APS potencial (%)")
    ax.legend(frameon=False, loc="lower right")
    finish(
        ax,
        "Cobertura APS ponderada por populacao",
        "Valores acima de 100% foram preservados como sinal de capacidade nominal, nao como acesso real.",
        "Fonte: Cobertura APS + Cadastro UBS + IBGE/SIDRA; agregacao ponderada por populacao municipal.",
    )
    fig.tight_layout(pad=2.4)
    fig.savefig(out / "03_aps_weighted_coverage_by_uf.png", bbox_inches="tight")
    plt.close(fig)

    plot = uf.nlargest(10, "aps_priority_score").sort_values("aps_priority_score")
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=180)
    ax.barh(plot["uf_sigla"], plot["aps_priority_score"], color=colors[2], alpha=0.9)
    for y, score, gap in zip(plot["uf_sigla"], plot["aps_priority_score"], plot["coverage_gap_media_pct"]):
        ax.text(score + 1, y, f"score {score:.1f} | gap medio {gap:.1f}%", va="center", fontsize=9, color="#3b352f")
    ax.set_xlabel("Score exploratorio de prioridade")
    finish(
        ax,
        "Sinais para investigacao territorial",
        "O score combina baixa disponibilidade relativa, gap de APS e qualidade de coordenadas. Ele nao e ranking de politica publica.",
        "Fonte: indicadores derivados do pipeline; score documentado como triagem exploratoria.",
    )
    fig.tight_layout(pad=2.4)
    fig.savefig(out / "04_priority_screening_top10.png", bbox_inches="tight")
    plt.close(fig)

    if not sensitivity.empty:
        plot = sensitivity.nlargest(10, "score_base").sort_values("score_base")
        fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=180)
        lower = plot["score_base"] - plot[["score_base", "score_coverage_led", "score_territory_led", "score_data_quality_led"]].min(axis=1)
        upper = plot[["score_base", "score_coverage_led", "score_territory_led", "score_data_quality_led"]].max(axis=1) - plot["score_base"]
        ax.barh(plot["uf_sigla"], plot["score_base"], color="#6d5dfc", alpha=0.88)
        ax.errorbar(plot["score_base"], plot["uf_sigla"], xerr=[lower, upper], fmt="none", ecolor="#16120f", elinewidth=1.2, capsize=3)
        ax.set_xlabel("Score base e faixa entre cenarios")
        finish(
            ax,
            "Sensibilidade do score por UF",
            "A barra mostra o score base; a linha mostra como ele muda quando os pesos sao alterados.",
            "Fonte: cenarios base, cobertura, territorio e qualidade cadastral.",
        )
        fig.tight_layout(pad=2.4)
        fig.savefig(out / "05_priority_sensitivity.png", bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate README chart assets.")
    parser.add_argument("--project-dir", default="projects/ubs-healthcare-mapping")
    args = parser.parse_args()
    save_charts(Path(args.project_dir))
    print("Report assets regenerated.")


if __name__ == "__main__":
    main()
