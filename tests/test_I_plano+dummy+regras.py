from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.operacao import TipoOperacao
from classes.regra_de_organizacao import RegraPorData, RegraPorLocal


@dataclass
class DummyFoto:
    caminho: Path
    nome_de_ficheiro: str
    duplicada: bool = False
    data_de_captura: Optional[datetime] = None
    local_gps: Optional[tuple[float, float]] = None


def test_integracao_plano_com_regra_por_data(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"x")

    foto = DummyFoto(
        caminho=origem,
        nome_de_ficheiro="a.jpg",
        data_de_captura=datetime(2024, 12, 31, 10, 0, 0),
    )

    raiz = tmp_path / "Fotos Organizadas"
    regra = RegraPorData()
    plano = PlanoDeOperacoes(regra=regra, raiz_destino=raiz)

    ops = plano.gerar([foto])
    op = ops[0]

    assert op.tipo == TipoOperacao.MOVER
    assert op.destino == raiz / "2024" / "12" / "a.jpg"


def test_integracao_plano_com_regra_por_local(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"x")

    foto = DummyFoto(
        caminho=origem,
        nome_de_ficheiro="a.jpg",
        local_gps=(38.722222, -9.138889),
    )

    raiz = tmp_path / "Fotos Organizadas"
    regra = RegraPorLocal(precision=3)
    plano = PlanoDeOperacoes(regra=regra, raiz_destino=raiz)

    ops = plano.gerar([foto])
    op = ops[0]

    assert op.tipo == TipoOperacao.MOVER
    assert op.destino == raiz / "GPS_38.722_-9.139" / "a.jpg"


def test_integracao_plano_regra_por_local_sem_gps_cai_em_semlocal(tmp_path: Path):
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"x")

    foto = DummyFoto(caminho=origem, nome_de_ficheiro="a.jpg", local_gps=None)

    raiz = tmp_path / "Fotos Organizadas"
    regra = RegraPorLocal()
    plano = PlanoDeOperacoes(regra=regra, raiz_destino=raiz)

    ops = plano.gerar([foto])
    op = ops[0]

    assert op.tipo == TipoOperacao.MOVER
    assert op.destino == raiz / "SemLocal" / "a.jpg"
