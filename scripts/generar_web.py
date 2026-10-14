"""Genera la web estática completa en la carpeta web/ a partir de los datos.

No necesita servidor: la carpeta web/ se puede publicar tal cual (GitHub Pages, Cloudflare Pages, Netlify...).
"""
import html
import json
import re
import shutil
import urllib.parse
from datetime import datetime, timezone

import guias
from clasificar import NIVELES, TIPOS, clasificar, explicar, puntuaciones
from comun import RAIZ, leer_json

WEB = RAIZ / "web"
PLANTILLA = RAIZ / "plantilla"
e = html.escape


# ---------- Datos ----------

def cargar():
    config = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    tiendas = {t["id"]: t for t in leer_json("tiendas.json")}
    precios = leer_json("precios.json", {})
    historial = leer_json("historial.json", {})
    cupones = leer_json("cupones_manual.json", []) + leer_json("cupones.json", [])
    palas = []
    for p in leer_json("catalogo.json", []):
        ofertas = []
        for tid, o in precios.get(p["id"], {}).items():
            if tid in tiendas and o.get("precio") and "error" not in o:
                ofertas.append({**o, "tienda": tiendas[tid]})
        ofertas.sort(key=lambda o: (o.get("disponible") is False, o["precio"]))
        vigentes = [o for o in ofertas if o.get("disponible") is not False]
        if not vigentes:
            continue
        for o in ofertas:
            cupon = descuento_cupon(cupones, o["tienda"]["id"])
            if cupon:
                o["cupon"] = cupon["codigo"]
                o["precio_cupon"] = round(o["precio"] * (1 - cupon["pct"] / 100), 2)
        con_cupon = [o for o in vigentes if o.get("precio_cupon")]
        mejor_cupon = min(con_cupon, key=lambda o: o["precio_cupon"]) if con_cupon else None
        if mejor_cupon and mejor_cupon["precio_cupon"] >= vigentes[0]["precio"]:
            mejor_cupon = None
        clas = clasificar(p)
        clas["puntos"] = puntuaciones(p, clas)
        palas.append({**p, **clas, "ofertas": ofertas, "mejor": vigentes[0], "mejor_cupon": mejor_cupon,
                      "historial": historial.get(p["id"], {}),
                      "cupones": [c for c in cupones if c["tienda"] in {o["tienda"]["id"] for o in ofertas}]})
    palas.sort(key=lambda p: p.get("popularidad", 999))
    # Reviews de YouTube: las añadidas a mano (videos_manual.json) van primero
    automaticos = leer_json("videos.json", {})
    manuales = leer_json("videos_manual.json", {})
    for p in palas:
        lista = list(manuales.get(p["id"], [])) + automaticos.get(p["id"], {}).get("videos", [])
        vistos = set()
        p["videos"] = [v for v in lista if not (v["id"] in vistos or vistos.add(v["id"]))][:3]
    estado = leer_json("estado.json", {})
    return config, tiendas, palas, cupones, estado


def descuento_cupon(cupones, tienda_id):
    """Mayor descuento porcentual publicado por la tienda, o None."""
    mejores = []
    for c in cupones:
        m = re.search(r"(\d{1,2})\s?%", c.get("descripcion", ""))
        if c["tienda"] == tienda_id and m and 0 < int(m.group(1)) <= 50:
            mejores.append({**c, "pct": int(m.group(1))})
    return max(mejores, key=lambda c: c["pct"]) if mejores else None


def rel_tienda():
    """Los enlaces a tiendas solo se marcan como patrocinados si de verdad hay afiliación o publicidad."""
    return "sponsored nofollow noopener" if MONETIZA else "nofollow noopener"


def enlace_tienda(tienda, url):
    """Aplica el código de afiliado de la tienda, si lo hay.

    - Si el campo 'afiliado' contiene {url}, se usa como plantilla (redes tipo Awin/Tradedoubler).
    - Si no, se añade como parámetro (p. ej. 'tag=tuid-21' para Amazon).
    """
    af = tienda.get("afiliado") or ""
    if "{url}" in af:
        return af.replace("{url}", urllib.parse.quote(url, safe=""))
    if af:
        return url + ("&" if "?" in url else "?") + af
    return url


def euros(n):
    return f"{n:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------- Piezas visuales ----------

def silueta(forma, clase="silueta"):
    forma = (forma or "").lower()
    if "redonda" in forma:
        cabeza = '<ellipse cx="40" cy="44" rx="31" ry="34"/>'
    elif "diamante" in forma:
        cabeza = '<path d="M40 6 C58 6 72 16 72 34 C72 52 56 70 40 80 C24 70 8 52 8 34 C8 16 22 6 40 6Z"/>'
    else:  # lágrima / híbrida
        cabeza = '<path d="M40 7 C60 7 72 22 72 40 C72 60 58 76 40 80 C22 76 8 60 8 40 C8 22 20 7 40 7Z"/>'
    agujeros = "".join(f'<circle cx="{x}" cy="{y}" r="2.2" class="hueco"/>'
                       for y in (26, 38, 50) for x in (28, 40, 52))
    return (f'<svg class="{clase}" viewBox="0 0 80 124" aria-hidden="true">'
            f'<g class="cabeza">{cabeza}</g>{agujeros}'
            f'<rect x="35" y="80" width="10" height="40" rx="4" class="puno"/></svg>')


