"""
Testes das funcoes puras de limpeza usadas pelo import de docentes
(sandbox/import_docentes_interesse.py). Nao dependem de planilha real nem de
MongoDB - so das funcoes de parsing/normalizacao.
"""

from __future__ import annotations

import import_docentes_interesse as import_mod

CATALOG = ["Saude", "Educacao", "Tecnologia da informação(TI)"]


def test_normalize_email_remove_espacos_internos_e_baixa_caixa():
    assert import_mod.normalize_email("Luis. Barros@UPE.br") == "luis.barros@upe.br"
    assert import_mod.normalize_email(None) == ""


def test_split_areas_reconhece_valores_do_catalogo():
    known, rejected = import_mod.split_areas("Saude,Educacao", CATALOG)

    assert known == ["Saude", "Educacao"]
    assert rejected == []


def test_split_areas_separa_valor_fora_do_catalogo_em_rejeitadas():
    known, rejected = import_mod.split_areas("Saude,Arqueologia Marinha", CATALOG)

    assert known == ["Saude"]
    assert rejected == ["Arqueologia Marinha"]


def test_split_segmentos_separa_por_virgula_e_remove_duplicatas():
    segmentos = import_mod.split_segmentos("Pesquisa, Extensao, Pesquisa")

    assert segmentos == ["Pesquisa", "Extensao"]


def test_split_segmentos_vazio_devolve_lista_vazia():
    assert import_mod.split_segmentos("") == []
    assert import_mod.split_segmentos(None) == []


def test_build_docentes_nao_grava_area_fora_do_catalogo(tmp_path):
    rows = [
        ("a@upe.br", "Saude,Arqueologia Marinha", "Pesquisa"),
    ]
    path = _write_workbook(tmp_path, rows)

    by_email, stats, report = import_mod.build_docentes(path, CATALOG)

    assert by_email["a@upe.br"]["areas_interesse"] == ["Saude"]
    assert report["areas_rejeitadas"] == {"a@upe.br": ["Arqueologia Marinha"]}


def test_build_docentes_descarta_email_invalido(tmp_path):
    rows = [("nao-e-email", "Saude", "Pesquisa")]
    path = _write_workbook(tmp_path, rows)

    by_email, stats, _report = import_mod.build_docentes(path, CATALOG)

    assert by_email == {}
    assert stats["email_invalido"] == 1


def test_build_docentes_documenta_merge_de_duplicata_divergente(tmp_path):
    rows = [
        ("a@upe.br", "Saude", "Pesquisa"),
        ("a@upe.br", "Educacao", "Extensao"),
    ]
    path = _write_workbook(tmp_path, rows)

    by_email, stats, report = import_mod.build_docentes(path, CATALOG)

    # comportamento atual: duplicata faz UNIAO das areas/segmentos, nao substitui
    assert sorted(by_email["a@upe.br"]["areas_interesse"]) == ["Educacao", "Saude"]
    assert sorted(by_email["a@upe.br"]["segmentos"]) == ["Extensao", "Pesquisa"]
    assert stats["linhas_duplicadas"] == 1
    assert report["duplicatas_divergentes"] == ["a@upe.br"]


def _write_workbook(tmp_path, rows):
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(("email", "areas_interesse", "segmentos"))
    for row in rows:
        sheet.append(row)
    path = tmp_path / "planilha.xlsx"
    workbook.save(path)
    return path
