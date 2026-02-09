from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

from classes.detetar_duplicados import DetetarDuplicados
from classes.executor_de_operacoes import ExecutorSeguro
from classes.foto import Foto
from classes.monitor_de_operacoes import MonitorDeOperacoes
from classes.plano_de_operacoes import PlanoDeOperacoes
from classes.regra_de_organizacao import RegraPorData, RegraPorLocal
from classes.relatorio import Relatorio


EXTENSOES_FOTO = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}


def listar_ficheiros_foto(raiz: Path, limite: Optional[int] = None) -> List[Path]:
    ficheiros: List[Path] = []
    for p in raiz.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in EXTENSOES_FOTO:
            continue
        ficheiros.append(p)
        if limite is not None and len(ficheiros) >= limite:
            break
    return ficheiros


def construir_fotos(caminhos: Iterable[Path]) -> List[Foto]:
    fotos: List[Foto] = []
    for c in caminhos:
        f = Foto(c)
        f.extrair_metadados()
        f.calcular_hash()
        fotos.append(f)
    return fotos


def escolher_raiz_destino(pasta_origem: Path) -> Path:
    # cria a pasta ao mesmo nível da origem
    return pasta_origem.parent / "Foto_Organizada"

def perguntar_aplicar() -> bool:
    """
    Pergunta ao utilizador se quer aplicar as operações após preview.
    Aceita apenas: s/S/y/Y e n/N.
    Qualquer outra coisa repete com aviso.
    """
    while True:
        resp = input("Aplicar agora as operações? [s/N] ").strip()

        if resp in ("s", "S", "y", "Y"):
            return True
        if resp in ("n", "N", ""):
            # Enter vazio conta como "não" (por causa do [s/N])
            return False

        print("Opção inválida. Responde apenas com: s/S/y/Y (sim) ou n/N (não).")

def run(
    origem: Path,
    modo_preview: bool,
    regra: str,
    precision: int,
    limite: Optional[int],
) -> int:
    if not origem.exists() or not origem.is_dir():
        print(f"ERRO: origem não existe ou não é diretório: {origem}")
        return 2

    caminhos = listar_ficheiros_foto(origem, limite=limite)
    if not caminhos:
        print("Nenhuma foto encontrada (extensões suportadas: jpg/jpeg/png/webp/tif/tiff/heic).")
        return 0

    fotos = construir_fotos(caminhos)

    # Duplicados (marca Foto.duplicada)
    n_duplicadas = DetetarDuplicados().marcar_duplicados(fotos)

    # Regra
    if regra == "data":
        regra_obj = RegraPorData()
    elif regra == "local":
        regra_obj = RegraPorLocal(precision=precision)
    else:
        print(f"ERRO: regra inválida: {regra} (usa 'data' ou 'local')")
        return 2

    raiz_destino = escolher_raiz_destino(origem)

    # Plano (dry-run real)
    plano = PlanoDeOperacoes(regra=regra_obj, raiz_destino=raiz_destino)
    operacoes = plano.gerar(fotos)

    # Execução (ou preview)
    monitor = MonitorDeOperacoes()
    executor = ExecutorSeguro(monitor=monitor)
    resultado = executor.executar(operacoes, modo_preview=modo_preview)

    # Relatório
    resumo = Relatorio().gerar(
        operacoes=operacoes,
        resultado=resultado,
        registos=monitor.obter_registos(),
        duplicadas=n_duplicadas,
    )

    # Output simples (por agora)
    modo_txt = "PREVIEW" if modo_preview else "REAL"
    print(f"\n=== Foto_Organizada | modo={modo_txt} | regra={regra} ===")
    print(f"Origem: {origem}")
    print(f"Destino: {raiz_destino}")
    print(f"Fotos analisadas: {len(fotos)} | Duplicadas: {resumo.duplicadas}")
    print(f"Operações: total={resumo.total_operacoes} movidas={resumo.movidas} skipped={resumo.skipped} erros={resumo.erros}")
    print(f"Logs: info={resumo.logs_info} warn={resumo.logs_warn} error={resumo.logs_error}")

    if resumo.skips_por_motivo:
        print("\nSkips por motivo:")
        for motivo, n in sorted(resumo.skips_por_motivo.items(), key=lambda x: (-x[1], x[0])):
            print(f"  - {motivo}: {n}")

    # Mostrar top 5 pastas de destino por volume
    if resumo.distribuicao_por_pasta:
        print("\nTop pastas destino:")
        top = sorted(resumo.distribuicao_por_pasta.items(), key=lambda x: (-x[1], str(x[0])))[:5]
        for pasta, n in top:
            print(f"  - {pasta}: {n}")

    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Organizador de Fotografias (CLI) — AF3→AF6")
    p.add_argument("--origem", type=Path, required=True, help="Pasta origem (ex.: DCIM/WhatsApp)")
    p.add_argument("--modo", choices=["preview", "real"], default="preview", help="Preview não mexe no disco")
    p.add_argument("--regra", choices=["data", "local"], default="data", help="Regra de organização")
    p.add_argument("--precision", type=int, default=3, help="Precisão GPS (só na regra local)")
    p.add_argument("--limite", type=int, default=None, help="Limitar nº de fotos (debug/teste)")
    p.add_argument("--yes", action="store_true", help="Aplicar após preview sem perguntar")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # 1) Preview sempre
    code = run(
        origem=args.origem,
        modo_preview=True,
        regra=args.regra,
        precision=args.precision,
        limite=args.limite,
    )
    if code != 0:
        return code

    # 2) Decisão
    auto_aplicar = args.yes or (args.modo == "real")

    if not auto_aplicar:
        aplicar = perguntar_aplicar()
        if not aplicar:
            print("Ok — mantido em preview. Nenhuma alteração foi aplicada.")
            return 0

    # 3) Execução real
    return run(
        origem=args.origem,
        modo_preview=False,
        regra=args.regra,
        precision=args.precision,
        limite=args.limite,
    )


if __name__ == "__main__":
    raise SystemExit(main())
