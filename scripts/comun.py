"""Utilidades compartidas: descarga educada, lectura de precios y normalización de nombres.

Solo usa la librería estándar de Python para que funcione en cualquier sitio sin instalar nada.
"""
import gzip
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
PAUSA_POR_DOMINIO = 2.5  # segundos entre peticiones a la misma tienda
_ultima_peticion = {}
DEBUG = bool(os.environ.get("DEBUG"))


def leer_json(nombre, defecto=None):
    ruta = DATOS / nombre
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_json(nombre, datos):
    ruta = DATOS / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def descargar(url, reintentos=2):
    """Descarga una página respetando una pausa por dominio. Devuelve (url_final, html) o (None, None)."""
    dominio = urllib.parse.urlparse(url).netloc
    espera = PAUSA_POR_DOMINIO - (time.time() - _ultima_peticion.get(dominio, 0))
    if espera > 0:
        time.sleep(espera)
    for intento in range(reintentos + 1):
        try:
            _ultima_peticion[dominio] = time.time()
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                crudo = r.read()
                if crudo[:2] == b"\x1f\x8b":
                    crudo = gzip.decompress(crudo)
                if DEBUG:
                    print(f"   {time.time() - _ultima_peticion[dominio]:5.1f}s {url}", flush=True)
                return r.url, crudo.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if DEBUG:
                print(f"   HTTP {e.code} {url}", flush=True)
            if e.code in (403, 404, 410):
                return None, None
        except Exception as e:
            if DEBUG:
                print(f"   ERROR {e} {url}", flush=True)
        time.sleep(3 * (intento + 1))
    return None, None


# ---------- Lectura de precio en fichas de producto ----------

def _productos_ld(o):
    if isinstance(o, dict):
        if "Product" in str(o.get("@type")):
            yield o
        for v in o.values():
            yield from _productos_ld(v)
    elif isinstance(o, list):
        for v in o:
            yield from _productos_ld(v)


def _a_numero(v):
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").replace("€", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        n = round(float(s), 2)
        return n if 5 < n < 2000 else None
    except ValueError:
        return None


def leer_ficha(html_pagina):
    """Extrae nombre, precio (EUR), disponibilidad y EAN de una ficha de producto."""
    res = {"nombre": None, "precio": None, "disponible": None, "ean": None}
    for bloque in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html_pagina, re.S):
        try:
            datos = json.loads(bloque.strip(), strict=False)
        except Exception:
            continue
        for p in _productos_ld(datos):
            res["nombre"] = res["nombre"] or p.get("name")
            ean = p.get("gtin13") or p.get("gtin") or p.get("gtin12")
            if ean and re.fullmatch(r"\d{12,14}", str(ean)):
                res["ean"] = res["ean"] or str(ean)
            ofertas = p.get("offers")
            if isinstance(ofertas, dict) and ofertas.get("@type") == "AggregateOffer":
                ofertas = [{"price": ofertas.get("lowPrice"), "priceCurrency": ofertas.get("priceCurrency"),
                            "availability": ofertas.get("availability")}]
            for of in (ofertas if isinstance(ofertas, list) else [ofertas]):
                if not isinstance(of, dict):
                    continue
                if of.get("priceCurrency") not in (None, "EUR"):
                    continue
                precio = _a_numero(of.get("price") or (of.get("priceSpecification") or {}).get("price"))
                if precio and res["precio"] is None:
                    res["precio"] = precio
                    disp = str(of.get("availability", ""))
                    res["disponible"] = None if not disp else ("InStock" in disp or "LimitedAvailability" in disp)
    if res["precio"] is None:
        m = re.search(r'<meta[^>]+property="product:price:amount"[^>]+content="([\d.,]+)"', html_pagina)
        if m:
            res["precio"] = _a_numero(m.group(1))
    if res["ean"] is None:
        m = (re.search(r'itemprop="gtin13"[^>]*content="(\d{13})"', html_pagina)
             or re.search(r'\bEAN\b\W{0,20}(\d{13})\b', html_pagina))
        if m:
            res["ean"] = m.group(1)
    if res["nombre"] is None:
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html_pagina)
        if m:
            res["nombre"] = html.unescape(m.group(1))
    return res


# ---------- Normalización y emparejado de nombres ----------

def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def slug(texto):
    return normalizar(texto).replace(" ", "-")


# Palabras que distinguen variantes de un mismo modelo: si aparecen en el candidato
# pero no en la pala de referencia, no es la misma pala.
VARIANTES = {"woman", "women", "w", "mujer", "junior", "jr", "girl", "kids", "light", "comfort", "cmf",
             "hybrid", "hyb", "geo", "ctr", "ctrl", "control", "power", "attack", "lite", "soft", "hard", "pro",
             "plus", "team", "ltd", "limited", "edition", "xseries", "series", "x", "cloud", "tour", "finals",
             "pack", "llavero", "protector", "funda", "paletero", "mochila", "zapatillas", "camiseta",
             "grip", "overgrip", "bolsa", "mini", "replica", "carbon", "elite", "air", "luxury", "alum",
             "segunda", "mano", "usada", "usado", "reacondicionada", "demo", "test", "evo", "colours", "colors",
             "silhoutte", "silhouette", "max", "premier", "exclusive", "special", "custom", "personalizada",
             "pickleball", "tenis", "playa", "beach", "frontenis", "palette", "racket"}
RELLENO = {"pala", "padel", "de", "by", "the", "para", "palas", "y", "con"}
_es_anio = lambda t: bool(re.fullmatch(r"\d\d", t)) and 20 <= int(t) <= 30


def tokens_modelo(nombre):
    """Tokens significativos del nombre; los años se normalizan a 2 cifras (2026 -> 26)."""
    out = []
    for t in normalizar(nombre).split():
        if t in RELLENO:
            continue
        if re.fullmatch(r"20\d\d", t):
            t = t[2:]
        out.append(t)
    return out


def mismo_modelo(nombre_ref, nombre_candidato, marca=None, vocabulario=frozenset()):
    """True si el candidato es exactamente el mismo modelo que la referencia.

    - Debe contener todos los tokens de la referencia.
    - No puede tener palabras extra que identifiquen otra variante (lista VARIANTES) ni palabras
      que aparecen en los nombres de otros modelos del catálogo (vocabulario).
    - No puede tener números extra (versiones como '3.0') ni un año distinto.
    - Si la referencia no indica año y el candidato sí, no se puede asegurar: se rechaza
      (en ese caso solo el EAN puede confirmar que es la misma pala).
    El nombre del jugador ('Juan Tello') sí se permite, porque unas tiendas lo ponen y otras no.
    """
    ref = tokens_modelo(nombre_ref)
    cand = tokens_modelo(nombre_candidato)
    marca_n = normalizar(marca) if marca else None
    ref_set = set(ref)
    anios_ref = {t for t in ref if _es_anio(t)}
    anios_cand = {t for t in cand if _es_anio(t)}
    if anios_cand and anios_cand != anios_ref:
        return False
    if any(t not in cand for t in ref if t != marca_n and not (t in anios_ref and not anios_cand)):
        return False
    for t in set(cand) - ref_set:
        if t in VARIANTES or t in vocabulario:
            return False
        if t.isdigit() and len(t) <= 2:  # número de versión extra (p. ej. '3' de 'Viper 3.0')
            return False
    return True
