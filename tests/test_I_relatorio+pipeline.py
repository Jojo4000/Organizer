from __future__ import annotations

from datetime import datetime
from pathlib import Path

from classes.executor_de_operacoes import ExecutorSeguro
from classes.foto import Foto
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData
from classes.relatorio import Relatorio


def test_i_pipeline_relatorio_execucao_real(tmp_path: Path):
    # Arrange: cria uma "foto" (ficheiro qualquer serve para o move)
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"X")

    foto = Foto(origem)
    # inject data para não depender de EXIF
    foto._data_de_captura = datetime(2024, 12, 31, 10, 0, 0)  # noqa: SLF001

    raiz = tmp_path / "Fotos Organizadas"
    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)
    ops = plano.gerar([foto])

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    # Act
    resultado = ex.executar(ops, modo_preview=False)
    resumo = Relatorio().gerar(
        operacoes=ops,
        resultado=resultado,
        registos=monitor.obter_registos(),
        duplicadas=1 if foto.duplicada else 0,
    )

    # Assert: move real aconteceu
    destino = raiz / "2024" / "12" / "a.jpg"
    assert destino.exists()
    assert not origem.exists()

    # Assert: relatório consistente
    assert resumo.total_operacoes == 1
    assert resumo.movidas == 1
    assert resumo.skipped == 0
    assert resumo.erros == 0

    # distribuição por pasta
    assert resumo.distribuicao_por_pasta[destino.parent] == 1

    # logs existem (MOVER/DONE pelo menos)
    assert resumo.logs_info >= 1


def test_i_pipeline_relatorio_preview_nao_mexe_no_disco(tmp_path: Path):
    # Arrange
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"X")

    foto = Foto(origem)
    foto._data_de_captura = datetime(2024, 12, 31, 10, 0, 0)  # noqa: SLF001

    raiz = tmp_path / "Fotos Organizadas"
    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)
    ops = plano.gerar([foto])

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    # Act: preview
    resultado = ex.executar(ops, modo_preview=True)
    resumo = Relatorio().gerar(
        operacoes=ops,
        resultado=resultado,
        registos=monitor.obter_registos(),
        duplicadas=1 if foto.duplicada else 0,
    )

    # Assert: não mexe no disco
    destino = raiz / "2024" / "12" / "a.jpg"
    assert origem.exists()
    assert not destino.exists()

    # Assert: relatório consistente (preview conta como "movidas" no teu ResultadoExecucao)
    assert resumo.total_operacoes == 1
    assert resumo.movidas == 1
    assert resumo.skipped == 0
    assert resumo.erros == 0

    # logs: deve haver um PREVIEW MOVER
    msgs = [r.mensagem for r in monitor.obter_registos()]
    assert any("PREVIEW MOVER" in m for m in msgs)