MOSTRAR_FOTOS = True  # se toma de config.json en main()
MONETIZA = False  # True si hay AdSense o algún enlace de afiliado configurado


def url_foto(p, tam):
    """Foto del producto servida por la tienda de origen, redimensionada a tam x tam píxeles."""
    u = html.unescape(p.get("imagen_origen") or "")
    if not u or not MOSTRAR_FOTOS:
        return None
    return re.sub(r"(width|height)=\d+", lambda m: f"{m.group(1)}={tam}",
                  re.sub(r"canvas=\d+:\d+", f"canvas={tam}:{tam}", u))


def figura(p, clase="", tam=220, alt=None):
    """Foto real de la pala; si no hay o no carga, se ve la silueta dibujada."""
    forma = p.get("caracteristicas", {}).get("Forma")
    dibujo = silueta(forma, "silueta grande" if "grande" in clase else "silueta")
    foto = url_foto(p, tam)
    if not foto:
        return dibujo
    texto_alt = p["nombre"] if alt is None else alt  # alt="" cuando el nombre ya está escrito al lado
    return (f'<span class="foto {clase}"><img src="{e(foto)}" alt="{e(texto_alt)}" loading="lazy" '
            f'referrerpolicy="no-referrer" onerror="this.parentNode.classList.add(\'foto-error\')">{dibujo}</span>')


def barra_indice(indice):
    return (f'<div class="indice" title="Índice potencia/control: {indice}/100">'
            f'<span>Control</span><div class="pista"><i style="left:{indice}%"></i></div><span>Potencia</span></div>')


def grafico_historial(hist):
    puntos = sorted(hist.items())[-90:]
    if len(puntos) < 2:
        return '<p class="nota">El historial de precios se irá dibujando a medida que pasen los días.</p>'
    valores = [v for _, v in puntos]
    lo, hi = min(valores), max(valores)
    rango = (hi - lo) or 1
    ancho, alto = 600, 160
    coords = [(i * ancho / (len(puntos) - 1), 10 + (hi - v) * (alto - 20) / rango) for i, (_, v) in enumerate(puntos)]
    linea = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    return (f'<svg class="historial" viewBox="0 0 {ancho} {alto}" preserveAspectRatio="none" role="img" '
            f'aria-label="Precio mínimo diario: entre {euros(lo)} y {euros(hi)}">'
            f'<polyline points="{linea}"/></svg>'
            f'<div class="historial-ejes"><span>{puntos[0][0]}</span><span>mín. {euros(lo)} · máx. {euros(hi)}</span>'
            f'<span>{puntos[-1][0]}</span></div>')


def bloque_videos(p):
    """Reviews de YouTube: miniatura que se convierte en reproductor al pulsarla (sin cookies hasta entonces)."""
    busqueda = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(f'{p["nombre"]} review')
    tarjetas = "".join(f'''<button class="video" type="button" data-video="{e(v["id"])}" aria-label="Reproducir: {e(v.get("titulo", ""))}">
    <span class="video-mini"><img src="https://i.ytimg.com/vi/{e(v["id"])}/hqdefault.jpg" alt="" loading="lazy"><span class="video-play">▶</span></span>
    <span class="video-titulo">{e(v.get("titulo", "Review en YouTube"))}</span>
    <span class="video-canal">{e(v.get("canal", ""))}{" · " + e(v["fecha"][:4]) if v.get("fecha") else ""}</span></button>'''
                       for v in p["videos"])
    intro = ("Vídeos de otros jugadores y tiendas sobre esta pala, seleccionados automáticamente (pueden contener "
             "errores). Los vídeos pertenecen a sus autores y se alojan en YouTube."
             if p["videos"] else "Todavía no hemos seleccionado vídeos de esta pala.")
    return f'''<h2>Reviews en vídeo</h2>
  <p class="nota">{intro}</p>
  {f'<div class="videos">{tarjetas}</div><p class="aviso-video">Al pulsar ▶ se carga el reproductor de YouTube (Google), que puede usar cookies y tratar datos según su <a href="https://policies.google.com/privacy" target="_blank" rel="nofollow noopener">política de privacidad</a>. Más información en nuestra <a href="cookies.html">política de cookies</a>.</p>' if tarjetas else ""}
  <p><a class="boton boton-secundario" href="{e(busqueda)}" target="_blank" rel="nofollow noopener">▶ Ver más reviews en YouTube <span class="solo-lectores">(se abre en una pestaña nueva)</span></a></p>'''


