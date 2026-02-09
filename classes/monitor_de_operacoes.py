from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence, Protocol

from classes.operacao import Operacao


class MonitorProtocol(Protocol):
    def registar(self, mensagem: str, nivel: str = "INFO", operacao: Optional[Operacao] = None) -> None: ...
    def obter_registos(self) -> Sequence["Registo"]: ...
@dataclass(frozen=True)
class Registo:
    instante: datetime
    nivel: str          # "INFO", "WARN", "ERROR"
    mensagem: str
    operacao: Optional[Operacao] = None


class MonitorDeOperacoes:
    """
    Guarda logs/registos durante o preview e/ou execução.
    - Não escreve em ficheiros (por agora)
    - Serve para o Relatorio e para debug
    """

    def __init__(self) -> None:
        self._registos: List[Registo] = []

    def registar(self, mensagem: str, nivel: str = "INFO", operacao: Optional[Operacao] = None) -> None:
        self._registos.append(
            Registo(
                instante=datetime.now(),
                nivel=nivel,
                mensagem=mensagem,
                operacao=operacao,
            )
        )

    def obter_registos(self) -> Sequence[Registo]:
        # devolve uma vista "só-leitura"
        return tuple(self._registos)

    def limpar(self) -> None:
        self._registos.clear()
