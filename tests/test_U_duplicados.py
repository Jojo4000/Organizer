from pathlib import Path

from classes.detetar_duplicados import DetetarDuplicados
from classes.foto import Foto


def test_u_duplicados_marca_segunda_como_duplicada(tmp_path: Path):
    # Arrange: dois ficheiros com o mesmo conteúdo
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_bytes(b"conteudo_igual")
    b.write_bytes(b"conteudo_igual")

    foto_a = Foto(a)
    foto_b = Foto(b)

    detetor = DetetarDuplicados(algoritmo="md5")

    # Act
    grupos = detetor.detetar([foto_a, foto_b])

    # Assert
    assert len(grupos) == 1
    assert grupos[0].hash_conteudo is not None
    assert len(grupos[0].fotos) == 2

    # Política MVP: primeira não duplicada, segunda duplicada
    assert foto_a.duplicada is False
    assert foto_b.duplicada is True


def test_u_duplicados_tres_iguais_marca_duas_como_duplicadas(tmp_path: Path):
    p1 = tmp_path / "1.jpg"
    p2 = tmp_path / "2.jpg"
    p3 = tmp_path / "3.jpg"
    content = b"X" * 100

    p1.write_bytes(content)
    p2.write_bytes(content)
    p3.write_bytes(content)

    f1, f2, f3 = Foto(p1), Foto(p2), Foto(p3)

    detetor = DetetarDuplicados()

    grupos = detetor.detetar([f1, f2, f3])

    assert len(grupos) == 1
    assert f1.duplicada is False
    assert f2.duplicada is True
    assert f3.duplicada is True


def test_u_duplicados_conteudos_diferentes_nao_marca(tmp_path: Path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_bytes(b"AAA")
    b.write_bytes(b"BBB")

    fa = Foto(a)
    fb = Foto(b)

    detetor = DetetarDuplicados()
    grupos = detetor.detetar([fa, fb])

    assert grupos == []
    assert fa.duplicada is False
    assert fb.duplicada is False


def test_u_duplicados_ignora_ficheiro_inexistente(tmp_path: Path):
    # Foto aponta para caminho que não existe
    inexistente = tmp_path / "nao_existe.jpg"
    f = Foto(inexistente)

    detetor = DetetarDuplicados()
    grupos = detetor.detetar([f])

    # Não dá hash, logo não forma grupos nem marca duplicado
    assert grupos == []
    assert f.duplicada is False
    assert f.hash_conteudo is None
