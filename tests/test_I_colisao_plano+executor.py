from datetime import datetime
from pathlib import Path

from classes.executor_de_operacoes import ExecutorSeguro
from classes.foto import Foto
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData


def test_i_plano_executor_colisao_aplica_saferename(tmp_path: Path):
    origem_dir = tmp_path / "DCIM"
    origem_dir.mkdir()

    origem = origem_dir / "a.jpg"
    origem.write_bytes(b"NOVO")

    foto = Foto(origem)
    foto._data_de_captura = datetime(2024, 12, 31, 10, 0, 0)  # noqa: SLF001

    raiz = tmp_path / "Fotos Organizadas"
    destino_original = raiz / "2024" / "12" / "a.jpg"
    destino_original.parent.mkdir(parents=True)
    destino_original.write_bytes(b"EXISTENTE")  # força colisão

    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)
    ops = plano.gerar([foto])

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)
    ex.executar(ops, modo_preview=False)

    # não substitui o existente
    assert destino_original.read_bytes() == b"EXISTENTE"

    # cria o renomeado
    destino_renomeado = destino_original.parent / "a (1).jpg"
    assert destino_renomeado.exists()
    assert destino_renomeado.read_bytes() == b"NOVO"

    msgs = [r.mensagem for r in monitor.obter_registos()]
    assert any("Colisão no destino" in m for m in msgs)
