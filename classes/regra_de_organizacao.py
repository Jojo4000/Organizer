from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol


class FotoProtocol(Protocol):
    """Contrato informal (duck typing verificável) para objetos tipo Foto."""
    @property
    def caminho(self) -> Path: ...

    @property
    def nome_de_ficheiro(self) -> str: ...

    @property
    def data_de_captura(self) -> Optional[datetime]: ...

    @property
    def local_gps(self) -> Optional[tuple[float, float]]: ...

    @property
    def duplicada(self) -> bool: ...

class RegraDeOrganizacao(ABC):
    @abstractmethod
    def calcular_destino(self, foto: FotoProtocol, raiz: Path) -> Path:
        """Calcula a pasta destino. Não cria pastas nem mexe em ficheiros."""
        raise NotImplementedError


class RegraPorData(RegraDeOrganizacao):
    def calcular_destino(self, foto: FotoProtocol, raiz: Path) -> Path:
        dt = getattr(foto, "data_de_captura", None)

        # fallback LSP: sem data -> SemData
        if dt is None:
            return raiz / "SemData"

        ano = f"{dt.year:04d}"
        mes = f"{dt.month:02d}"

        # ✅ Ano/Mês (sem dia)
        return raiz / ano / mes


@dataclass(frozen=True)
class RegraPorLocal(RegraDeOrganizacao):
    precision: int = 3
    pasta_sem_local: str = "SemLocal"
    prefixo: str = "GPS"

    def calcular_destino(self, foto: FotoProtocol, raiz: Path) -> Path:
        gps = foto.local_gps
        if gps is None:
            return raiz / self.pasta_sem_local

        lat, lon = gps
        lat_r = round(lat, self.precision)
        lon_r = round(lon, self.precision)

        pasta = f"{self.prefixo}_{lat_r:.{self.precision}f}_{lon_r:.{self.precision}f}"
        return raiz / pasta
