from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence
from datetime import datetime

from classes.foto import Foto


@dataclass(frozen=True)
class GrupoDuplicados:
    """Representa um grupo de fotos com o mesmo hash."""
    hash_conteudo: str
    fotos: Sequence[Foto]


class DetetarDuplicados:
    """
    Responsável por identificar e marcar fotos duplicadas com base no hash de conteúdo.

    Política MVP:
      - Para cada hash repetido, mantém a primeira foto como "original"
      - Marca as restantes como duplicadas (foto.marcar_como_duplicado())
    """

    def __init__(self, algoritmo: str = "md5") -> None:
        self._algoritmo = algoritmo

    def detetar(self, fotos: Iterable[Foto]) -> List[GrupoDuplicados]:
        """
        Marca duplicados nas fotos recebidas e devolve uma lista de grupos de duplicados.

        Nota: esta função pode chamar foto.calcular_hash() se necessário.
        """
        por_hash: Dict[str, List[Foto]] = {}

        # 1) Garantir hash e agrupar
        for foto in fotos:
            if foto.hash_conteudo is None:
                foto.calcular_hash(self._algoritmo)

            # Se mesmo assim não houver hash (ficheiro não existe, etc.), ignora
            if foto.hash_conteudo is None:
                continue

            por_hash.setdefault(foto.hash_conteudo, []).append(foto)

        # 2) Escolher original (mais antigo) + marcar duplicados + devolver grupos
        grupos: List[GrupoDuplicados] = []
        for h, lista in por_hash.items():
            if len(lista) <= 1:
                continue

            # chave de ordenação do "original":
            # - menor data_de_captura (EXIF -> fallback mtime)
            # - em empate, menor caminho (determinístico)
            def key_original(f: Foto):
                dt = f.data_de_captura or datetime.max  # None vai para o fim
                return (dt, str(f.caminho))

            original = min(lista, key=key_original)

            # reordena para pôr original primeiro (mantém grupo coerente)
            ordenadas = [original] + [f for f in lista if f is not original]

            # marca duplicadas as restantes
            for f in ordenadas[1:]:
                f.marcar_como_duplicado()

            grupos.append(GrupoDuplicados(hash_conteudo=h, fotos=tuple(ordenadas)))

        return grupos

    def marcar_duplicados(self, fotos: Iterable[Foto]) -> int:
        """
        Marca duplicados (efeito colateral nas fotos) e devolve quantas foram marcadas.
        Mantém compatibilidade com o main.
        """
        grupos = self.detetar(fotos)
        return sum(max(0, len(g.fotos) - 1) for g in grupos)