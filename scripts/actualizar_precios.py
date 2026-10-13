"""Busca cada pala del catálogo en cada tienda y guarda su precio actual.

- La primera vez localiza la ficha de la pala en cada tienda (buscador o sitemap) y la recuerda.
- Comprueba que es la misma pala por EAN (código de barras) o, si no hay, por nombre exacto del modelo.
- Guarda precios en datos/precios.json y el mínimo diario en datos/historial.json.
Uso: python scripts/actualizar_precios.py [max_palas]
"""
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from comun import descargar, guardar_json, leer_ficha, leer_json, mismo_modelo, tokens_modelo, normalizar

MAX_CANDIDATOS = 3
_sitemaps = {}
_vocabulario = {}


def vocabulario_ajeno(pala, catalogo):
    """Palabras que aparecen en nombres de OTRAS palas del catálogo (p. ej. 'silhoutte', 'comfort').

    Si una ficha candidata contiene una de ellas y nuestra pala no, probablemente es otro modelo.
    Se excluyen marcas, años, números y nombres de jugadores (unas tiendas los ponen y otras no).
    """
    if not _vocabulario:
        jugadores, marcas, todas = set(), set(), set()
        for p in catalogo:
            jugadores |= set(tokens_modelo(p.get("caracteristicas", {}).get("Colección Jugadores", "")))
            marcas.add(normalizar(p["marca"]))
            todas |= set(tokens_modelo(p["nombre"]))
        _vocabulario["base"] = {t for t in todas - jugadores - marcas if not t.isdigit()}
    return _vocabulario["base"] - set(tokens_modelo(pala["nombre"]))


def consulta(pala):
    """Texto de búsqueda: marca + modelo sin años ni palabras de relleno."""
    toks = [t for t in tokens_modelo(pala["nombre"]) if not re.fullmatch(r"\d\d", t) or not 20 <= int(t) <= 30]
    return " ".join(toks)


def candidatos(tienda, pala):
    nucleo = [t for t in tokens_modelo(pala["nombre"])
              if t != normalizar(pala["marca"]) and not (re.fullmatch(r"\d\d", t) and 20 <= int(t) <= 30)]
    if tienda["modo"] == "sitemap":
        if tienda["id"] not in _sitemaps:
            _, xml = descargar(tienda["sitemap"])
            _sitemaps[tienda["id"]] = re.findall(r"<loc>(?:<!\[CDATA\[)?\s*([^<\]\s]+)", xml or "")
        enlaces = _sitemaps[tienda["id"]]
    else:
        _, pag = descargar(tienda["busqueda"].format(q=urllib.parse.quote_plus(consulta(pala))))
        if not pag:
            return []
        enlaces = re.findall(tienda["patron_producto"], pag.replace("&amp;", "&"))
    vistos = []
    for e in enlaces:
        e = e.split("?")[0].split("#")[0]
        if not re.fullmatch(tienda["patron_producto"], e):
            continue
        e = tienda.get("prefijo", "") + e
        if e in vistos:
            continue
        slug_toks = set(tokens_modelo(e.rsplit("/", 1)[-1].replace(".html", "")))
        if all(t in slug_toks for t in nucleo):
            vistos.append(e)
    # Prioriza las URLs que pasan el filtro estricto de variantes
    vistos.sort(key=lambda e: not mismo_modelo(pala["nombre"], e.rsplit("/", 1)[-1], pala["marca"], pala["_vocab"]))
    return vistos[:MAX_CANDIDATOS]


def leer_precio(tienda, url):
    _, pag = descargar(url + tienda.get("sufijo_precio", ""))
    return leer_ficha(pag) if pag else None


def es_la_misma(pala, ficha):
    if pala.get("ean") and ficha.get("ean"):
        return pala["ean"] == ficha["ean"]
    return bool(ficha.get("nombre")) and mismo_modelo(pala["nombre"], ficha["nombre"], pala["marca"], pala["_vocab"])


def main():
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
    tiendas = [t for t in leer_json("tiendas.json") if t["modo"] != "solo_enlace"]
    catalogo = leer_json("catalogo.json", [])[:limite]
    precios = leer_json("precios.json", {})
    historial = leer_json("historial.json", {})
    ahora = datetime.now(timezone.utc).isoformat(timespec="minutes")
    hoy = ahora[:10]

    def recorrer_tienda(tienda):
        """Procesa todas las palas en una tienda. Cada tienda va en su propio hilo."""
        tid = tienda["id"]
        for pala in catalogo:
            pid = pala["id"]
            url = pala.get("urls", {}).get(tid)
            ficha = None
            if url:
                ficha = leer_precio(tienda, url)
                if ficha and ficha["precio"] is None:
                    ficha = None
            elif pala.get("urls_descartadas", {}).get(tid) != hoy[:7]:  # reintenta buscar cada mes
                for cand in candidatos(tienda, pala):
                    f = leer_precio(tienda, cand)
                    if f and f["precio"] and es_la_misma(pala, f):
                        url, ficha = cand, f
                        pala.setdefault("urls", {})[tid] = cand
                        break
                if not url:
                    pala.setdefault("urls_descartadas", {})[tid] = hoy[:7]
            if ficha:
                if not pala.get("ean") and ficha.get("ean"):
                    pala["ean"] = ficha["ean"]
                precios[pid][tid] = {"precio": ficha["precio"], "disponible": ficha["disponible"],
                                     "url": url, "actualizado": ahora}
            elif tid in precios[pid] and url:
                precios[pid][tid]["error"] = ahora  # se mantiene el último precio conocido, marcado
        print(f"Tienda {tienda['nombre']}: terminada", flush=True)

    for pala in catalogo:
        precios.setdefault(pala["id"], {})
        pala["_vocab"] = vocabulario_ajeno(pala, catalogo)
    # Padel Nuestro primero: aporta el EAN que luego confirma las demás tiendas
    recorrer_tienda(tiendas[0])
    with ThreadPoolExecutor(max_workers=len(tiendas)) as hilos:
        list(hilos.map(recorrer_tienda, tiendas[1:]))

    for i, pala in enumerate(catalogo, 1):
        pid = pala["id"]
        vigentes = [p["precio"] for p in precios[pid].values() if p.get("disponible") is not False and "error" not in p]
        if vigentes:
            dia = historial.setdefault(pid, {})
            dia[hoy] = min(min(vigentes), dia.get(hoy, 10**6))
        resumen = ", ".join(f"{t}: {v['precio']}" for t, v in precios[pid].items())
        print(f"[{i}/{len(catalogo)}] {pala['nombre']} -> {resumen or 'sin precios'}")

    for pala in catalogo:
        pala.pop("_vocab", None)
    completo = {p["id"]: p for p in leer_json("catalogo.json", [])}
    completo.update({p["id"]: p for p in catalogo})
    guardar_json("catalogo.json", list(completo.values()))
    guardar_json("precios.json", precios)
    guardar_json("historial.json", historial)
    guardar_json("estado.json", {"ultima_actualizacion": ahora})


if __name__ == "__main__":
    main()