def tarjeta(p):
    c = p.get("caracteristicas", {})
    niveles = " ".join(p["niveles"])
    tiendas_n = len([o for o in p["ofertas"] if o.get("disponible") is not False])
    return f'''<a class="tarjeta" href="pala-{p["id"]}.html" data-tipo="{p["tipo"]}" data-niveles="{niveles}"
  data-marca="{e(p["marca"])}" data-precio="{p["mejor"]["precio"]}" data-indice="{p["indice"]}" data-pop="{p.get("popularidad", 999)}">
  {figura(p, "foto-tarjeta", 220, alt="")}
  <div class="tarjeta-cuerpo">
    <span class="etiqueta tipo-{p["tipo"]}">{TIPOS[p["tipo"]]["nombre"]}</span>
    <h3>{e(p["nombre"])}</h3>
    <p class="meta">{e(" · ".join(NIVELES[n]["nombre"] for n in p["niveles"]))}</p>
    {barra_indice(p["indice"])}
    <div class="precio-fila"><span class="desde">desde</span> <strong>{euros(p["mejor"]["precio"])}</strong>
      <span class="en">en {e(p["mejor"]["tienda"]["nombre"])}</span></div>
    <p class="meta">Comparada en {tiendas_n} tienda{"s" if tiendas_n != 1 else ""}</p>
  </div>
</a>'''


def rejilla(palas):
    return '<div class="rejilla" id="rejilla">' + "".join(tarjeta(p) for p in palas) + "</div>"


# ---------- Maquetación ----------

def pagina(cfg, ruta, titulo, descripcion, cuerpo, estado, jsonld=None):
    adsense = ""
    if cfg.get("adsense_cliente"):
        adsense = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
                   f'{e(cfg["adsense_cliente"])}" crossorigin="anonymous"></script>')
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    actualizado = estado.get("ultima_actualizacion", "")
    anio = datetime.now().year
    nav = "".join(f'<a href="{t["pagina"]}">{t["nombre"]}</a>' for t in TIPOS.values())
    return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{e(cfg["dominio"].rstrip("/"))}/{ruta}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 124'%3E%3Cellipse cx='40' cy='44' rx='31' ry='34' fill='%2316a34a'/%3E%3Crect x='35' y='80' width='10' height='40' rx='4' fill='%2316a34a'/%3E%3C/svg%3E">
<link rel="stylesheet" href="estilos.css">
{adsense}
{ld}
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<header class="cabecera">
  <div class="contenedor cabecera-fila">
    <a class="logo" href="index.html" aria-label="{e(cfg["nombre_web"])}, página de inicio">{silueta("redonda", "logo-icono")}<span>{e(cfg["nombre_web"])}</span></a>
    <nav class="menu" aria-label="Menú principal">{nav}<a href="comparador.html" class="menu-destacado">Comparador gráfico</a><a href="guias.html">Guías</a><a href="cupones.html">Cupones</a></nav>
  </div>
</header>
<main class="contenedor" id="contenido" tabindex="-1">
{cuerpo}
</main>
<footer class="pie">
  <div class="contenedor">
    <p class="actualizado" data-fecha="{e(actualizado)}">Precios actualizados automáticamente cada pocas horas.</p>
    <p class="aviso-afiliado">{e(cfg["nombre_web"])} es un comparador informativo: no vende productos. Los precios
      pueden variar en la tienda en el momento de la compra y la venta, el envío, la garantía y las devoluciones son
      responsabilidad de cada tienda.{
      " Algunos enlaces son de afiliado: si compras a través de ellos, podemos recibir una pequeña comisión sin coste adicional para ti."
      if MONETIZA else " No cobramos a las tiendas ni a los usuarios: compra donde prefieras."}</p>
    <nav class="pie-enlaces" aria-label="Información legal"><a href="sobre-nosotros.html">Sobre nosotros</a>
      <a href="terminos.html">Términos y condiciones</a><a href="terminos.html#compras">Compras y devoluciones</a>
      <a href="aviso-legal.html">Aviso legal</a><a href="privacidad.html">Privacidad</a><a href="cookies.html">Cookies</a>
      <a href="accesibilidad.html">Accesibilidad</a></nav>
    <p>© {anio} {e(cfg["nombre_web"])}</p>
  </div>
