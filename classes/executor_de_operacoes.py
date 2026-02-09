from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set, Literal

from classes.monitor_de_operacoes import MonitorDeOperacoes, MonitorProtocol
from classes.operacao import Operacao, TipoOperacao


StatusOp = Literal["MOVIDA", "SKIPPED", "ERRO", "PREVIEW"]


@dataclass
class ResultadoExecucao:
    total: int
    movidas: int
    skipped: int
    erros: int


class ExecutorDeOperacoes:
    """
    Base (sem comportamento transversal):
      - validações mínimas
      - I/O real (mover)
      - criação de diretórios (com cache)
    Logging e SafeRename são adicionados por mixins cooperativos.
    """

    def __init__(self, monitor: Optional[MonitorProtocol] = None) -> None:
        self._monitor: MonitorProtocol = monitor or MonitorDeOperacoes()
        self._dirs_criadas: Set[Path] = set()

    @property
    def monitor(self) -> MonitorProtocol:
        return self._monitor

    def executar(self, operacoes: Iterable[Operacao], modo_preview: bool = False) -> ResultadoExecucao:
        total = movidas = skipped = erros = 0

        for op in operacoes:
            total += 1
            status = self._executar_pipeline(op, modo_preview)

            if status in ("MOVIDA", "PREVIEW"):
                movidas += 1
            elif status == "SKIPPED":
                skipped += 1
            else:
                erros += 1

        return ResultadoExecucao(total=total, movidas=movidas, skipped=skipped, erros=erros)

    def _executar_pipeline(self, op: Operacao, modo_preview: bool) -> StatusOp:
        # SKIP explícito
        if op.tipo == TipoOperacao.SKIP:
            return "SKIPPED"

        # só suportamos MOVER (por agora)
        if op.tipo != TipoOperacao.MOVER:
            op.motivo = f"Tipo não suportado: {op.tipo}"
            return "SKIPPED"

        # preview: não toca no disco
        if modo_preview:
            return "PREVIEW"

        # validação de origem: não rebenta, faz SKIP
        if not op.origem.exists() or not op.origem.is_file():
            op.motivo = "origem não existe ou não é ficheiro"
            return "SKIPPED"

        # I/O real (safe rename pode interferir aqui via mixin)
        self.executar_operacao(op)
        return "MOVIDA"

    def executar_operacao(self, op: Operacao) -> None:
        destino = op.destino
        self._ensure_dir(destino.parent)
        shutil.move(str(op.origem), str(destino))

    def _ensure_dir(self, pasta: Path) -> None:
        p = pasta.resolve()
        if p in self._dirs_criadas:
            return
        p.mkdir(parents=True, exist_ok=True)
        self._dirs_criadas.add(p)


class SafeRenameMixin:
    """Resolve colisões no destino e chama super() (mixin cooperativo)."""

    def executar_operacao(self, op: Operacao) -> None:
        destino = op.destino

        # se existir, calcula nome alternativo e MUTa op.destino
        if destino.exists():
            novo = self._safe_rename(destino)
            op.destino = novo
            self._monitor.registar(
                f"Colisão no destino; SafeRename -> {novo.name}",
                nivel="WARN",
                operacao=op,
            )

        return super().executar_operacao(op)  # type: ignore[misc]

    def _safe_rename(self, destino: Path) -> Path:
        base = destino.stem
        ext = destino.suffix
        pasta = destino.parent

        i = 1
        while True:
            candidato = pasta / f"{base} ({i}){ext}"
            if not candidato.exists():
                return candidato
            i += 1


class LogMixin:
    """Logging transversal cooperativo (antes/depois/erro + preview/skip)."""

    def _executar_pipeline(self, op: Operacao, modo_preview: bool) -> StatusOp:
        try:
            status = super()._executar_pipeline(op, modo_preview)  # type: ignore[misc]

            if status == "PREVIEW":
                self._monitor.registar(
                    f"PREVIEW MOVER: {op.origem} -> {op.destino}",
                    nivel="INFO",
                    operacao=op,
                )
                return status

            if status == "SKIPPED":
                self._monitor.registar(f"SKIP: {op.motivo}", nivel="INFO", operacao=op)
                return status

            return status  # MOVIDA (logs do move vêm de executar_operacao)

        except Exception as e:
            self._monitor.registar(f"ERRO: {type(e).__name__}: {e}", nivel="ERROR", operacao=op)
            return "ERRO"

    def executar_operacao(self, op: Operacao) -> None:
        # antes (destino ainda é o planeado)
        self._monitor.registar(f"MOVER: {op.origem} -> {op.destino}", nivel="INFO", operacao=op)

        # aqui entra SafeRenameMixin (se estiver na MRO)
        super().executar_operacao(op)  # type: ignore[misc]

        # depois (destino pode ter sido mutado para a versão safe)
        self._monitor.registar(f"DONE: {op.origem.name} -> {op.destino}", nivel="INFO", operacao=op)


class ExecutorSeguro(LogMixin, SafeRenameMixin, ExecutorDeOperacoes):
    """
    MRO:
      ExecutorSeguro -> LogMixin -> SafeRenameMixin -> ExecutorDeOperacoes -> object
    """
    pass
