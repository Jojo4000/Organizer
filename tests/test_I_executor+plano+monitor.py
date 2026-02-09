from datetime import datetime
from pathlib import Path

from classes.executor_de_operacoes import ExecutorSeguro
from classes.foto import Foto
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData


def test_i_plano_executor_monitor_move_real(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"X")

    foto = Foto(origem)
    # inject data para a regra por data (integração do pipeline, sem depender de EXIF)
    foto._data_de_captura = datetime(2024, 12, 31, 10, 0, 0)  # noqa: SLF001

    raiz = tmp_path / "Fotos Organizadas"

    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)
    ops = plano.gerar([foto])

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)
    res = ex.executar(ops, modo_preview=False)

    destino = raiz / "2024" / "12" / "a.jpg"
    assert destino.exists()
    assert not origem.exists()
    assert res.movidas == 1
    assert res.erros == 0

    # confirma que houve logs
    msgs = [r.mensagem for r in monitor.obter_registos()]
    assert any(m.startswith("MOVER:") for m in msgs)