</footer>
<script src="app.js"></script>
</body>
</html>'''


def filtros(palas, tipo_fijo=None, nivel_fijo=None):
    marcas = sorted({p["marca"] for p in palas})
    opt_tipo = "".join(f'<option value="{k}"{" selected" if k == tipo_fijo else ""}>{v["nombre"]}</option>'
                       for k, v in TIPOS.items())
    opt_nivel = "".join(f'<option value="{k}"{" selected" if k == nivel_fijo else ""}>{v["nombre"]}</option>'
                        for k, v in NIVELES.items())
    opt_marca = "".join(f'<option value="{e(m)}">{e(m)}</option>' for m in marcas)
    campo_tipo = "" if tipo_fijo else \
        f'<label>Tipo de juego<select name="tipo"><option value="">Todos</option>{opt_tipo}</select></label>'
    campo_nivel = "" if nivel_fijo else \
        f'<label>Nivel<select name="nivel"><option value="">Todos</option>{opt_nivel}</select></label>'
    return f'''<form class="filtros" id="filtros" onsubmit="return false">
  {campo_tipo}{campo_nivel}
  <label>Marca<select name="marca"><option value="">Todas</option>{opt_marca}</select></label>
  <label>Precio máximo<select name="precio"><option value="">Sin límite</option>
    <option value="80">80 €</option><option value="120">120 €</option><option value="160">160 €</option>
    <option value="200">200 €</option><option value="250">250 €</option></select></label>
  <label>Ordenar<select name="orden"><option value="pop">Destacadas</option><option value="precio">Precio más bajo</option>
    <option value="potencia">Más potencia</option><option value="control">Más control</option></select></label>
</form>
<p class="contador" id="contador"></p>'''


# ---------- Páginas ----------

def representante(palas, tipo):
    """Pala que ilustra un tipo de juego: la más popular con foto entre las más claramente de ese tipo."""
    centro = {"potencia": 100, "hibrida": 50, "control": 0}[tipo]
    candidatas = [p for p in palas if p["tipo"] == tipo and url_foto(p, 220)]
    if not candidatas:
        return None
    claras = [p for p in candidatas if abs(p["indice"] - centro) <= 20] or candidatas
    return min(claras, key=lambda p: p.get("popularidad", 999))


def portada(cfg, palas, cupones, estado, guias_disponibles=()):
    cajas = []
    for k, v in TIPOS.items():
        rep = representante(palas, k)
        imagen = (figura(rep, "foto-tipo", 220, alt="") if rep
                  else silueta({"potencia": "diamante", "hibrida": "lagrima", "control": "redonda"}[k]))
        ejemplo = f'<small>Ej.: {e(rep["nombre"])}</small>' if rep else ""
        cajas.append(f'''<a class="tipo-caja tipo-{k}" href="{v["pagina"]}">
      {imagen}
      <strong>{v["plural"]}</strong><span>{sum(1 for p in palas if p["tipo"] == k)} palas comparadas</span>{ejemplo}</a>''')
    tarjetas_tipo = "".join(cajas)
    bloque_guias = ""
    if guias_disponibles:
        bloque_guias = ('<section><h2>Guías de compra</h2><div class="g-tarjetas">' + "".join(
            f'<a class="g-tarjeta" href="{r}"><strong>{e(t)}</strong><span>{e(s)}</span></a>'
            for r, t, s in guias_disponibles) + '</div></section>')
    banner = ""
    if cupones:
        banner = (f'<a class="banner-cupon" href="cupones.html">🏷️ Hay {len(cupones)} código'
                  f'{"s" if len(cupones) != 1 else ""} de descuento activo{"s" if len(cupones) != 1 else ""}. Ver cupones →</a>')
    cuerpo = f'''
<section class="hero">
  <h1>Encuentra tu pala de pádel al mejor precio</h1>
  <p>Comparamos {len(palas)} palas en {len({o["tienda"]["id"] for p in palas for o in p["ofertas"]})} tiendas online de pádel,
     las clasificamos por tipo de juego y nivel y te mostramos qué tienda tiene el precio más bajo según nuestra última
     actualización.</p>
  <a class="boton boton-principal" href="comparador.html">📊 Abrir el comparador gráfico</a>
</section>
{banner}
<section class="tipos">{tarjetas_tipo}</section>
<section>
  <h2>Todas las palas</h2>
  {filtros(palas)}
  {rejilla(palas)}
</section>
{bloque_guias}
<section class="explicacion">
  <h2>¿Cómo clasificamos las palas?</h2>
  <p>Cada pala recibe un <strong>índice de potencia/control de 0 a 100</strong> calculado a partir de su forma,
     su balance, la dureza del núcleo y el tipo de juego que declara el fabricante. Por debajo de 38 la consideramos
     de control, por encima de 62 de potencia, y entre medias híbrida. <a href="guia-elegir-pala.html">Lee la guía completa →</a></p>
