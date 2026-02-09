from pathlib import Path

from classes.detetar_duplicados import DetetarDuplicados
from classes.foto import Foto
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData
from classes.operacao import TipoOperacao


def test_i_duplicados_afetam_plano(tmp_path: Path):
    origem_dir = tmp_path / "DCIM"
    origem_dir.mkdir()

    a = origem_dir / "a.jpg"
    b = origem_dir / "b.jpg"
    a.write_bytes(b"conteudo_igual")
    b.write_bytes(b"conteudo_igual")

    foto_a = Foto(a)
    foto_b = Foto(b)

    # 1) detetar duplicados (marca a segunda)
    detetor = DetetarDuplicados()
    detetor.detetar([foto_a, foto_b])

    # 2) gerar plano (duplicado deve virar SKIP)
    raiz = tmp_path / "Fotos Organizadas"
    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)

    ops = plano.gerar([foto_a, foto_b])

    assert len(ops) == 2
    assert ops[0].tipo == TipoOperacao.MOVER
    assert ops[1].tipo == TipoOperacao.SKIP
    assert ops[1].motivo == "Duplicado"
