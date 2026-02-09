from datetime import datetime
from pathlib import Path

from classes.foto import Foto
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.operacao import TipoOperacao
from classes.regra_de_organizacao import RegraPorData


def test_integracao_plano_com_foto_real_sem_exif(tmp_path: Path):
    # Arrange: cria um ficheiro qualquer (não precisa ser imagem real)
    origem = tmp_path / "DCIM" / "a.jpg"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(b"x")

    foto = Foto(origem)

    # Força data de captura sem mexer em EXIF: definimos diretamente para o teste
    # (isto é aceitável num teste de integração do encaixe Plano+Foto)
    foto._data_de_captura = datetime(2024, 12, 31, 10, 0, 0)  # noqa: SLF001

    raiz = tmp_path / "Fotos Organizadas"
    plano = PlanoDeOperacoes(regra=RegraPorData(), raiz_destino=raiz)

    # Act
    ops = plano.gerar([foto])
    op = ops[0]

    # Assert
    assert op.tipo == TipoOperacao.MOVER
    assert op.origem == origem
    assert op.destino == raiz / "2024" / "12" / "a.jpg"
