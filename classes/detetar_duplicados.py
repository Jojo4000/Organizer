from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image
import imagehash

from classes.foto import Foto


@dataclass(frozen=True)
class GrupoDuplicados:
    """Representa um grupo de fotos com o mesmo hash (exato)."""
    hash_conteudo: str
    fotos: Sequence[Foto]


@dataclass(frozen=True)
class GrupoQuaseDuplicados:
    """Representa um grupo de fotos visualmente muito semelhantes (pHash)."""
    hash_visual: str
    fotos: Sequence[Foto]
    threshold: int


class DetetarDuplicados:
    """
    Responsável por identificar e marcar fotos duplicadas.

    Modos:
      1) Exato (MD5/SHA): bytes iguais -> duplicado garantido
      2) Quase (pHash): aparência semelhante -> duplicado provável

    Política MVP:
      - Para cada grupo repetido, escolhe 1 "original" (mais antigo)
      - Marca as restantes como duplicadas (foto.marcar_como_duplicado())
    """

    def __init__(self, algoritmo: str = "md5") -> None:
        self._algoritmo = algoritmo

    # ------------------------
    # Duplicados EXATOS (hash bytes)
    # ------------------------

    def detetar(self, fotos: Iterable[Foto]) -> List[GrupoDuplicados]:
        por_hash: Dict[str, List[Foto]] = {}

        # 1) Garantir hash e agrupar
        for foto in fotos:
            if foto.hash_conteudo is None:
                foto.calcular_hash(self._algoritmo)

            if foto.hash_conteudo is None:
                continue

            por_hash.setdefault(foto.hash_conteudo, []).append(foto)

        # 2) Marcar duplicados (mantém mais antigo como original)
        grupos: List[GrupoDuplicados] = []
        for h, lista in por_hash.items():
            if len(lista) > 1:
                self._marcar_grupo_com_original_mais_antigo(lista)
                grupos.append(GrupoDuplicados(hash_conteudo=h, fotos=tuple(lista)))

        return grupos

    def marcar_duplicados(self, fotos: Iterable[Foto]) -> int:
        """Mantém compatibilidade com o main: marca e devolve quantas foram marcadas."""
        grupos = self.detetar(fotos)
        return sum(max(0, len(g.fotos) - 1) for g in grupos)

    # ------------------------
    # Quase duplicados (pHash)
    # ------------------------

    def detetar_quase_duplicados(
        self,
        fotos: Iterable[Foto],
        threshold: int = 2,
    ) -> List[GrupoQuaseDuplicados]:
        """
        Deteta "quase duplicados" por pHash.

        - Só considera fotos ainda NÃO marcadas como duplicadas
        - Marca duplicadas dentro de cada grupo, escolhendo o "original" mais antigo
        """
        candidatas = [f for f in fotos if not f.duplicada]

        # grupos representados por (hash_representante, lista_fotos)
        grupos: List[Tuple[imagehash.ImageHash, List[Foto]]] = []

        for foto in candidatas:
            h = self._calcular_phash(foto.caminho)
            if h is None:
                continue

            colocado = False
            for h_rep, lista in grupos:
                # distância de Hamming (ImageHash implementa subtração)
                if (h - h_rep) <= threshold:
                    lista.append(foto)
                    colocado = True
                    break

            if not colocado:
                grupos.append((h, [foto]))

        # marcar duplicados em grupos com mais de 1
        saida: List[GrupoQuaseDuplicados] = []
        for h_rep, lista in grupos:
            if len(lista) > 1:
                self._marcar_grupo_com_original_mais_antigo(lista)
                saida.append(
                    GrupoQuaseDuplicados(
                        hash_visual=str(h_rep),
                        fotos=tuple(lista),
                        threshold=threshold,
                    )
                )

        return saida

    def marcar_quase_duplicados(self, fotos: Iterable[Foto], threshold: int = 2) -> int:
        """
        Marca quase-duplicados (efeito colateral nas fotos) e devolve quantas foram marcadas.
        """
        antes = sum(1 for f in fotos if f.duplicada)
        self.detetar_quase_duplicados(fotos, threshold=threshold)
        depois = sum(1 for f in fotos if f.duplicada)
        return max(0, depois - antes)

    # ------------------------
    # Helpers
    # ------------------------

    def _calcular_phash(self, caminho: Path) -> Optional[imagehash.ImageHash]:
        """
        Calcula pHash da imagem.
        Se o Pillow não conseguir abrir (ex.: HEIC sem suporte), devolve None.
        """
        try:
            with Image.open(caminho) as img:
                return imagehash.phash(img)
        except Exception:
            return None

    def _chave_antiguidade(self, foto: Foto) -> datetime:
        """
        Define como comparamos "original mais antigo":
        1) data_de_captura (EXIF ou mtime já preenchido na Foto)
        2) fallback mtime direto do sistema se necessário
        """
        if foto.data_de_captura is not None:
            return foto.data_de_captura
        try:
            return datetime.fromtimestamp(foto.caminho.stat().st_mtime)
        except Exception:
            return datetime.max

    def _marcar_grupo_com_original_mais_antigo(self, lista: List[Foto]) -> None:
        """
        Escolhe o original como o mais antigo e marca os restantes como duplicados.
        """
        if not lista:
            return

        original = min(lista, key=self._chave_antiguidade)

        for f in lista:
            if f is original:
                continue
            f.marcar_como_duplicado()
