from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Set, List

from classes.monitor_de_operacoes import MonitorDeOperacoes, MonitorProtocol
from classes.operacao import Operacao, TipoOperacao


# -------------------------
# Modelos de resultado
# -------------------------

@dataclass
class ResultadoExecucao:
    total: int
    movidas: int
    skipped: int
    erros: int


@dataclass
class ExecResultadoOp:
    status: str  # "MOVED" | "SKIPPED" | "ERROR"
    motivo: str
    destino_final: Optional[Path] = None
    avisos: List[str] = field(default_factory=list)


# -------------------------
# Mixins cooperativos
# -------------------------

class LogMixin:
    """
    Logging transversal (antes / depois / erro) via MonitorProtocol.
    Cooperativo: interceta executar_operacao e chama super().
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    _monitor: MonitorProtocol  # esperado no self

    def executar_operacao(
        self,
        op: Operacao,
        modo_preview: bool = False,
        destino_override: Optional[Path] = None,
    ) -> ExecResultadoOp:
        origem = op.origem
        destino_planeado = destino_override or op.destino

        # "antes" (só faz sentido para MOVER)
        if op.tipo == TipoOperacao.MOVER and not modo_preview:
            self._monitor.registar(
                f"ANTES MOVER: {origem} -> {destino_planeado}",
                nivel="INFO",
                operacao=op,
            )

        res = super().executar_operacao(op, modo_preview=modo_preview, destino_override=destino_override)

        # avisos (ex.: colisão resolvida)
        for aviso in res.avisos:
            self._monitor.registar(aviso, nivel="WARN", operacao=op)

        # logs principais
        if res.status == "SKIPPED":
            self._monitor.registar(f"SKIP: {res.motivo}", nivel="INFO", operacao=op)
            return res

        if res.status == "ERROR":
            self._monitor.registar(f"ERRO: {res.motivo}", nivel="ERROR", operacao=op)
            return res

        # MOVED
        destino_final = res.destino_final or destino_planeado
        if modo_preview:
            self._monitor.registar(
                f"PREVIEW MOVER: {origem} -> {destino_final}",
                nivel="INFO",
                operacao=op,
            )
        else:
            # "depois"
            self._monitor.registar(
                f"MOVER: {origem} -> {destino_final}",
                nivel="INFO",
                operacao=op,
            )

        return res


class SafeRenameMixin:
    """
    Renome seguro em colisões.
    Cooperativo: interceta executar_operacao e chama super().
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

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

    def executar_operacao(
        self,
        op: Operacao,
        modo_preview: bool = False,
        destino_override: Optional[Path] = None,
    ) -> ExecResultadoOp:
        destino = destino_override or op.destino

        # aplica SafeRename se houver colisão (mesmo em preview, para o plano ser fiel)
        if op.tipo == TipoOperacao.MOVER and destino.exists():
            novo = self._safe_rename(destino)
            res = super().executar_operacao(op, modo_preview=modo_preview, destino_override=novo)
            res.avisos.append(f"Colisão no destino; SafeRename -> {novo.name}")
            return res

        return super().executar_operacao(op, modo_preview=modo_preview, destino_override=destino_override)


# -------------------------
# Executor base (core)
# -------------------------

class ExecutorDeOperacoes:
    """
    Core do executor: validações, preview, criação de diretórios, I/O (move).
    Não faz logging nem SafeRename aqui — isso vem pelos mixins.
    """

    def __init__(self, monitor: Optional[MonitorProtocol] = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._monitor: MonitorProtocol = monitor or MonitorDeOperacoes()
        self._dirs_criadas: Set[Path] = set()

    @property
    def monitor(self) -> MonitorProtocol:
        return self._monitor

    def executar(self, operacoes: Iterable[Operacao], modo_preview: bool = False) -> ResultadoExecucao:
        total = movidas = skipped = erros = 0

        for op in operacoes:
            total += 1
            res = self.executar_operacao(op, modo_preview=modo_preview)

            if res.status == "MOVED":
                movidas += 1
            elif res.status == "SKIPPED":
                skipped += 1
            else:
                erros += 1

        return ResultadoExecucao(total=total, movidas=movidas, skipped=skipped, erros=erros)

    def executar_operacao(
        self,
        op: Operacao,
        modo_preview: bool = False,
        destino_override: Optional[Path] = None,
    ) -> ExecResultadoOp:
        # 1) tipo
        if op.tipo == TipoOperacao.SKIP:
            return ExecResultadoOp(status="SKIPPED", motivo=op.motivo or "SKIP")

        if op.tipo != TipoOperacao.MOVER:
            return ExecResultadoOp(status="SKIPPED", motivo=f"tipo não suportado ({op.tipo})")

        origem = op.origem
        destino = destino_override or op.destino

        # 2) valida origem
        if not origem.exists() or not origem.is_file():
            return ExecResultadoOp(status="SKIPPED", motivo="origem não existe ou não é ficheiro")

        # 3) preview não mexe no disco
        if modo_preview:
            return ExecResultadoOp(status="MOVED", motivo="PREVIEW", destino_final=destino)

        # 4) execução real
        try:
            self._ensure_dir(destino.parent)
            shutil.move(str(origem), str(destino))
            return ExecResultadoOp(status="MOVED", motivo="OK", destino_final=destino)
        except Exception as e:
            return ExecResultadoOp(status="ERROR", motivo=f"{type(e).__name__}: {e}", destino_final=destino)

    def _ensure_dir(self, pasta: Path) -> None:
        p = pasta.resolve()
        if p in self._dirs_criadas:
            return
        p.mkdir(parents=True, exist_ok=True)
        self._dirs_criadas.add(p)


# -------------------------
# Hierarquia “complexa” (AF6.2)
# -------------------------

class ExecutorSeguro(LogMixin, SafeRenameMixin, ExecutorDeOperacoes):
    """
    Combina comportamentos via herança múltipla.
    MRO esperada: LogMixin -> SafeRenameMixin -> ExecutorDeOperacoes -> object
    """
    pass