</section>'''
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": cfg["nombre_web"], "url": cfg["dominio"]}
    return pagina(cfg, "", f'{cfg["nombre_web"]} · Comparador de palas de pádel',
                  cfg["eslogan"], cuerpo, estado, ld)


TEXTOS_TIPO = {
    "potencia": ("Las palas de potencia suelen tener forma de diamante y balance alto: el peso se concentra en la cabeza "
                 "y el punto dulce está más arriba. Dan más salida de bola en remates y bandejas, pero exigen técnica "
                 "y pueden castigar el codo si no se tiene un buen gesto. Son para jugadores de nivel medio-alto que "
                 "suelen jugar en el lado del revés y terminan los puntos."),
    "hibrida": ("Las palas híbridas o polivalentes suelen tener forma de lágrima y balance medio. Buscan un equilibrio "
                "entre pegada y precisión, por eso son la opción más versátil: sirven tanto para defender desde el fondo "
                "como para atacar en la red. Son una apuesta segura si no tienes claro tu estilo de juego."),
    "control": ("Las palas de control suelen ser redondas, con balance bajo y un punto dulce amplio y centrado. Son más "
                "manejables, perdonan los golpes descentrados y ayudan a colocar la bola con precisión. Son ideales para "
                "quien empieza, para jugadores de drive y para cualquiera que priorice la defensa y la regularidad."),
}


def pagina_tipo(cfg, palas, tipo, estado):
    t = TIPOS[tipo]
    lista = [p for p in palas if p["tipo"] == tipo]
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › {t["plural"]}</nav>
<h1>{t["plural"]}: comparativa y mejores precios</h1>
<p class="intro">{TEXTOS_TIPO[tipo]}</p>
{filtros(lista, tipo_fijo=tipo)}
{rejilla(lista)}'''
    return pagina(cfg, t["pagina"], f'{t["plural"]} {datetime.now().year}: comparativa y precios · {cfg["nombre_web"]}',
                  f'Comparamos {len(lista)} {t["plural"].lower()} y su precio en varias tiendas online de pádel de España.',
                  cuerpo, estado)


TEXTOS_NIVEL = {
    "iniciacion": ("Si estás empezando o juegas de forma ocasional, busca una pala manejable, con núcleo blando o medio "
                   "y punto dulce amplio. Te ayudará a coger confianza, cuidará tu brazo y no hace falta gastar mucho."),
    "avanzado": ("Para jugadores que compiten en torneos amateur o juegan varias veces por semana: palas con materiales "
                 "de mayor calidad (carbono), núcleos más duros y más precisión en el golpeo."),
    "profesional": ("Las palas tope de gama, usadas por los jugadores profesionales. Núcleos duros y materiales premium "
                    "que exigen una técnica muy depurada para sacarles partido."),
}


