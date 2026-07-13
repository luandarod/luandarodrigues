"""Build an interpretable municipal decision matrix for telemedicine.

The matrix complements the ranked Phase 2/Phase 4 scores with decision classes
that are easier to defend in a pre-paper or media planning context.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("projects/ubs-healthcare-mapping")


OUTPUT_COLUMNS = [
    "ibge_municipio",
    "ibge_municipio_7",
    "municipio_nome_ibge",
    "uf_sigla",
    "regiao_nome_oficial",
    "populacao_residente",
    "decision_class",
    "decision_label",
    "ads_positioning_tier",
    "recommended_next_action",
    "primary_driver",
    "explanation",
    "telemedicine_phase2_balanced",
    "phase2_rank_balanced",
    "phase2_need_pillar",
    "phase2_spatial_mismatch_score",
    "phase2_feasibility_pillar",
    "digital_readiness_score",
    "households_with_internet_pct",
    "mobile_4g5g_resident_coverage_pct",
    "phase2_spatial_target_rank",
    "phase4_routed_target_rank",
    "phase4_interpretation",
    "evidence_grade",
    "method_notes",
]


LABELS = {
    "pharmacy_assisted_pilot": "Piloto farmácia assistida",
    "pharmacy_assisted_geodesic_candidate": "Candidato farmácia assistida",
    "national_priority_high_readiness": "Prioridade nacional com prontidão",
    "national_priority_inclusion_first": "Prioridade nacional com inclusão digital antes",
    "high_need_digital_inclusion_first": "Alta necessidade, baixa prontidão digital",
    "regional_scale_opportunity": "Oportunidade regional para teste",
    "monitor_or_low_priority": "Monitorar",
    "insufficient_evidence": "Evidência insuficiente",
}


ADS_TIERS = {
    "pharmacy_assisted_pilot": "pilot_with_local_partner",
    "pharmacy_assisted_geodesic_candidate": "validate_route_and_partner",
    "national_priority_high_readiness": "test_digital_ads_now",
    "national_priority_inclusion_first": "test_assisted_or_low_bandwidth_offer",
    "high_need_digital_inclusion_first": "digital_inclusion_first",
    "regional_scale_opportunity": "regional_experiment",
    "monitor_or_low_priority": "monitor",
    "insufficient_evidence": "do_not_target_before_data_fix",
}


NEXT_ACTIONS = {
    "pharmacy_assisted_pilot": "Validar parceiro, privacidade, escala clínica e OSRM local antes de piloto.",
    "pharmacy_assisted_geodesic_candidate": "Roteirizar localmente e confirmar farmácia parceira antes de mídia.",
    "national_priority_high_readiness": "Priorizar teste de mídia agregado por município ou UF com medição de conversão.",
    "national_priority_inclusion_first": "Testar oferta assistida ou baixo consumo de dados antes de campanha puramente digital.",
    "high_need_digital_inclusion_first": "Tratar como território de inclusão digital, não como campanha digital simples.",
    "regional_scale_opportunity": "Usar em experimento regional ou lista ampliada, com controle de robustez.",
    "monitor_or_low_priority": "Manter em monitoramento até nova evidência ou atualização de dados.",
    "insufficient_evidence": "Corrigir ou complementar dados antes de qualquer decisão operacional.",
}


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df.get(column), errors="coerce")


def _nonempty_rank(df: pd.DataFrame, column: str) -> pd.Series:
    return _num(df, column).notna() & _num(df, column).gt(0)


def _primary_driver(row: pd.Series) -> str:
    components = {
        "necessidade": row.get("phase2_need_pillar"),
        "barreira espacial": row.get("phase2_spatial_mismatch_score"),
        "viabilidade": row.get("phase2_feasibility_pillar"),
        "prontidão digital": row.get("digital_readiness_score"),
    }
    numeric = {k: float(v) for k, v in components.items() if pd.notna(v)}
    if not numeric:
        return "dados insuficientes"
    return max(numeric, key=numeric.get)


def _evidence_grade(row: pd.Series) -> str:
    if row.get("phase4_interpretation") == "phase4_primary_routed_target":
        return "B_routed_public_osrm_proxy"
    if pd.notna(row.get("phase2_rank_balanced")):
        return "C_geodesic_municipal_proxy"
    return "D_incomplete"


def _explanation(row: pd.Series) -> str:
    name = row.get("municipio_nome_ibge", "Município")
    uf = row.get("uf_sigla", "")
    label = row.get("decision_label", "classe indefinida")
    driver = row.get("primary_driver", "dados")
    rank = row.get("phase2_rank_balanced")
    rank_text = "sem rank nacional" if pd.isna(rank) else f"rank nacional {int(rank)}"
    return f"{name}/{uf}: {label}; {rank_text}; principal sinal: {driver}."


def build_decision_matrix(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    rank = _num(result, "phase2_rank_balanced")
    digital = _num(result, "digital_readiness_score")
    need = _num(result, "phase2_need_pillar")
    eligible = result["phase2_eligibility"].eq("eligible_phase2_geodesic_proxy") & rank.notna()

    digital_median = float(digital.loc[eligible].median())

    phase4_pilot = result["phase4_interpretation"].eq("phase4_primary_routed_target")
    geodesic_pharmacy = _nonempty_rank(result, "phase2_spatial_target_rank")
    top100 = rank.le(100)
    top500 = rank.le(500)
    high_need = need.ge(75)
    low_readiness = digital.lt(digital_median)
    high_readiness = digital.ge(digital_median)

    result["decision_class"] = "monitor_or_low_priority"
    result.loc[~eligible, "decision_class"] = "insufficient_evidence"
    result.loc[eligible & top500, "decision_class"] = "regional_scale_opportunity"
    result.loc[eligible & high_need & low_readiness, "decision_class"] = "high_need_digital_inclusion_first"
    result.loc[eligible & top100 & low_readiness, "decision_class"] = "national_priority_inclusion_first"
    result.loc[eligible & top100 & high_readiness, "decision_class"] = "national_priority_high_readiness"
    result.loc[eligible & geodesic_pharmacy, "decision_class"] = "pharmacy_assisted_geodesic_candidate"
    result.loc[eligible & phase4_pilot, "decision_class"] = "pharmacy_assisted_pilot"

    result["decision_label"] = result["decision_class"].map(LABELS)
    result["ads_positioning_tier"] = result["decision_class"].map(ADS_TIERS)
    result["recommended_next_action"] = result["decision_class"].map(NEXT_ACTIONS)
    result["primary_driver"] = result.apply(_primary_driver, axis=1)
    result["evidence_grade"] = result.apply(_evidence_grade, axis=1)
    result["method_notes"] = np.where(
        result["decision_class"].eq("pharmacy_assisted_pilot"),
        "Roteamento público OSRM; exige rerodagem local antes de claim acadêmico.",
        "Triagem municipal ecológica; não usar como targeting individual ou prova causal.",
    )
    result["explanation"] = result.apply(_explanation, axis=1)

    return result[OUTPUT_COLUMNS].sort_values(
        ["decision_class", "phase2_rank_balanced"],
        ascending=[True, True],
        na_position="last",
    )


def summarize(matrix: pd.DataFrame) -> dict[str, object]:
    counts = matrix["decision_class"].value_counts().sort_index().to_dict()
    return {
        "rows": int(len(matrix)),
        "decision_class_counts": {str(k): int(v) for k, v in counts.items()},
        "top100_rows": int(_num(matrix, "phase2_rank_balanced").le(100).sum()),
        "phase4_pilot_rows": int(matrix["decision_class"].eq("pharmacy_assisted_pilot").sum()),
        "digital_inclusion_first_rows": int(matrix["decision_class"].str.contains("inclusion_first").sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build municipal telemedicine decision matrix.")
    parser.add_argument("--source", type=Path, default=ROOT / "data/enriched/telemedicine_opportunity_phase4.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/enriched/telemedicine_decision_matrix.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/enriched/telemedicine_decision_matrix_metadata.json")
    args = parser.parse_args()

    matrix = build_decision_matrix(pd.read_csv(args.source, low_memory=False))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(args.output, index=False)
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "matrix_version": "decision-matrix-v1",
        "source": str(args.source),
        "classification_order": [
            "insufficient_evidence",
            "regional_scale_opportunity",
            "high_need_digital_inclusion_first",
            "national_priority_inclusion_first",
            "national_priority_high_readiness",
            "pharmacy_assisted_geodesic_candidate",
            "pharmacy_assisted_pilot",
        ],
        "digital_readiness_threshold": "median among Phase 2 eligible municipalities",
        "important_limits": [
            "Classes are decision-support categories, not clinical access diagnoses.",
            "Ads tiers are for aggregated geographic experiments, not individual targeting.",
            "Pharmacy-assisted classes require partner validation before implementation.",
        ],
        "summary": summarize(matrix),
    }
    args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata["summary"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
