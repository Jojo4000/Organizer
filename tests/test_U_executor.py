from pathlib import Path

from classes.executor_de_operacoes import ExecutorSeguro
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.operacao import Operacao, TipoOperacao


def _mensagens(monitor: MonitorDeOperacoes) -> list[str]:
    return [r.mensagem for r in monitor.obter_registos()]


def test_u_executor_preview_nao_move_mas_regista(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"X")

    destino = tmp_path / "Fotos Organizadas" / "2024" / "12" / "31" / "a.jpg"
    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    res = ex.executar([op], modo_preview=True)

    assert origem.exists()  # não mexe
    assert not destino.exists()
    msgs = _mensagens(monitor)
    assert any("PREVIEW MOVER" in m for m in msgs)

    assert res.total == 1
    assert res.movidas == 1
    assert res.skipped == 0
    assert res.erros == 0


def test_u_executor_move_cria_diretorios_e_move(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"conteudo")

    destino = tmp_path / "Fotos Organizadas" / "2024" / "12" / "31" / "a.jpg"
    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    res = ex.executar([op], modo_preview=False)

    assert not origem.exists()
    assert destino.exists()
    assert destino.read_bytes() == b"conteudo"

    msgs = _mensagens(monitor)
    assert any(m.startswith("MOVER:") for m in msgs)

    assert res.total == 1
    assert res.movidas == 1
    assert res.skipped == 0
    assert res.erros == 0


def test_u_executor_colisao_aplica_saferename(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"NOVO")

    destino = tmp_path / "Fotos Organizadas" / "2024" / "12" / "31" / "a.jpg"
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"EXISTENTE")  # colisão

    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    res = ex.executar([op], modo_preview=False)

    # original destino mantém-se
    assert destino.exists()
    assert destino.read_bytes() == b"EXISTENTE"

    # novo ficheiro vai para "a (1).jpg"
    destino_renomeado = destino.parent / "a (1).jpg"
    assert destino_renomeado.exists()
    assert destino_renomeado.read_bytes() == b"NOVO"
    assert not origem.exists()

    msgs = _mensagens(monitor)
    assert any("Colisão no destino" in m for m in msgs)

    assert res.total == 1
    assert res.movidas == 1
    assert res.skipped == 0
    assert res.erros == 0


def test_u_executor_skip_nao_mexe(tmp_path: Path):
    origem = tmp_path / "a.jpg"
    origem.write_bytes(b"x")

    op = Operacao(origem=origem, destino=origem, tipo=TipoOperacao.SKIP, motivo="Duplicado")

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    res = ex.executar([op], modo_preview=False)

    assert origem.exists()
    msgs = _mensagens(monitor)
    assert any("SKIP: Duplicado" in m for m in msgs)

    assert res.total == 1
    assert res.movidas == 0
    assert res.skipped == 1
    assert res.erros == 0


def test_u_executor_origem_inexistente_vira_skip_warn(tmp_path: Path):
    origem = tmp_path / "nao_existe.jpg"
    destino = tmp_path / "Fotos Organizadas" / "x.jpg"

    op = Operacao(origem=origem, destino=destino, tipo=TipoOperacao.MOVER)

    monitor = MonitorDeOperacoes()
    ex = ExecutorSeguro(monitor=monitor)

    res = ex.executar([op], modo_preview=False)

    assert not destino.exists()
    msgs = _mensagens(monitor)
    assert any("origem não existe" in m for m in msgs)

    assert res.total == 1
    assert res.movidas == 0
    assert res.skipped == 1
    assert res.erros == 0
