from datetime import datetime

from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.operacao import Operacao, TipoOperacao
from pathlib import Path


def test_monitor_registar_adiciona_registo():
    monitor = MonitorDeOperacoes()

    monitor.registar("Olá mundo")

    regs = monitor.obter_registos()
    assert len(regs) == 1
    r = regs[0]
    assert r.mensagem == "Olá mundo"
    assert r.nivel == "INFO"
    assert isinstance(r.instante, datetime)
    assert r.operacao is None


def test_monitor_registar_com_nivel_e_operacao():
    monitor = MonitorDeOperacoes()
    op = Operacao(
        origem=Path("a.jpg"),
        destino=Path("b.jpg"),
        tipo=TipoOperacao.MOVER,
        motivo="OK",
    )

    monitor.registar("A mover", nivel="WARN", operacao=op)

    r = monitor.obter_registos()[0]
    assert r.nivel == "WARN"
    assert r.mensagem == "A mover"
    assert r.operacao == op


def test_monitor_obter_registos_e_imutavel():
    monitor = MonitorDeOperacoes()
    monitor.registar("x")

    regs = monitor.obter_registos()

    # Deve ser sequência imutável (tuple) para evitar alterações externas
    assert isinstance(regs, tuple)

    # tentar modificar deve falhar
    try:
        regs.append("y")  # type: ignore[attr-defined]
        assert False, "tuple não devia ter append"
    except AttributeError:
        assert True


def test_monitor_limpar_remove_todos_os_registos():
    monitor = MonitorDeOperacoes()
    monitor.registar("1")
    monitor.registar("2")

    assert len(monitor.obter_registos()) == 2

    monitor.limpar()

    assert len(monitor.obter_registos()) == 0
