from __future__ import annotations

import os
import time
from pathlib import Path

from PIL import Image, ImageDraw

from classes.detetar_duplicados import DetetarDuplicados
from classes.foto import Foto


def _criar_imagem_base(destino: Path, quality: int) -> None:
    img = Image.new("RGB", (128, 128), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 108, 108], outline="black", width=5)
    draw.line([0, 0, 127, 127], fill="black", width=3)
    img.save(destino, format="JPEG", quality=quality)


def _criar_imagem_diferente(destino: Path, quality: int) -> None:
    img = Image.new("RGB", (128, 128), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 120, 120], outline="black", width=5)  # deslocado
    draw.line([127, 0, 0, 127], fill="black", width=3)            # outra diagonal
    img.save(destino, format="JPEG", quality=quality)


def test_u_quase_duplicados_phash_marca_e_mantem_mais_antiga(tmp_path: Path):
    p1 = tmp_path / "a1.jpg"
    p2 = tmp_path / "a2.jpg"

    _criar_imagem_base(p1, quality=95)
    _criar_imagem_base(p2, quality=30)  # bytes diferentes, aparência igual

    # Forçar "antiguidade": p1 mais antigo
    old = time.time() - 86400
    now = time.time()
    os.utime(p1, (old, old))
    os.utime(p2, (now, now))

    f1 = Foto(p1); f1.extrair_metadados()
    f2 = Foto(p2); f2.extrair_metadados()

    det = DetetarDuplicados()
    marcadas = det.marcar_quase_duplicados([f1, f2], threshold=2)

    assert marcadas == 1
    assert f1.duplicada is False
    assert f2.duplicada is True


def test_u_quase_duplicados_nao_marca_imagens_diferentes(tmp_path: Path):
    p1 = tmp_path / "base.jpg"
    p2 = tmp_path / "diff.jpg"

    _criar_imagem_base(p1, quality=90)
    _criar_imagem_diferente(p2, quality=90)

    f1 = Foto(p1); f1.extrair_metadados()
    f2 = Foto(p2); f2.extrair_metadados()

    det = DetetarDuplicados()
    marcadas = det.marcar_quase_duplicados([f1, f2], threshold=2)

    assert marcadas == 0
    assert f1.duplicada is False
    assert f2.duplicada is False