def pagina_nivel(cfg, palas, nivel, estado):
    n = NIVELES[nivel]
    lista = [p for p in palas if nivel in p["niveles"]]
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › Nivel {n["nombre"]}</nav>
<h1>Palas de pádel para nivel {n["nombre"].lower()}</h1>
<p class="intro">{TEXTOS_NIVEL[nivel]}</p>
{filtros(lista, nivel_fijo=nivel)}
{rejilla(lista)}'''
    total = len(lista)
    return pagina(cfg, n["pagina"], f'Palas de pádel nivel {n["nombre"].lower()} · {cfg["nombre_web"]}',
                  f'{total} palas de pádel recomendadas para nivel {n["nombre"].lower()}, con su precio en cada tienda.',
                  cuerpo, estado)


def pagina_pala(cfg, p, palas, tiendas, estado):
    c = p.get("caracteristicas", {})
    filas = []
    for o in p["ofertas"]:
        mejor = o is p["mejor"]
        agotada = o.get("disponible") is False
        filas.append(f'''<tr class="{"mejor" if mejor else ""}{" agotada" if agotada else ""}">
  <td class="tienda">{e(o["tienda"]["nombre"])}{' <span class="sello">Más barata</span>' if mejor else ""}</td>
  <td class="precio">{euros(o["precio"])}{" <small>Agotada</small>" if agotada else ""}{
      f'<span class="con-cupon">{euros(o["precio_cupon"])} con <code>{e(o["cupon"])}</code></span>' if o.get("precio_cupon") and not agotada else ""}</td>
  <td class="hora" data-fecha="{e(o["actualizado"])}"></td>
  <td><a class="boton{" boton-principal" if mejor else ""}" href="{e(enlace_tienda(o["tienda"], o["url"]))}"
     target="_blank" rel="{rel_tienda()}">Ir a la tienda<span class="solo-lectores"> {e(o["tienda"]["nombre"])} a ver {e(p["nombre"])} (se abre en una pestaña nueva)</span></a></td></tr>''')
    con_precio = {o["tienda"]["id"] for o in p["ofertas"]}
    for t in tiendas.values():
        if t["id"] in con_precio:
            continue
        q = urllib.parse.quote_plus(p["nombre"])
        url = t["busqueda"].format(q=q)
        motivo = "Consultar precio" if t["modo"] == "solo_enlace" else "Buscar en la tienda"
        filas.append(f'''<tr class="sin-precio"><td class="tienda">{e(t["nombre"])}</td>
  <td class="precio">—</td><td class="hora"></td>
  <td><a class="boton boton-secundario" href="{e(enlace_tienda(t, url))}" target="_blank" rel="{rel_tienda()}">{motivo}<span class="solo-lectores"> en {e(t["nombre"])} (se abre en una pestaña nueva)</span></a></td></tr>''')

    cupones_html = ""
    if p["cupones"]:
        items = "".join(f'<li><strong>{e(tiendas[cu["tienda"]]["nombre"])}</strong>: código <code>{e(cu["codigo"])}</code>'
                        f'{" — " + e(cu.get("descripcion", "")) if cu.get("descripcion") else ""}</li>' for cu in p["cupones"])
        cupones_html = f'<div class="cupones-pala"><h3>🏷️ Códigos de descuento en estas tiendas</h3><ul>{items}</ul>' \
                       f'<p class="nota">Comprueba las condiciones en la tienda: algunos códigos no se aplican a palas o productos rebajados.</p></div>'

    fichas = [("Forma", c.get("Forma")), ("Balance", c.get("Balance")), ("Núcleo", c.get("Núcleo")),
              ("Dureza", c.get("Dureza")), ("Cara", c.get("Cara")), ("Superficie", c.get("Superfície")),
              ("Acabado", c.get("Acabado")), ("Jugador", c.get("Jugador")), ("Colección", c.get("Colección Jugadores")),
              ("Tipo de juego (fabricante)", c.get("Tipo de Juego")), ("Nivel (fabricante)", c.get("Nivel de Juego")),
              ("EAN", p.get("ean"))]
    tabla_ficha = "".join(f"<tr><th>{k}</th><td>{e(v)}</td></tr>" for k, v in fichas if v)

    similares = [q for q in palas if q["id"] != p["id"] and q["tipo"] == p["tipo"]
                 and set(q["niveles"]) & set(p["niveles"])]
    similares.sort(key=lambda q: abs(q["mejor"]["precio"] - p["mejor"]["precio"]))
    ahorro = p["ofertas"][-1]["precio"] - p["mejor"]["precio"] if len(p["ofertas"]) > 1 else 0
    ahorro_txt = (f' Entre las tiendas comparadas, la diferencia entre el precio más bajo y el más alto es de <strong>{euros(ahorro)}</strong>.'
                  if ahorro >= 1 else "")
    t = TIPOS[p["tipo"]]

    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › <a href="{t["pagina"]}">{t["plural"]}</a> › {e(p["nombre"])}</nav>
<article class="ficha">
  <div class="ficha-cabecera">
    <div class="ficha-foto">{figura(p, "grande", 500)}{
        f'<a class="credito" href="{e(p["urls"]["padelnuestro"])}" target="_blank" rel="nofollow noopener">Imagen: Padel Nuestro <span class="solo-lectores">(se abre en una pestaña nueva)</span></a>'
        if url_foto(p, 500) and p.get("urls", {}).get("padelnuestro") else ""}</div>
    <div>
      <span class="etiqueta tipo-{p["tipo"]}">{t["nombre"]}</span>
      <h1>{e(p["nombre"])}</h1>
      <p class="meta">{e(p["marca"])} · Nivel {e(", ".join(NIVELES[n]["nombre"] for n in p["niveles"]))}</p>
      <div class="precio-grande">desde <strong>{euros(p["mejor"]["precio"])}</strong> en {e(p["mejor"]["tienda"]["nombre"])}</div>
      {f'<p class="aviso-cupon">🏷️ O <strong>{euros(p["mejor_cupon"]["precio_cupon"])}</strong> en {e(p["mejor_cupon"]["tienda"]["nombre"])} aplicando el código <code>{e(p["mejor_cupon"]["cupon"])}</code> (sujeto a las condiciones de la tienda).</p>' if p["mejor_cupon"] else ""}
      {barra_indice(p["indice"])}
      <p>{e(explicar(p, p))}{ahorro_txt}</p>
      <a class="boton" href="comparador.html?p={p["id"]}">📊 Comparar con otras palas</a>
    </div>
  </div>

  <h2>Comparativa de precios</h2>
  <div class="tabla-scroll"><table class="precios">
    <thead><tr><th>Tienda</th><th>Precio</th><th>Actualizado</th><th></th></tr></thead>
    <tbody>{"".join(filas)}</tbody>
  </table></div>
  {cupones_html}

  <h2>Evolución del precio más bajo</h2>
  {grafico_historial(p["historial"])}

  <h2>Características técnicas</h2>
  <table class="ficha-tecnica">{tabla_ficha}</table>

  {bloque_videos(p)}

  {"<h2>Palas similares</h2>" + rejilla(similares[:4]) if similares else ""}
</article>'''
    ofertas_ld = [{"@type": "Offer", "price": o["precio"], "priceCurrency": "EUR", "url": o["url"],
                   "seller": {"@type": "Organization", "name": o["tienda"]["nombre"]},
                   "availability": "https://schema.org/" + ("OutOfStock" if o.get("disponible") is False else "InStock")}
                  for o in p["ofertas"]]
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["nombre"],
          "brand": {"@type": "Brand", "name": p["marca"]},
          "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": p["mejor"]["precio"],
                     "highPrice": max(o["precio"] for o in p["ofertas"]), "offerCount": len(p["ofertas"]),
                     "offers": ofertas_ld}}
    if p.get("ean"):
        ld["gtin13"] = p["ean"]
    return pagina(cfg, f'pala-{p["id"]}.html',
                  f'{p["nombre"]}: precio más barato y comparativa · {cfg["nombre_web"]}',
                  f'{p["nombre"]} desde {euros(p["mejor"]["precio"])}. Compara su precio en {len(p["ofertas"])} tiendas, '
                  f'características y tipo de juego ({t["nombre"].lower()}).', cuerpo, estado, ld)


