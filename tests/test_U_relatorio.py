from __future__ import annotations

from datetime import datetime
from pathlib import Path

from classes.executor_de_operacoes import ResultadoExecucao
from classes.monitor_de_operacoes import Registo
from classes.operacao import Operacao, TipoOperacao
from classes.relatorio import Relatorio


def test_u_relatorio_contagens_basicas(tmp_path: Path):
    ops = [
        Operacao(origem=tmp_path / "a.jpg", destino=tmp_path / "out" / "a.jpg", tipo=TipoOperacao.MOVER),
        Operacao(origem=tmp_path / "b.jpg", destino=tmp_path / "out" / "b.jpg", tipo=TipoOperacao.MOVER),
        Operacao(origem=tmp_path / "c.jpg", destino=tmp_path / "out" / "c.jpg", tipo=TipoOperacao.SKIP, motivo="Duplicado"),
    ]

    res_exec = ResultadoExecucao(total=3, movidas=2, skipped=1, erros=0)

    registos = [
        Registo(instante=datetime.now(), nivel="INFO", mensagem="MOVER...", operacao=ops[0]),
        Registo(instante=datetime.now(), nivel="WARN", mensagem="Colisão...", operacao=ops[1]),
        Registo(instante=datetime.now(), nivel="ERROR", mensagem="ERRO...", operacao=ops[1]),
    ]

    resumo = Relatorio().gerar(operacoes=ops, resultado=res_exec, registos=registos, duplicadas=1)

    assert resumo.total_operacoes == 3
    assert resumo.movidas == 2
    assert resumo.skipped == 1
    assert resumo.erros == 0

    assert resumo.logs_info == 1
    assert resumo.logs_warn == 1
    assert resumo.logs_error == 1

    assert resumo.duplicadas == 1


def test_u_relatorio_skips_por_motivo(tmp_path: Path):
    ops = [
        Operacao(origem=tmp_path / "a.jpg", destino=tmp_path / "x" / "a.jpg", tipo=TipoOperacao.SKIP, motivo="Duplicado"),
        Operacao(origem=tmp_path / "b.jpg", destino=tmp_path / "x" / "b.jpg", tipo=TipoOperacao.SKIP, motivo="Duplicado"),
        Operacao(origem=tmp_path / "c.jpg", destino=tmp_path / "x" / "c.jpg", tipo=TipoOperacao.SKIP, motivo="Origem inválida"),
    ]

    res_exec = ResultadoExecucao(total=3, movidas=0, skipped=3, erros=0)
    resumo = Relatorio().gerar(operacoes=ops, resultado=res_exec, registos=[])

    assert resumo.skips_por_motivo["Duplicado"] == 2
    assert resumo.skips_por_motivo["Origem inválida"] == 1


def test_u_relatorio_distribuicao_por_pasta(tmp_path: Path):
    pasta1 = tmp_path / "Fotos Organizadas" / "2024" / "12" / "31"
    pasta2 = tmp_path / "Fotos Organizadas" / "2025" / "01" / "01"

    ops = [
        Operacao(origem=tmp_path / "a.jpg", destino=pasta1 / "a.jpg", tipo=TipoOperacao.MOVER),
        Operacao(origem=tmp_path / "b.jpg", destino=pasta1 / "b.jpg", tipo=TipoOperacao.MOVER),
        Operacao(origem=tmp_path / "c.jpg", destino=pasta2 / "c.jpg", tipo=TipoOperacao.MOVER),
        Operacao(origem=tmp_path / "d.jpg", destino=pasta2 / "d.jpg", tipo=TipoOperacao.SKIP, motivo="Duplicado"),
    ]

    res_exec = ResultadoExecucao(total=4, movidas=3, skipped=1, erros=0)
    resumo = Relatorio().gerar(operacoes=ops, resultado=res_exec, registos=[])

    assert resumo.distribuicao_por_pasta[pasta1] == 2
    assert resumo.distribuicao_por_pasta[pasta2] == 1
    assert pasta2 in resumo.distribuicao_por_pasta
    # SKIP não entra na distribuição (porque não é mover)
