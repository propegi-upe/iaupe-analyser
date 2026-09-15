"""
Testes do coracao do algoritmo de notificacao (pipeline/orchestration/docente_match.py).

match_docentes e normalize_option sao funcoes puras (sem I/O), entao os casos
abaixo nao precisam de mock de MongoDB/SMTP.
"""

from __future__ import annotations

from pipeline.orchestration.docente_match import match_docentes, normalize_option


def test_edital_sem_classificacao_nao_notifica_ninguem():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": ["Pesquisa"]}]

    matches = match_docentes(docentes, areas_edital=[], segmentos_edital=[])

    assert matches == []


def test_docente_casa_por_area_sem_ter_segmento_em_comum():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": ["Extensao"]}]

    matches = match_docentes(docentes, areas_edital=["Saude"], segmentos_edital=["Pesquisa"])

    assert [m.email for m in matches] == ["a@upe.br"]
    assert matches[0].areas == ["Saude"]
    assert matches[0].segmentos == []


def test_docente_casa_por_segmento_sem_ter_area_em_comum():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Educacao"], "segmentos": ["Pesquisa"]}]

    matches = match_docentes(docentes, areas_edital=["Saude"], segmentos_edital=["Pesquisa"])

    assert [m.email for m in matches] == ["a@upe.br"]
    assert matches[0].areas == []
    assert matches[0].segmentos == ["Pesquisa"]


def test_docente_sem_nenhum_overlap_nao_casa():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Educacao"], "segmentos": ["Extensao"]}]

    matches = match_docentes(docentes, areas_edital=["Saude"], segmentos_edital=["Pesquisa"])

    assert matches == []


def test_normalizacao_ignora_espacos_internos_e_caixa():
    docentes = [
        {"email": "a@upe.br", "areas_interesse": ["Tecnologia da informação( TI)"], "segmentos": []}
    ]

    matches = match_docentes(docentes, areas_edital=["Tecnologia da informação(TI)"], segmentos_edital=[])

    assert [m.email for m in matches] == ["a@upe.br"]


def test_normalize_option_remove_espacos_e_baixa_caixa():
    assert normalize_option(" Tecnologia DA Informacao ") == "tecnologiadainformacao"
    assert normalize_option(None) == ""


def test_email_duplicado_mantem_apenas_a_primeira_ocorrencia():
    docentes = [
        {"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": []},
        {"email": "A@UPE.BR", "areas_interesse": ["Educacao"], "segmentos": []},
    ]

    matches = match_docentes(docentes, areas_edital=["Saude", "Educacao"], segmentos_edital=[])

    assert len(matches) == 1
    assert matches[0].areas == ["Saude"]


def test_resultado_ordenado_por_email():
    docentes = [
        {"email": "z@upe.br", "areas_interesse": ["Saude"], "segmentos": []},
        {"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": []},
    ]

    matches = match_docentes(docentes, areas_edital=["Saude"], segmentos_edital=[])

    assert [m.email for m in matches] == ["a@upe.br", "z@upe.br"]
