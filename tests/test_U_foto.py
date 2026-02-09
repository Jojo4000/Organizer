import os
from datetime import datetime
from types import SimpleNamespace

import pytest

# Ajusta este import conforme o teu projeto.
# Recomendado: garantir que "classes" tem __init__.py e importar assim:
import classes.foto as foto_module
from classes.foto import Foto


class DummyImg:
    """Mock simples para simular Image.open(...) como context manager."""
    def __init__(self, exif):
        self._exif = exif

    def getexif(self):
        return self._exif

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def patch_image_open(monkeypatch, exif_dict):
    """Substitui Image.open(...) por um dummy que devolve o EXIF desejado."""
    monkeypatch.setattr(foto_module.Image, "open", lambda *_args, **_kwargs: DummyImg(exif_dict))


def set_mtime(path, ts: float):
    os.utime(path, (ts, ts))


def approx_dt_equals(dt: datetime, ts: float, tol_seconds: float = 0.001):
    """Compara datetime com timestamp com tolerância pequena."""
    assert dt is not None
    assert abs(dt.timestamp() - ts) <= tol_seconds


def test_extrair_metadados_fallback_para_mtime_sem_exif(tmp_path, monkeypatch):
    # Arrange
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"nao_importa_ser_imagem_real")
    mtime = 1_700_000_000.0
    set_mtime(p, mtime)

    patch_image_open(monkeypatch, exif_dict={})  # sem tags EXIF

    foto = Foto(p)

    # Act
    foto.extrair_metadados()

    # Assert
    approx_dt_equals(foto.data_de_captura, mtime)
    assert foto.local_gps is None


def test_extrair_metadados_usa_exif_datetimeoriginal(tmp_path, monkeypatch):
    # Arrange
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x")
    mtime = 1_600_000_000.0
    set_mtime(p, mtime)

    exif = {36867: "2020:01:02 03:04:05"}  # DateTimeOriginal
    patch_image_open(monkeypatch, exif_dict=exif)

    foto = Foto(p)

    # Act
    foto.extrair_metadados()

    # Assert
    assert foto.data_de_captura == datetime(2020, 1, 2, 3, 4, 5)
    # Confirma que não caiu para mtime
    assert foto.data_de_captura.timestamp() != pytest.approx(mtime)


def test_extrair_metadados_exif_invalido_cai_para_mtime(tmp_path, monkeypatch):
    # Arrange
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x")
    mtime = 1_650_000_000.0
    set_mtime(p, mtime)

    exif = {36867: "data_invalida"}  # DateTimeOriginal inválida
    patch_image_open(monkeypatch, exif_dict=exif)

    foto = Foto(p)

    # Act
    foto.extrair_metadados()

    # Assert
    approx_dt_equals(foto.data_de_captura, mtime)


def test_extrair_metadados_sem_gps_local_gps_none(tmp_path, monkeypatch):
    # Arrange
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x")
    set_mtime(p, 1_700_000_100.0)

    exif = {36867: "2021:05:06 07:08:09"}  # data ok, sem 34853
    patch_image_open(monkeypatch, exif_dict=exif)

    foto = Foto(p)

    # Act
    foto.extrair_metadados()

    # Assert
    assert foto.data_de_captura == datetime(2021, 5, 6, 7, 8, 9)
    assert foto.local_gps is None


def test_extrair_metadados_com_gps_retorna_tuple_lat_lon(tmp_path, monkeypatch):
    # Arrange
    p = tmp_path / "foto.jpg"
    p.write_bytes(b"x")
    set_mtime(p, 1_700_000_200.0)

    # Exemplo: 38° 43' 20" N, 9° 8' 20" W (Lisboa aproximado)
    gps_info = {
        1: "N",
        2: ((38, 1), (43, 1), (20, 1)),
        3: "W",
        4: ((9, 1), (8, 1), (20, 1)),
    }

    exif = {
        36867: "2022:01:01 00:00:00",
        34853: gps_info,  # GPSInfo
    }
    patch_image_open(monkeypatch, exif_dict=exif)

    foto = Foto(p)

    # Act
    foto.extrair_metadados()

    # Assert
    assert foto.local_gps is not None
    assert isinstance(foto.local_gps, tuple)
    lat, lon = foto.local_gps

    # 38 + 43/60 + 20/3600 = 38.722222...
    assert lat == pytest.approx(38.722222, rel=1e-6)
    # 9 + 8/60 + 20/3600 = 9.138888..., mas W => negativo
    assert lon == pytest.approx(-9.138889, rel=1e-6)


def test_calcular_hash_md5_estavel(tmp_path):
    # Arrange
    p = tmp_path / "ficheiro.bin"
    content = b"abc123"
    p.write_bytes(content)

    foto = Foto(p)

    # Act
    foto.calcular_hash("md5")

    # Assert
    import hashlib
    expected = hashlib.md5(content).hexdigest()
    assert foto.hash_conteudo == expected


def test_marcar_como_duplicado_muda_estado(tmp_path):
    p = tmp_path / "x.jpg"
    p.write_bytes(b"x")

    foto = Foto(p)
    assert foto.duplicada is False

    foto.marcar_como_duplicado()
    assert foto.duplicada is True
