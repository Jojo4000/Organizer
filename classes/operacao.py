from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TipoOperacao(str, Enum):
    """Tipos de operação suportados no MVP."""
    MOVER = "MOVER"
    SKIP = "SKIP"


@dataclass
class Operacao:
    """
    Operação proposta pelo PlanoDeOperacoes (preview/dry-run).
    Não executa nada: descreve o que seria feito.
    """
    origem: Path
    destino: Path
    tipo: TipoOperacao
    motivo: str = "OK"
    destino_final: Optional[Path] = None  # <-- novo

    # Será preenchido pelo Executor se tiver de renomear por colisão
    destino_final: Optional[Path] = None

    @property
    def destino_efetivo(self) -> Path:
        return self.destino_final or self.destino