def pagina_comparador(cfg, palas, estado):
    """Comparador gráfico: hasta 3 palas en un radar de 5 ejes + tabla enfrentada."""
    datos = []
    for p in palas:
        c = p.get("caracteristicas", {})
        datos.append({
            "id": p["id"], "nombre": p["nombre"], "marca": p["marca"], "tipo": TIPOS[p["tipo"]]["nombre"],
            "nivel": ", ".join(NIVELES[n]["nombre"] for n in p["niveles"]), "indice": p["indice"],
            "forma": c.get("Forma", "—"), "balance": c.get("Balance", "—"), "cara": c.get("Cara", "—"),
            "nucleo": c.get("Núcleo", "—"), "dureza_txt": c.get("Dureza", "—"),
            "puntos": puntuaciones(p, p), "precio": p["mejor"]["precio"],
            "tienda": p["mejor"]["tienda"]["nombre"], "foto": url_foto(p, 400),
            "silueta": "diamante" if "diamante" in (c.get("Forma") or "").lower()
            else "redonda" if "redonda" in (c.get("Forma") or "").lower() else "lagrima",
        })
    # Por defecto: la más popular de cada tipo, para que la página ya diga algo al abrirla
    por_defecto = [next(p["id"] for p in palas if p["tipo"] == t) for t in TIPOS if any(q["tipo"] == t for q in palas)]
    siluetas = {f: silueta(f, "silueta grande") for f in ("diamante", "lagrima", "redonda")}
    selectores = "".join(f'''<div class="hueco-pala serie-{i}">
    <label for="pala{i}">Pala {i + 1}</label>
    <div class="campo"><input id="pala{i}" type="search" placeholder="🔍 Busca marca o modelo…" autocomplete="off" spellcheck="false"></div>
    <div class="hueco-figura"></div></div>''' for i in range(3))
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › Comparador gráfico</nav>
<h1>Comparador gráfico de palas</h1>
<p class="intro">Elige hasta tres palas y compara de un vistazo su potencia, control, manejo, salida de bola y dureza.</p>
<section class="comparador">
  <div class="huecos">{selectores}</div>
  <div class="radar-caja"><svg id="radar" viewBox="-170 -150 340 300" role="img" aria-label="Gráfico de radar que compara las palas elegidas. Los mismos datos aparecen en la tabla siguiente."></svg></div>
  <div class="tabla-scroll"><table class="tabla-comparar" id="tabla-comparar"></table></div>
  <p class="nota">Puntuaciones de 1 a 10 <strong>estimadas por {e(cfg["nombre_web"])}</strong> a partir de las características
    técnicas publicadas (forma, balance, núcleo, dureza y material de la cara); no son pruebas en pista.
    Sirven para comparar palas entre sí. <a href="guia-elegir-pala.html">¿Qué significa cada característica?</a></p>
  <button class="boton" id="compartir" type="button">Copiar enlace de esta comparativa</button>
</section>
<script>
window.PALAS = {json.dumps(datos, ensure_ascii=False)};
window.SILUETAS = {json.dumps(siluetas)};
window.POR_DEFECTO = {json.dumps(por_defecto)};
</script>
<script src="comparador.js"></script>'''
    return pagina(cfg, "comparador.html", f'Comparador gráfico de palas de pádel · {cfg["nombre_web"]}',
                  "Compara hasta tres palas de pádel en un gráfico: potencia, control, manejo, salida de bola y dureza.",
                  cuerpo, estado)


def pagina_cupones(cfg, cupones, tiendas, estado):
    if cupones:
        items = "".join(f'''<div class="cupon"><strong>{e(tiendas[c["tienda"]]["nombre"])}</strong>
  <code>{e(c["codigo"])}</code><p>{e(c.get("descripcion") or c.get("texto", ""))}</p>
  <a class="boton" href="{e(enlace_tienda(tiendas[c["tienda"]], tiendas[c["tienda"]]["web"]))}" target="_blank"
     rel="{rel_tienda()}">Ir a {e(tiendas[c["tienda"]]["nombre"])}<span class="solo-lectores"> (se abre en una pestaña nueva)</span></a></div>''' for c in cupones if c["tienda"] in tiendas)
    else:
        items = '<p>Ahora mismo no hemos detectado códigos de descuento. Revisamos las tiendas cada pocas horas.</p>'
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › Cupones</nav>
<h1>Códigos de descuento en tiendas de pádel</h1>
<p class="intro">Revisamos automáticamente las portadas de las tiendas que comparamos, cada pocas horas, en busca de
códigos promocionales publicados. No tenemos acuerdos con las tiendas: un código puede haber caducado o no aplicarse a
todos los productos.
Comprueba siempre las condiciones en la tienda: muchos códigos excluyen productos ya rebajados.</p>
<div class="cupones">{items}</div>'''
    return pagina(cfg, "cupones.html", f'Cupones y códigos de descuento de pádel · {cfg["nombre_web"]}',
                  "Códigos promocionales detectados en las tiendas de pádel que comparamos.", cuerpo, estado)


