from datetime import datetime
from pathlib import Path

from classes.executor_de_operacoes import ExecutorSeguro
from classes.foto import Foto
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData


def test_i_preview_nao_mexe_no_disco(tmp_path: Path):
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
    ex.executar(ops, modo_preview=True)

    destino = raiz / "2024" / "12" / "31" / "a.jpg"
    assert origem.exists()
    assert not destino.exists()
    # garante que nem criou diretórios
    assert not destino.parent.exists()

    msgs = [r.mensagem for r in monitor.obter_registos()]
    assert any("PREVIEW MOVER" in m for m in msgs)
