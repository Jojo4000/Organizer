from pathlib import Path
from classes.executor_de_operacoes import ExecutorSeguro
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.operacao import Operacao, TipoOperacao


def test_i_ordem_logs_colisao_antes_done(tmp_path: Path):
    origem = tmp_path / "a.jpg"
    origem.write_bytes(b"NOVO")

    destino = tmp_path / "dest" / "a.jpg"
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"EXISTENTE")  # colisão

    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)
    ex.executar([op], modo_preview=False)

    msgs = [r.mensagem for r in monitor.obter_registos()]

    i_antes = next(i for i, m in enumerate(msgs) if m.startswith("ANTES MOVER:"))
    i_col = next(i for i, m in enumerate(msgs) if "Colisão no destino" in m)
    i_mover = next(i for i, m in enumerate(msgs) if m.startswith("MOVER:"))

    assert i_antes < i_col < i_mover

    # opcional: confirma que o nome gerado aparece no warning
    assert any("SafeRename -> a (1).jpg" in m for m in msgs)
