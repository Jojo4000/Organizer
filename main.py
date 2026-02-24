from __future__ import annotations

import warnings
from PIL import Image as PILImage
from PIL import Image
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

def detetar_imagens_grandes(caminhos: list[Path]) -> tuple[list[Path], int]:
    """
    Devolve (lista_grandes, max_pixels).
    Abre a imagem apenas para ler dimensões, e não deixa o warning "vazar".
    Considera "grande" se exceder o limite atual do Pillow (MAX_IMAGE_PIXELS).
    """
    grandes: list[Path] = []
    max_px = 0

    # Limite atual (default do Pillow costuma ser ~89M px)
    limite = PILImage.MAX_IMAGE_PIXELS
    if limite is None:
        # Se estiver None, não há limite => não sinalizamos nada como "grande"
        return [], 0

    for p in caminhos:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", PILImage.DecompressionBombWarning)
                with Image.open(p) as img:
                    px = img.size[0] * img.size[1]

            if px > int(limite):
                grandes.append(p)
                max_px = max(max_px, px)

        except Exception:
            # se não conseguir abrir, ignora para este check
            continue

    return grandes, max_px

def decidir_tratamento_imagens_grandes(caminhos: list[Path]) -> tuple[Optional[list[Path]], bool, int]:
    """
    Decide o que fazer quando há imagens muito grandes.
    Retorna:
      - caminhos_filtrados (ou None se cancelar)
      - incluir_grandes (True => processar tudo; False => ignorar grandes)
      - n_grandes (para mensagens)
    """
    grandes, max_px = detetar_imagens_grandes(caminhos)
    if not grandes:
        return caminhos, True, 0

    mp = max_px / 1_000_000
    n_grandes = len(grandes)

    print(
        f"\nAVISO: Detetadas {n_grandes} imagem(ns) muito grandes (até ~{mp:.0f} MP). "
        "O Pillow avisa por segurança (DecompressionBombWarning) e o processamento pode ser mais lento/consumir mais RAM."
    )
    print("Isto também pode indicar ficheiros maliciosos (decompression bomb), se a origem não for confiável.")

    # 1) Preferência: continuar SEM as grandes
    ignorar = perguntar_aplicar(
        f"Continuar ignorando estas {n_grandes} imagem(ns) muito grandes? [s/N] "
    )
    if ignorar:
        filtrados = [p for p in caminhos if p not in set(grandes)]
        if not filtrados:
            print("Ok — todas as imagens encontradas são consideradas 'muito grandes'. Nada para processar.")
            return [], False, n_grandes
        print(f"Ok — a continuar SEM {n_grandes} imagem(ns) muito grandes.")
        return filtrados, False, n_grandes

    # 2) Se não quer ignorar, pergunta se quer INCLUIR
    incluir = perguntar_aplicar(
        f"Incluir as {n_grandes} imagem(ns) muito grandes (pode ser lento/consumir mais RAM)? [s/N] "
    )
    if incluir:
        print("Ok — a continuar INCLUINDO as imagens muito grandes.")
        return caminhos, True, n_grandes

    # 3) Caso contrário, cancelar
    print("Ok — cancelado. Não foi feita nenhuma análise nem alterações no disco.")
    return None, False, n_grandes

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

def perguntar_aplicar(pergunta: str = "Aplicar agora as operações? [s/N] ") -> bool:
    """
    Pergunta ao utilizador e devolve True/False.
    Aceita apenas: s/S/y/Y e n/N (ou Enter).
    Qualquer outra coisa repete com aviso.
    """
    while True:
        resp = input(pergunta).strip()

        if resp in ("s", "S", "y", "Y"):
            return True
        if resp in ("n", "N", ""):
            return False

        print("Opção inválida. Responde apenas com: s/S/y/Y (sim) ou n/N (não).")

def preparar_plano(
    origem: Path,
    regra: str,
    precision: int,
    limite: Optional[int],
) -> tuple[list[Foto], list, int, Path, str] | int:
    if not origem.exists() or not origem.is_dir():
        print(f"ERRO: origem não existe ou não é diretório: {origem}")
        return 2

    caminhos = listar_ficheiros_foto(origem, limite=limite)
    if not caminhos:
        print("Nenhuma foto encontrada (extensões suportadas: jpg/jpeg/png/webp/tif/tiff/heic).")
        return 0

    # ✅ NOVO: decisão do que fazer com imagens grandes (antes de abrir EXIF/pHash)
    caminhos_decididos, incluir_grandes, _n_grandes = decidir_tratamento_imagens_grandes(caminhos)
    if caminhos_decididos is None:
        # cancelado pelo utilizador
        return 0

    caminhos = caminhos_decididos

    # ✅ Evita spam de warnings a partir daqui
    warnings.filterwarnings("ignore", category=PILImage.DecompressionBombWarning)

    # ✅ Se o user aceitou incluir grandes, aumenta o limite
    if incluir_grandes:
        PILImage.MAX_IMAGE_PIXELS = 200_000_000  # 200MP

    fotos = construir_fotos(caminhos)

    det = DetetarDuplicados()
    det.marcar_duplicados(fotos)

    # quase duplicados (se o método existir)
    if hasattr(det, "marcar_quase_duplicados"):
        det.marcar_quase_duplicados(fotos, threshold=3)

    n_duplicadas = sum(1 for f in fotos if f.duplicada)

    if regra == "data":
        regra_obj = RegraPorData()
    elif regra == "local":
        regra_obj = RegraPorLocal(precision=precision)
    else:
        print(f"ERRO: regra inválida: {regra} (usa 'data' ou 'local')")
        return 2

    raiz_destino = escolher_raiz_destino(origem)
    plano = PlanoDeOperacoes(regra=regra_obj, raiz_destino=raiz_destino)
    operacoes = plano.gerar(fotos)

    return fotos, operacoes, n_duplicadas, raiz_destino, regra

