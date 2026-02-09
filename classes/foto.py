# Classe path vai buscar os caminhos de pastas/ficheiros em Windows/Linux
from pathlib import Path
# Classe datetime representa a data/hora num objeto
from datetime import datetime
# Opção de tipo que vai permitir que em anotações de tipo exista a possibilidade de ser None sem erro
from typing import Optional
# Módulo que vai permitir calcular hash para comparação de duplicados
import hashlib
# Classe Image permite abrir o ficheiro imagem e aceder a metadados do objeto imagem
# Dicionário TAGS é um tradutor de IDs numéricos para do EXIF para nomes legíveis
from PIL import Image, ExifTags
TAGS = ExifTags.TAGS

class Foto:

    def __init__(self, caminho: Path) -> None:
        self._caminho: Path = Path(caminho)
        self._data_de_captura: Optional[datetime] = None
        self._local_gps: Optional[tuple[float, float]] = None
        self._hash_conteudo: Optional[str] = None
        self._duplicada: bool = False

    # --- Atributos ---
    @property
    def caminho(self) -> Path:
        return self._caminho

    @property
    def nome_de_ficheiro(self) -> str:
        return self._caminho.name

    @property
    def data_de_captura(self) -> Optional[datetime]:
        return self._data_de_captura

    @property
    def local_gps(self) -> Optional[tuple[float, float]]:
        return self._local_gps

    @property
    def hash_conteudo(self) -> Optional[str]:
        return self._hash_conteudo

    @property
    def duplicada(self) -> bool:
        return self._duplicada

    # --- métodos ---

    def extrair_metadados(self) -> None:
        """
        Preenche data_de_captura e local_gps.

        - Data: tenta EXIF (DateTimeOriginal/Digitized/DateTime); se falhar usa mtime.
        - GPS: tenta EXIF GPSInfo; se falhar ou não existir fica None.
        """

        # Se o ficheiro não existir
        if not self._caminho.exists() or not self._caminho.is_file():
            return

        self._data_de_captura = None
        self._local_gps = None

        try:
            with Image.open(self._caminho) as img:
                exif = img.getexif()

            # 36867: DateTimeOriginal | 36868: DateTimeDigitized | 306: DateTime
            data_str = exif.get(36867) or exif.get(36868) or exif.get(306)

            if data_str:
                try:
                    self._data_de_captura = datetime.strptime(str(data_str), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    self._preencher_data_a_partir_do_sistema()
            else:
                self._preencher_data_a_partir_do_sistema()

            # GPSInfo (34853) — fica None se não existir/der erro
            gps_info = exif.get(34853)
            if gps_info:
                self._local_gps = self._extrair_gps(gps_info)

        except Exception:
            # mantém o comportamento simples: se algo falhar, pelo menos a data vem do sistema
            self._preencher_data_a_partir_do_sistema()

    def _preencher_data_a_partir_do_sistema(self) -> None:
        """ Em caso de EXIF não existir, usa-se a data da modificação do ficheiro."""

        # Recebe os metadados fornecidos pelo métodoo '.stat()'
        info = self._caminho.stat()

        # Funciona para todos os sistemas operativos
        ts = info.st_mtime
        self._data_de_captura = datetime.fromtimestamp(ts)

    def calcular_hash(self, algoritmo: str = "md5") -> None:
        """
        Calcula o hash do ficheiro no disco em "MD5" por ser rápido e não haver
        risco de segurança, a não ser que seja definido outra acho no parâmetro
        quando chamar função (ex.: .calcular_hash("sha256"))
        """
        # Se o ficheiro não existir ou não for um ficheiro normal
        if not self._caminho.exists() or not self._caminho.is_file():
            return
        # Instanciação de um objeto hash_
        hash_ = hashlib.new(algoritmo)

        # Abre o ficheiro e lê em modo binário 'rb'
        with self._caminho.open("rb") as f:
            for bloco in iter(lambda: f.read(8192), b""):
                hash_.update(bloco)

        # Guarda o hash final como uma string hexadecimal
        self._hash_conteudo = hash_.hexdigest()

    def marcar_como_duplicado(self) -> None:
        """Apenas altera o estado de duplicado: Boolean """
        self._duplicada = True

    def _extrair_gps(self, gps_info) -> Optional[tuple[float, float]]:
        """
        Extrai coordenadas GPS (latitude, longitude) a partir de GPSInfo do EXIF.

        Retorna:
          - (lat, lon) em graus decimais (float, float)
          - None se não existir GPS ou se algo falhar
        """
        try:
            # Normaliza gps_info para um dicionário "normal" do Python
            # (gps_info pode vir como um tipo especial do Pillow)
            gps = dict(gps_info)

            # No EXIF GPSInfo:
            # 1 = GPSLatitudeRef  ('N' ou 'S')
            # 2 = GPSLatitude     (graus, minutos, segundos) em frações
            # 3 = GPSLongitudeRef ('E' ou 'W')
            # 4 = GPSLongitude    (graus, minutos, segundos) em frações
            lat = self._gps_coord_to_deg(gps.get(2), gps.get(1))  # 2=Latitude, 1=Ref N/S
            lon = self._gps_coord_to_deg(gps.get(4), gps.get(3))  # 4=Longitude, 3=Ref E/W

            # Se faltarem dados ou conversão falhar, não inventamos coordenadas
            if lat is None or lon is None:
                return None

            return (lat, lon)

        except Exception:
            # Fail-safe: se algo inesperado acontecer, devolve None
            return None

    def _gps_coord_to_deg(self, coord, ref) -> Optional[float]:
        """
        Converte coordenada EXIF GPS (DMS) em graus decimais.

        coord: normalmente uma sequência com 3 itens (deg, min, sec),
               e cada item pode ser:
               - tuple (num, den) representando fração num/den
               - ou um número/IFDRational que o float() entende
        ref: 'N'/'S' para latitude, 'E'/'W' para longitude

        Retorna:
          - float em graus decimais
          - None se faltar informação / formato inválido
        """
        # Se não temos a coordenada completa ou referência, não dá para calcular
        if not coord or not ref:
            return None

        def to_float(x) -> Optional[float]:
            """
            Converte um valor EXIF para float.

            - Se vier como fração (num, den), converte para num/den
            - Se vier como número (ou IFDRational), usa float(x)
            """
            if isinstance(x, tuple) and len(x) == 2:
                # numerador e denominador
                num, den = x
                if float(den) == 0.0:
                    return None
                return float(num) / float(den)
            return float(x)

        # coord[0], coord[1], coord[2] -> graus, minutos, segundos
        deg = to_float(coord[0])
        minutes = to_float(coord[1])
        seconds = to_float(coord[2])

        # Se alguma parte falhar, devolvemos None (sem exceções para cima)
        if deg is None or minutes is None or seconds is None:
            return None

        # Converte DMS para graus decimais
        # decimal = graus + minutos/60 + segundos/3600
        value = deg + (minutes / 60.0) + (seconds / 3600.0)

        # Ajusta o sinal consoante hemisfério:
        # Sul (S) e Oeste (W) devem ser negativos
        ref = str(ref).upper()
        if ref in ("S", "W"):
            value = -value
        return value

    def local_gps_formatado(self) -> Optional[str]:
        """
        Representação textual opcional do GPS para logs/relatórios.

        Retorna:
          - "lat,lon" com 6 casas decimais
          - None se não houver GPS
        """
        if not self._local_gps:
            return None
        lat, lon = self._local_gps
        return f"{lat:.6f},{lon:.6f}"