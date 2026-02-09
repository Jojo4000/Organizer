from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from classes.executor_de_operacoes import ResultadoExecucao
from classes.monitor_de_operacoes import Registo
from classes.operacao import Operacao, TipoOperacao


@dataclass(frozen=True)
class ResumoRelatorio:
    total_operacoes: int
    movidas: int
    skipped: int
    erros: int

    # logs agregados
    logs_info: int
    logs_warn: int
    logs_error: int

    # análises úteis
    skips_por_motivo: Mapping[str, int]
    distribuicao_por_pasta: Mapping[Path, int]

    # opcional (se passares fotos)
    duplicadas: Optional[int] = None


class Relatorio:
    """
    Calcula um resumo final do que o sistema fez (ou planeou fazer).

    SRP: apenas calcula; não imprime e não escreve ficheiros.
    """

    def gerar(
        self,
        operacoes: Sequence[Operacao],
        resultado: ResultadoExecucao,
        registos: Sequence[Registo],
        duplicadas: Optional[int] = None,
    ) -> ResumoRelatorio:
        skips_por_motivo = self._contar_skips_por_motivo(operacoes)
        distribuicao = self._contar_por_pasta_destino(operacoes)
        info, warn, error = self._contar_logs_por_nivel(registos)

        return ResumoRelatorio(
            total_operacoes=resultado.total,
            movidas=resultado.movidas,
            skipped=resultado.skipped,
            erros=resultado.erros,
            logs_info=info,
            logs_warn=warn,
            logs_error=error,
            skips_por_motivo=skips_por_motivo,
            distribuicao_por_pasta=distribuicao,
            duplicadas=duplicadas,
        )

    def _contar_skips_por_motivo(self, operacoes: Iterable[Operacao]) -> dict[str, int]:
        contagem: dict[str, int] = {}

        for op in operacoes:
            if op.tipo == TipoOperacao.SKIP:
                motivo = op.motivo or "SemMotivo"
                contagem[motivo] = contagem.get(motivo, 0) + 1

        return contagem

    def _contar_por_pasta_destino(self, operacoes: Iterable[Operacao]) -> dict[Path, int]:
        """
        Conta quantas operações (MOVER) vão para cada pasta.
        Útil para ver distribuição por ano/mês/dia ou GPS/SemLocal.

        Nota: Para SKIP não conta (não tem destino real).
        """
        contagem: dict[Path, int] = {}

        for op in operacoes:
            if op.tipo != TipoOperacao.MOVER:
                continue

            pasta = op.destino.parent
            contagem[pasta] = contagem.get(pasta, 0) + 1

        return contagem

    def _contar_logs_por_nivel(self, registos: Sequence[Registo]) -> tuple[int, int, int]:
        info = warn = error = 0

        for r in registos:
            nivel = (r.nivel or "").upper()
            if nivel == "WARN":
                warn += 1
            elif nivel == "ERROR":
                error += 1
            else:
                # default INFO (inclui qualquer coisa inesperada para não perder contagem)
                info += 1

        return info, warn, error
