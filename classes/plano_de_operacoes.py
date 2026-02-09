from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from classes.operacao import Operacao, TipoOperacao
from classes.regra_de_organizacao import RegraDeOrganizacao, FotoProtocol


@dataclass
class PlanoDeOperacoes:
    """
    Gera um plano (lista de Operacao) a partir de:
      - uma RegraDeOrganizacao (estratégia)
      - uma coleção de fotos

    IMPORTANTÍSSIMO:
      - Não toca no disco (não cria pastas, não move ficheiros)
      - Serve para preview/dry-run
    """
    regra: RegraDeOrganizacao
    raiz_destino: Path

    def gerar(self, fotos: Iterable[FotoProtocol]) -> List[Operacao]:
        operacoes: List[Operacao] = []

        for foto in fotos:
            origem = Path(foto.caminho) if hasattr(foto, "caminho") else None

            # Se não conseguirmos obter o caminho de origem, não conseguimos planear
            if origem is None:
                operacoes.append(
                    Operacao(
                        origem=Path(),
                        destino=self.raiz_destino,
                        tipo=TipoOperacao.SKIP,
                        motivo="Foto sem caminho (incompatível com o plano)"
                    )
                )
                continue

            # Se estiver marcada como duplicada, não mexemos (política MVP)
            if getattr(foto, "duplicada", False):
                operacoes.append(
                    Operacao(
                        origem=origem,
                        destino=origem,
                        tipo=TipoOperacao.SKIP,
                        motivo="Duplicado"
                    )
                )
                continue

            # A regra devolve uma PASTA destino (não o ficheiro)
            pasta_destino = self.regra.calcular_destino(foto, self.raiz_destino)

            # O ficheiro destino é pasta_destino + nome do ficheiro original
            destino = pasta_destino / foto.nome_de_ficheiro

            # Evitar operações inúteis (já está onde devia estar)
            # Resolve também casos onde raiz_destino == pasta atual por engano.
            if destino.resolve() == origem.resolve():
                operacoes.append(
                    Operacao(
                        origem=origem,
                        destino=destino,
                        tipo=TipoOperacao.SKIP,
                        motivo="Já está no destino"
                    )
                )
                continue

            # Por defeito, no MVP: mover
            operacoes.append(
                Operacao(
                    origem=origem,
                    destino=destino,
                    tipo=TipoOperacao.MOVER,
                    motivo="OK"
                )
            )

        return operacoes
