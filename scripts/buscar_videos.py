"""Busca reviews en YouTube de cada pala con la API oficial (YouTube Data API v3).

Necesita una clave de API gratuita: variable de entorno YOUTUBE_API_KEY o archivo clave_youtube.txt en la raíz
del proyecto (ese archivo no se sube a GitHub). Sin clave, el script no hace nada y la web muestra solo
un botón de búsqueda en YouTube.

Cuota gratuita: 10.000 unidades/día; cada búsqueda cuesta 100. Este script hace como mucho 80 búsquedas al
día y vuelve a buscar cada pala una vez al mes, así que nunca se pasa del límite.
"""
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

from comun import RAIZ, VARIANTES, guardar_json, leer_json, normalizar, tokens_modelo

API = "https://www.googleapis.com/youtube/v3/"
MAX_BUSQUEDAS_DIA = 80
REFRESCO_DIAS = 30
VIDEOS_POR_PALA = 3
PALABRAS_REVIEW = {"review", "analisis", "prueba", "probamos", "test", "opinion", "opiniones", "unboxing",
                   "comparativa", "testeo", "probando", "reseña", "resena"}


def clave():
    if os.environ.get("YOUTUBE_API_KEY"):
        return os.environ["YOUTUBE_API_KEY"].strip()
    f = RAIZ / "clave_youtube.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def llamar(metodo, **params):
    url = API + metodo + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def segundos(iso):
    """'PT12M3S' -> 723"""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def es_del_modelo(pala, titulo, contexto=""):
    """El vídeo debe ser de pádel y nombrar exactamente este modelo.

    - 'pádel'/'pala' en el título, el canal o la descripción (contexto), y nunca 'tenis'.
    - Todos los tokens del modelo (salvo marca y año) en un mismo trozo del título (los trozos se
      separan por | // : - ...). En ese trozo no puede haber otra variante (Hybrid, Light, Woman...),
      otro número de versión (Piton 8.0) ni otro año.
    """
    marca = normalizar(pala["marca"])
    es_anio = lambda t: bool(re.fullmatch(r"\d\d", t)) and 20 <= int(t) <= 30
    if re.search(r"[Ѐ-ӿ؀-ۿ一-鿿]", titulo):  # cirílico, árabe, chino
        return False
    todo = normalizar(f"{titulo} {contexto}")
    if re.search(r"\b(tenis|tennis)\b", todo) or not re.search(r"\b(padel|pala|palas)\b", todo):
        return False
    ref = tokens_modelo(pala["nombre"])
    nucleo = [t for t in ref if t != marca and not es_anio(t)]
    anios_ref = {t for t in ref if es_anio(t)}
    for trozo in re.split(r"\s[|/:\-–—]+\s|\s*//\s*|[|:]", titulo):
        tit = tokens_modelo(trozo)
        if not nucleo or not all(t in tit for t in nucleo):
            continue
        anios_tit = {t for t in tit if es_anio(t)}
        if anios_ref and anios_tit and not anios_ref & anios_tit:
            return False
        extras = set(tit) - set(ref)
        if extras & (VARIANTES - PALABRAS_REVIEW):
            return False
        return not any(t.isdigit() and len(t) <= 2 and not es_anio(t) for t in extras)
    return False


def buscar(pala, k):
    modelo = " ".join(t for t in pala["nombre"].split() if not re.fullmatch(r"by", t, re.I))
    res = llamar("search", key=k, part="snippet", type="video", maxResults=15, q=f"{modelo} pádel review",
                 relevanceLanguage="es", regionCode="ES", videoEmbeddable="true", safeSearch="strict")
    candidatos = []
    for it in res.get("items", []):
        titulo = html.unescape(it["snippet"]["title"])
        contexto = f'{it["snippet"]["channelTitle"]} {it["snippet"].get("description", "")}'
        if es_del_modelo(pala, titulo, contexto):
            candidatos.append({"id": it["id"]["videoId"], "titulo": titulo,
                               "canal": html.unescape(it["snippet"]["channelTitle"]),
                               "fecha": it["snippet"]["publishedAt"][:10]})
    if not candidatos:
        return []
    # Duración (descarta shorts) y visualizaciones: 1 unidad de cuota por llamada
    det = llamar("videos", key=k, part="contentDetails,statistics", id=",".join(c["id"] for c in candidatos))
    info = {v["id"]: v for v in det.get("items", [])}
    buenos = []
    for pos, c in enumerate(candidatos):
        v = info.get(c["id"])
        if not v or segundos(v["contentDetails"].get("duration")) < 120:
            continue
        c["vistas"] = int(v.get("statistics", {}).get("viewCount", 0))
        es_review = bool(set(tokens_modelo(c["titulo"])) & PALABRAS_REVIEW)
        c["_orden"] = (not es_review, pos)  # primero las que se presentan como review, luego por relevancia
        buenos.append(c)
    buenos.sort(key=lambda c: c["_orden"])
    for c in buenos:
        c.pop("_orden")
    return buenos[:VIDEOS_POR_PALA]


def main():
    k = clave()
    if not k:
        print("Sin clave de YouTube: no se buscan vídeos (la web mostrará el botón de búsqueda).")
        return
    videos = leer_json("videos.json", {})
    cuota = videos.setdefault("_cuota", {})
    hoy = date.today().isoformat()
    if cuota.get("fecha") != hoy:
        cuota.update(fecha=hoy, busquedas=0)

    for pala in leer_json("catalogo.json", []):
        if cuota["busquedas"] >= MAX_BUSQUEDAS_DIA:
            print("Límite diario de búsquedas alcanzado; se continuará en la próxima ejecución.")
            break
        previo = videos.get(pala["id"])
        if previo and (date.today() - date.fromisoformat(previo["buscado"])).days < REFRESCO_DIAS:
            continue
        try:
            encontrados = buscar(pala, k)
        except urllib.error.HTTPError as e:
            print(f"Error de la API de YouTube ({e.code}): {e.read().decode('utf-8', 'replace')[:200]}")
            break
        cuota["busquedas"] += 1
        videos[pala["id"]] = {"buscado": hoy, "videos": encontrados}
        print(f"{pala['nombre']}: {len(encontrados)} vídeo(s)")
    videos["_actualizado"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    guardar_json("videos.json", videos)


if __name__ == "__main__":
    main()
