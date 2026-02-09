from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest

from classes.regra_de_organizacao import RegraPorData, RegraPorLocal


# Dummy simples para testar duck typing (não é a classe Foto real)
@dataclass
class DummyFoto:
    nome_de_ficheiro: str
    data_de_captura: Optional[datetime] = None
    local_gps: Optional[tuple[float, float]] = None


def test_regra_por_data_sem_data_usa_semdata(tmp_path: Path):
    regra = RegraPorData()
    foto = DummyFoto("a.jpg", data_de_captura=None)

    destino = regra.calcular_destino(foto, tmp_path)

    assert destino == tmp_path / "SemData"


def test_regra_por_data_com_data_cria_yyyy_mm(tmp_path: Path):
    regra = RegraPorData()
    foto = DummyFoto("a.jpg", data_de_captura=datetime(2024, 12, 31, 10, 0, 0))

    destino = regra.calcular_destino(foto, tmp_path)

    assert destino == tmp_path / "2024" / "12"


def test_regra_por_local_sem_gps_fallback_semlocal(tmp_path: Path):
    regra = RegraPorLocal()
    foto = DummyFoto("a.jpg", local_gps=None)

    destino = regra.calcular_destino(foto, tmp_path)

    # LSP: não rebenta sem GPS, cai em SemLocal
    assert destino == tmp_path / "SemLocal"


def test_regra_por_local_com_gps_cria_bucket_arredondado(tmp_path: Path):
    regra = RegraPorLocal(precision=3)
    foto = DummyFoto("a.jpg", local_gps=(38.722222, -9.138889))

    destino = regra.calcular_destino(foto, tmp_path)

    # precision=3 => 38.722 e -9.139
    assert destino == tmp_path / "GPS_38.722_-9.139"


def test_regra_por_local_precision_muda_bucket(tmp_path: Path):
    foto = DummyFoto("a.jpg", local_gps=(38.722222, -9.138889))

    regra_p3 = RegraPorLocal(precision=3)
    regra_p2 = RegraPorLocal(precision=2)

    destino_p3 = regra_p3.calcular_destino(foto, tmp_path)
    destino_p2 = regra_p2.calcular_destino(foto, tmp_path)

    assert destino_p3 != destino_p2
    assert destino_p2 == tmp_path / "GPS_38.72_-9.14"


def test_regra_por_local_pode_personalizar_prefixo_e_sem_local(tmp_path: Path):
    regra = RegraPorLocal(prefixo="LOCAL", pasta_sem_local="SemGPS", precision=3)

    foto_sem = DummyFoto("a.jpg", local_gps=None)
    assert regra.calcular_destino(foto_sem, tmp_path) == tmp_path / "SemGPS"

    foto_com = DummyFoto("a.jpg", local_gps=(1.23456, 2.34567))
    assert regra.calcular_destino(foto_com, tmp_path) == tmp_path / "LOCAL_1.235_2.346"