def paginas_estaticas(cfg, estado):
    """Páginas de texto (guía, legales) desde plantilla/*.html, sustituyendo {{variables}}."""
    res = {}
    for f in sorted(PLANTILLA.glob("*.html")):
        texto = f.read_text(encoding="utf-8")
        titulo, descripcion, cuerpo = texto.split("\n---\n", 2)
        # Bloques condicionales: los datos del titular solo aparecen si están en config.json
        for condicion, activa in (("titular", bool(cfg.get("titular"))), ("monetiza", MONETIZA)):
            quitar, dejar = (f"sin-{condicion}", f"si-{condicion}") if activa else (f"si-{condicion}", f"sin-{condicion}")
            cuerpo = re.sub(rf"<!--{quitar}-->.*?<!--/{quitar}-->", "", cuerpo, flags=re.S)
            cuerpo = cuerpo.replace(f"<!--{dejar}-->", "").replace(f"<!--/{dejar}-->", "")
        for k, v in cfg.items():
            cuerpo = cuerpo.replace("{{" + k + "}}", e(str(v)))
        res[f.name] = pagina(cfg, f.name, f"{titulo.strip()} · {cfg['nombre_web']}", descripcion.strip(), cuerpo, estado)
    return res


def main():
    global MOSTRAR_FOTOS, MONETIZA
    cfg, tiendas, palas, cupones, estado = cargar()
    MOSTRAR_FOTOS = cfg.get("mostrar_fotos", True)
    MONETIZA = bool(cfg.get("adsense_cliente") or any(t.get("afiliado") for t in tiendas.values()))
    if MONETIZA and not cfg.get("titular"):
        print("AVISO: hay publicidad o enlaces de afiliado activos pero no hay titular en config.json. "
              "La LSSI obliga a identificar al titular de webs con actividad económica.")
    if WEB.exists():
        shutil.rmtree(WEB)
    WEB.mkdir()
    for estatico in ("estilos.css", "app.js", "comparador.js"):
        shutil.copy(PLANTILLA / "recursos" / estatico, WEB / estatico)

    ayudas = {"pagina": pagina, "figura": figura, "euros": euros, "e": e}
    paginas_guias, guias_disponibles = guias.generar(cfg, palas, estado, ayudas)
    salida = {"index.html": portada(cfg, palas, cupones, estado, guias_disponibles),
              "cupones.html": pagina_cupones(cfg, cupones, tiendas, estado),
              "comparador.html": pagina_comparador(cfg, palas, estado)}
    for tipo in TIPOS:
        salida[TIPOS[tipo]["pagina"]] = pagina_tipo(cfg, palas, tipo, estado)
    for nivel in NIVELES:
        salida[NIVELES[nivel]["pagina"]] = pagina_nivel(cfg, palas, nivel, estado)
    for p in palas:
        salida[f'pala-{p["id"]}.html'] = pagina_pala(cfg, p, palas, tiendas, estado)
    salida.update(paginas_estaticas(cfg, estado))
    salida.update(paginas_guias)

    for nombre, contenido in salida.items():
        (WEB / nombre).write_text(contenido, encoding="utf-8")

    dominio = cfg["dominio"].rstrip("/")
    hoy = datetime.now(timezone.utc).date().isoformat()
    urls = "".join(f"<url><loc>{dominio}/{'' if n == 'index.html' else n}</loc><lastmod>{hoy}</lastmod></url>"
                   for n in salida)
    (WEB / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        encoding="utf-8")
    (WEB / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {dominio}/sitemap.xml\n", encoding="utf-8")
    if cfg.get("adsense_cliente"):
        pub = cfg["adsense_cliente"].replace("ca-", "")
        (WEB / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    (WEB / ".nojekyll").write_text("", encoding="utf-8")
    host = urllib.parse.urlparse(dominio).netloc
    if host and "tu-dominio" not in host:
        (WEB / "CNAME").write_text(host + "\n", encoding="utf-8")  # dominio propio en GitHub Pages
    print(f"Web generada: {len(salida)} páginas, {len(palas)} palas con precio")


if __name__ == "__main__":
    main()
