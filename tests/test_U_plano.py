from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

import pytest

from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.operacao import TipoOperacao


@dataclass
class DummyFoto:
    caminho: Path
    nome_de_ficheiro: str
    duplicada: bool = False
    data_de_captura: Optional[datetime] = None
    local_gps: Optional[tuple[float, float]] = None


class RegraSpy:
    """Regra falsa que devolve sempre uma pasta fixa e regista chamadas."""
    def __init__(self, pasta_destino: Path):
        self.pasta_destino = pasta_destino
        self.chamadas = []

    def calcular_destino(self, foto, raiz: Path) -> Path:
        self.chamadas.append((foto, raiz))
        return self.pasta_destino


def test_plano_duplica_gera_skip_sem_chamar_regra(tmp_path: Path):
    origem = tmp_path / "a.jpg"
    origem.write_bytes(b"x")

    foto = DummyFoto(caminho=origem, nome_de_ficheiro="a.jpg", duplicada=True)
    regra = RegraSpy(pasta_destino=tmp_path / "IGNORAR")

    plano = PlanoDeOperacoes(regra=regra, raiz_destino=tmp_path / "Fotos Organizadas")
    ops = plano.gerar([foto])

    assert len(ops) == 1
    op = ops[0]
    assert op.tipo == TipoOperacao.SKIP
    assert op.motivo == "Duplicado"
    assert op.origem == origem
    assert op.destino == origem  # como definimos no MVP
    assert regra.chamadas == []  # duplicado não deve calcular destino


def test_plano_ja_no_destino_gera_skip(tmp_path: Path):
    pasta_origem = tmp_path / "Fotos Organizadas" / "2024" / "12" / "31"
    pasta_origem.mkdir(parents=True)

    origem = pasta_origem / "a.jpg"
    origem.write_bytes(b"x")

    foto = DummyFoto(caminho=origem, nome_de_ficheiro="a.jpg")

    # regra devolve exatamente a pasta onde o ficheiro já está
    regra = RegraSpy(pasta_destino=pasta_origem)

    plano = PlanoDeOperacoes(regra=regra, raiz_destino=tmp_path / "Fotos Organizadas")
    ops = plano.gerar([foto])

    assert len(ops) == 1
    op = ops[0]
    assert op.tipo == TipoOperacao.SKIP
    assert op.motivo == "Já está no destino"
    assert op.origem.resolve() == origem.resolve()
    assert op.destino.resolve() == origem.resolve()


def test_plano_normal_gera_mover_com_destino_correto(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"x")

    foto = DummyFoto(caminho=origem, nome_de_ficheiro="a.jpg")

    raiz_destino = tmp_path / "Fotos Organizadas"
    pasta_destino = raiz_destino / "2024" / "12" / "31"

    regra = RegraSpy(pasta_destino=pasta_destino)

    plano = PlanoDeOperacoes(regra=regra, raiz_destino=raiz_destino)
    ops = plano.gerar([foto])

    assert len(ops) == 1
    op = ops[0]
    assert op.tipo == TipoOperacao.MOVER
    assert op.motivo == "OK"
    assert op.origem == origem
    assert op.destino == pasta_destino / "a.jpg"

    # regra foi chamada com a raiz_destino certa
    assert regra.chamadas == [(foto, raiz_destino)]


def test_plano_varias_fotos_mantem_ordem_e_numero(tmp_path: Path):
    raiz_destino = tmp_path / "Fotos Organizadas"
    pasta_destino = raiz_destino / "X"
    regra = RegraSpy(pasta_destino=pasta_destino)

    f1 = tmp_path / "a.jpg"; f1.write_bytes(b"a")
    f2 = tmp_path / "b.jpg"; f2.write_bytes(b"b")

    fotos = [
        DummyFoto(caminho=f1, nome_de_ficheiro="a.jpg"),
        DummyFoto(caminho=f2, nome_de_ficheiro="b.jpg"),
    ]

    plano = PlanoDeOperacoes(regra=regra, raiz_destino=raiz_destino)
    ops = plano.gerar(fotos)

    assert [op.origem for op in ops] == [f1, f2]
    assert [op.destino for op in ops] == [pasta_destino / "a.jpg", pasta_destino / "b.jpg"]
    assert all(op.tipo == TipoOperacao.MOVER for op in ops)
