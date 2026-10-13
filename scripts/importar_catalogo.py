"""Importa el catálogo de palas (con sus características técnicas) desde Padel Nuestro.

Recorre las primeras páginas del listado de palas (las más destacadas por la tienda),
entra en cada ficha y guarda forma, balance, núcleo, dureza, nivel, etc. en datos/catalogo.json.
Las palas ya importadas se conservan; solo se añaden las nuevas y se refrescan sus datos.
Uso: python scripts/importar_catalogo.py [numero_de_paginas]
"""
import html
import json
import re
import sys
from datetime import date

from comun import RAIZ, descargar, guardar_json, leer_ficha, leer_json, slug

LISTADO = "https://www.padelnuestro.com/palas-padel?p={p}"
EXCLUIR = re.compile(r"\b(junior|jr|girl|kids|nino|nina|pack|tenis playa|beach|outlet)\b", re.I)


def leer_caracteristicas(pagina):
    pares = re.findall(
        r'description-attributes-label">\s*(.*?)\s*</span>\s*<span class="description-attributes-value">\s*(.*?)\s*</span>',
        pagina, re.S)
    return {html.unescape(k).strip(): html.unescape(re.sub(r"\s+", " ", v)).strip() for k, v in pares}


def main():
    config = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    paginas = int(sys.argv[1]) if len(sys.argv) > 1 else config.get("paginas_catalogo", 5)
    catalogo = {p["id"]: p for p in leer_json("catalogo.json", [])}
    urls = []
    for n in range(1, paginas + 1):
        _, pag = descargar(LISTADO.format(p=n))
        if not pag:
            continue
        for a, b in re.findall(r'class="product-item-link"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="product-item-link"', pag):
            u = a or b
            if u not in urls:
                urls.append(u)
        print(f"Página {n}: {len(urls)} palas acumuladas")

    for pos, url in enumerate(urls, 1):
        _, pag = descargar(url)
        if not pag:
            continue
        ficha = leer_ficha(pag)
        car = leer_caracteristicas(pag)
        nombre = (ficha["nombre"] or "").strip()
        if not nombre or car.get("Producto", "Palas") != "Palas":
            continue
        if config.get("solo_palas_de_adulto") and (EXCLUIR.search(nombre) or car.get("Jugador", "").lower().startswith(("niñ", "jun"))):
            continue
        img = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', pag)
        pid = slug(nombre)
        previo = catalogo.get(pid, {})
        catalogo[pid] = {
            **previo,
            "id": pid,
            "nombre": nombre.title() if nombre.isupper() else nombre,
            "marca": car.get("Marca", nombre.split()[0].title()),
            "popularidad": pos,
            "ean": previo.get("ean") or ficha["ean"],
            "caracteristicas": car,
            "imagen_origen": html.unescape(img.group(1)) if img else None,
            "urls": {**previo.get("urls", {}), "padelnuestro": url},
            "alta": previo.get("alta") or date.today().isoformat(),
        }
        print(f"[{pos}/{len(urls)}] {nombre}")

    guardar_json("catalogo.json", sorted(catalogo.values(), key=lambda p: p.get("popularidad", 999)))
    print(f"Catálogo: {len(catalogo)} palas")


if __name__ == "__main__":
    main()