def executar_e_relatar(
    origem: Path,
    raiz_destino: Path,
    regra: str,
    operacoes,
    n_duplicadas: int,
    modo_preview: bool,
) -> int:
    monitor = MonitorDeOperacoes()
    executor = ExecutorSeguro(monitor=monitor)
    resultado = executor.executar(operacoes, modo_preview=modo_preview)

    resumo = Relatorio().gerar(
        operacoes=operacoes,
        resultado=resultado,
        registos=monitor.obter_registos(),
        duplicadas=n_duplicadas,
    )

    modo_txt = "PREVIEW" if modo_preview else "REAL"
    print(f"\n=== Foto_Organizada | modo={modo_txt} | regra={regra} ===")
    print(f"Origem: {origem}")
    print(f"Destino: {raiz_destino}")
    print(f"Operações: total={resumo.total_operacoes} movidas={resumo.movidas} skipped={resumo.skipped} erros={resumo.erros}")
    print(f"Duplicadas: {resumo.duplicadas}")
    print(f"Logs: info={resumo.logs_info} warn={resumo.logs_warn} error={resumo.logs_error}")

    return 0

def run(
    origem: Path,
    modo_preview: bool,
    regra: str,
    precision: int,
    limite: Optional[int],
    caminhos: Optional[List[Path]] = None,
    incluir_grandes: bool = True,
) -> int:
    if not origem.exists() or not origem.is_dir():
        print(f"ERRO: origem não existe ou não é diretório: {origem}")
        return 2

    if caminhos is None:
        caminhos = listar_ficheiros_foto(origem, limite=limite)

    if not caminhos:
        print("Nenhuma foto encontrada (extensões suportadas: jpg/jpeg/png/webp/tif/tiff/heic).")
        return 0

    # Se o utilizador aceitou incluir grandes: aumenta limite e evita spam de warnings
    if incluir_grandes:
        PILImage.MAX_IMAGE_PIXELS = 200_000_000  # 200MP
        warnings.filterwarnings("ignore", category=PILImage.DecompressionBombWarning)

    fotos = construir_fotos(caminhos)

    # Duplicados: 1) exatos (MD5) + 2) quase duplicados (pHash)
    det = DetetarDuplicados()
    det.marcar_duplicados(fotos)  # exatos

    # pHash só faz sentido se o metodo existir e se não estamos a evitar grandes por segurança/recursos
    if hasattr(det, "marcar_quase_duplicados"):
        # Se escolheste "ignorar grandes", elas já nem vêm nos caminhos => pHash corre no resto na mesma.
        det.marcar_quase_duplicados(fotos, threshold=3)

    n_duplicadas = sum(1 for f in fotos if f.duplicada)

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

    # Output simples
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

    if resumo.distribuicao_por_pasta:
        print("\nTop pastas destino:")
        top = sorted(resumo.distribuicao_por_pasta.items(), key=lambda x: (-x[1], str(x[0])))[:5]
        for pasta, n in top:
            print(f"  - {pasta}: {n}")

    return 0

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Organizador de Fotografias (CLI) — AF3→AF6")
    # Pasta onde estão as fotos
    p.add_argument("--origem", type=Path, required=True, help="Pasta origem (ex.: DCIM/WhatsApp)")
    # Opção preview para observar como os ficheiros vão mover com o relatório e efetivar com real
    p.add_argument("--modo", choices=["preview", "real"], default="preview", help="Preview não mexe no disco")
    # Opções de organização
    p.add_argument("--regra", choices=["data", "local"], default="data", help="Regra de organização")
    # Número de casas decimais para o arredondamento de GPS (futuramente aplicar localização no maoa)
    p.add_argument("--precision", type=int, default=3, help="Precisão GPS (só na regra local)")
    # Limitar o número de fotos que podem ser processadas.
    p.add_argument("--limite", type=int, default=None, help="Limitar nº de fotos (debug/teste)")
    # Opção de continuar com real após relatório de preview
    p.add_argument("--yes", action="store_true", help="Aplicar após preview sem perguntar")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    prep = preparar_plano(
        origem=args.origem,
        regra=args.regra,
        precision=args.precision,
        limite=args.limite,
    )
    if isinstance(prep, int):
        return prep

    fotos, operacoes, n_duplicadas, raiz_destino, regra = prep

    # 1) Preview (usando o plano já calculado)
    code = executar_e_relatar(
        origem=args.origem,
        raiz_destino=raiz_destino,
        regra=regra,
        operacoes=operacoes,
        n_duplicadas=n_duplicadas,
        modo_preview=True,
    )
    if code != 0:
        return code

    # 2) Decisão
    auto_aplicar = args.yes or (args.modo == "real")
    if not auto_aplicar:
        if not perguntar_aplicar():
            print("Ok — mantido em preview. Nenhuma alteração foi aplicada.")
            return 0

    # 3) REAL (reutiliza exatamente o mesmo plano — sem recalcular nada)
    return executar_e_relatar(
        origem=args.origem,
        raiz_destino=raiz_destino,
        regra=regra,
        operacoes=operacoes,
        n_duplicadas=n_duplicadas,
        modo_preview=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
