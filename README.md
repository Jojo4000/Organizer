# OrganizadorDeFotografias (CLI)

Projeto desenvolvido ao longo das AF3→AF7 (Programação por Objetos).
Organiza fotografias a partir de uma pasta origem, gerando um **plano (preview)** e, se o utilizador aceitar, executando a **organização real**.

## Funcionalidades
- **Scan recursivo** de fotos numa pasta (`rglob`).
- **Extração de metadados**:
  - Data de captura via EXIF (quando existe) ou fallback para `mtime`.
  - GPS (quando existe) convertido para `(lat, lon)` em graus decimais.
- **Deteção de duplicados exatos** (hash do conteúdo).
- **Deteção de quase-duplicados** (pHash / distância pequena) – biblioteca extra do Tópico 7.
- **Plano de operações (dry-run)**: gera operações sem tocar no disco.
- **Execução segura**:
  - logs via Monitor
  - **SafeRename** para evitar sobrescrita em colisões.
- **Relatório** com resumo de operações, logs e distribuição por pastas.

## Estrutura (resumo)
- `classes/` — domínio e lógica (Foto, Regras, Plano, Executor, Monitor, Relatório, Duplicados)
- `tests/` — testes unitários e integração (pytest)
- `main.py` — CLI (preview sempre + confirmação para executar real)

## Requisitos
- Python 3.12+
- Dependências principais: `pillow`, `imagehash` (Tópico 7)

Instalar dependências:
```bash
python -m pip install -r requirements.txt
```

Instalar dependências para desenvolvimento:
```bash
python -m pip install -r requirements-dev.txt
```

## Como usar

### Ajuda
Mostra todas as opções do CLI:
```bash
python main.py --help
```

### Executar (preview → pergunta → real)
Exemplo (organizar por data):
```bash
python main.py --origem "C:\caminho\para\fotos" --regra data
```

### Modos
```bash
--modo preview (default): faz preview e mostra relatório

--modo real: prepara para executar real (ainda pode perguntar, dependendo do --yes)
```
### Confirmar automaticamente após preview
```bash
python main.py --origem "C:\caminho\para\fotos" --regra data --yes
```

### Regras disponíveis
```bash
--regra data → organiza por Ano/Mês

--regra local → organiza por GPS_... ou SemLocal

--precision N controla arredondamento do GPS (default: 3)
```

#### Exemplo:
```bash
python main.py --origem "C:\caminho\para\fotos" --regra local --precision 3
```

###  Limitar nº de fotos (debug)
```bash
python main.py --origem "C:\caminho\para\fotos" --regra data --limite 50
```

### Duplicados e quase-duplicados

### Duplicados exatos: mesmo conteúdo (hash), marcados como Duplicado → o plano gera SKIP.

### Quase-duplicados: imagens muito semelhantes (pHash + distância pequena) → também marcados como Duplicado.

#### Política: o “original” é escolhido de forma determinística (mais antigo por data EXIF; fallback para mtime).

#### Segurança (imagens muito grandes)

#### Se existirem imagens com muitos megapixels, o Pillow pode emitir DecompressionBombWarning.
#### O programa avisa e permite:

#### processar tudo, ou ignorar apenas as imagens muito grandes e continuar com as restantes.

### Testes

#### Executar testes:
```bash
pytest -q
```

#### Coverage:
```bash
pytest --cov=classes --cov-report=term-missing
```