from __future__ import annotations

from pathlib import Path
from typing import Optional

from classes.executor_de_operacoes import ExecutorSeguro
from classes.operacao import Operacao, TipoOperacao


class DummyMonitor:
    """
    Monitor "duck-typed": NÃO herda de MonitorDeOperacoes nem implementa Protocol.
    Só tem o método registar com a assinatura esperada.
    """
    def __init__(self) -> None:
        self.mensagens: list[str] = []

    def registar(self, mensagem: str, nivel: str = "INFO", operacao: Optional[Operacao] = None) -> None:
        # guardamos os logs para inspeção
        self.mensagens.append(f"{nivel}:{mensagem}")


def test_i_executorseguro_aceita_monitor_ducktyping_e_logmixin_regista(tmp_path: Path):
    origem = tmp_path / "a.jpg"
    origem.write_bytes(b"X")

    destino = tmp_path / "dest" / "a.jpg"
    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    dummy = DummyMonitor()
    ex = ExecutorSeguro(monitor=dummy)

    # preview para garantir que não mexe no disco e mesmo assim loga
    res = ex.executar([op], modo_preview=True)

    assert res.total == 1
    assert res.movidas == 1
    assert origem.exists()
    assert not destino.exists()

    # Prova de integração: LogMixin usou o contrato MonitorProtocol (duck typing)
    # Esperamos pelo menos o log de preview mover.
    assert any("PREVIEW MOVER:" in m for m in dummy.mensagens)
