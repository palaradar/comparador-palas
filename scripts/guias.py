"""Guías de compra generadas con los datos reales del catálogo.

Cada guía combina un texto propio con una selección de palas que se recalcula en cada actualización:
si cambia un precio o entra una pala que encaja mejor, la guía cambia sola.
Las selecciones se basan solo en datos publicados (forma, balance, dureza, material, precio y popularidad
en tienda) y en las puntuaciones estimadas del comparador; no son pruebas en pista.
"""
from datetime import datetime

from clasificar import NIVELES, TIPOS
from comun import normalizar

ANIO = datetime.now().year
EJES = [("potencia", "Potencia"), ("control", "Control"), ("manejo", "Manejo"),
        ("salida", "Salida de bola"), ("dureza", "Dureza")]


def _c(p, clave):
    return (p.get("caracteristicas", {}).get(clave) or "").strip()


def _barras(p):
    filas = "".join(f'<div class="g-barra"><span>{nombre}</span><i><b style="width:{p["puntos"][k] * 10}%"></b></i>'
                    f'<em>{str(p["puntos"][k]).replace(".", ",")}</em></div>' for k, nombre in EJES)
    return f'<div class="g-barras">{filas}</div>'


def _ficha(p, h, posicion, motivo):
    e, euros = h["e"], h["euros"]
    specs = " · ".join(x for x in (_c(p, "Forma"), f'balance {_c(p, "Balance").lower()}' if _c(p, "Balance") else "",
                                   f'goma {_c(p, "Dureza").lower()}' if _c(p, "Dureza") else "", _c(p, "Cara")) if x)
    return f'''<article class="g-pala" id="{p["id"]}">
  <div class="g-num">{posicion}</div>
  <a class="g-foto" href="pala-{p["id"]}.html">{h["figura"](p, "foto-guia", 220)}</a>
  <div class="g-cuerpo">
    <span class="etiqueta tipo-{p["tipo"]}">{TIPOS[p["tipo"]]["nombre"]}</span>
    <h3><a href="pala-{p["id"]}.html">{e(p["nombre"])}</a></h3>
    <p class="meta">{e(specs)} · Nivel {e(", ".join(NIVELES[n]["nombre"] for n in p["niveles"]))}</p>
    <p class="g-motivo">{motivo}</p>
    {_barras(p)}
    <div class="g-precio">desde <strong>{euros(p["mejor"]["precio"])}</strong> en {e(p["mejor"]["tienda"]["nombre"])}
      <a class="boton boton-principal" href="pala-{p["id"]}.html">Ver precios<span class="solo-lectores"> de {e(p["nombre"])}</span></a>
      <a class="boton" href="comparador.html?p={p["id"]}">Comparar<span class="solo-lectores"> {e(p["nombre"])} con otras palas</span></a></div>
  </div>
</article>'''


def _pagina_guia(cfg, estado, h, ruta, titulo, descripcion, intro, palas, motivo, metodo, cierre=""):
    e = h["e"]
    if not palas:
        return None
    indice = "".join(f'<li><a href="#{p["id"]}">{e(p["nombre"])}</a> — {h["euros"](p["mejor"]["precio"])}</li>'
                     for p in palas)
    fichas = "".join(_ficha(p, h, i, motivo(p)) for i, p in enumerate(palas, 1))
    hoy = (estado.get("ultima_actualizacion") or datetime.now().isoformat())[:10]
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › <a href="guias.html">Guías</a> › {e(titulo)}</nav>
<article class="texto guia">
  <h1>{e(titulo)}</h1>
  <p class="nota">Actualizada automáticamente el {hoy} con los precios de las tiendas.</p>
  {intro}
  <div class="g-indice"><strong>Resumen rápido</strong><ol>{indice}</ol></div>
</article>
<section class="g-lista">{fichas}</section>
<article class="texto guia">
  <h2>Cómo hemos elegido estas palas</h2>
  {metodo}
  <p class="nota">Las puntuaciones de 1 a 10 son <strong>estimaciones de {e(cfg["nombre_web"])}</strong> a partir de las
  características técnicas publicadas, no pruebas en pista. Los precios pueden cambiar en la tienda.</p>
  {cierre}
  <p><a href="guias.html">← Ver todas las guías</a></p>
</article>'''
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": titulo,
          "itemListElement": [{"@type": "ListItem", "position": i, "name": p["nombre"],
                               "url": f'{cfg["dominio"].rstrip("/")}/pala-{p["id"]}.html'} for i, p in enumerate(palas, 1)]}
    return h["pagina"](cfg, ruta, f'{titulo} · {cfg["nombre_web"]}', descripcion, cuerpo, estado, ld)


def _top(palas, filtro, clave, n=8):
    """Las n mejores según `clave` (mayor es mejor); a igualdad, la más popular en tienda."""
    elegidas = [p for p in palas if filtro(p)]
    elegidas.sort(key=lambda p: (-clave(p), p.get("popularidad", 999)))
    return elegidas[:n]


# ---------- Guías ----------

def guia_control(cfg, palas, estado, h):
    sel = _top(palas, lambda p: p["tipo"] == "control",
               lambda p: p["puntos"]["control"] * 2 + p["puntos"]["manejo"])
    intro = f'''<p class="intro">Las palas de control son las que más perdonan: punto dulce grande, peso cerca del puño y
una salida de bola fácil de dosificar. Suelen recomendarse si estás empezando, si juegas en el lado de derecha
o si tu juego se basa en defender bien y colocar la bola. Esta es nuestra selección de las mejores palas de control de
{ANIO}, ordenadas por su puntuación de control y manejo.</p>'''
    metodo = '''<p>Partimos de todas las palas que clasificamos como de control (forma redonda o lágrima, balance bajo o
medio). Las ordenamos por su <strong>puntuación de control</strong>, con el <strong>manejo</strong> como segundo criterio;
cuando empatan, va primero la que aparece antes en el listado de palas de Padel Nuestro, nuestra tienda de
referencia (no son datos de ventas). Nadie paga por aparecer en esta lista.</p>'''
    motivo = lambda p: (f'Control {str(p["puntos"]["control"]).replace(".", ",")}/10 y manejo '
                        f'{str(p["puntos"]["manejo"]).replace(".", ",")}/10: '
                        + ("muy cómoda para iniciarse." if "iniciacion" in p["niveles"] else "precisión para jugadores con técnica."))
    return "mejores-palas-control.html", _pagina_guia(
        cfg, estado, h, "mejores-palas-control.html", f"Mejores palas de control {ANIO}",
        f"Las mejores palas de pádel de control de {ANIO}, ordenadas por control y manejo, con su precio actualizado.",
        intro, sel, motivo, metodo)


def guia_potencia(cfg, palas, estado, h):
    sel = _top(palas, lambda p: p["tipo"] == "potencia",
               lambda p: p["puntos"]["potencia"] * 2 + p["puntos"]["control"] * 0.5)
    intro = f'''<p class="intro">Las palas de potencia concentran el peso en la cabeza para que remates y bandejas salgan
con más velocidad. A cambio son menos manejables y exigen buena técnica: no suelen recomendarse si estás empezando o
tienes molestias en el codo. Estas son las mejores palas de potencia de {ANIO} según su puntuación.</p>'''
    metodo = '''<p>Tomamos las palas que clasificamos como de potencia (normalmente forma diamante y balance alto) y las
ordenamos por su <strong>puntuación de potencia</strong>. Como desempate tenemos en cuenta el <strong>control</strong>,
porque una pala que pega fuerte y además permite colocar la bola es más útil en partido. Nadie paga por aparecer en
esta lista.</p>'''
    def motivo(p):
        goma = normalizar(_c(p, "Dureza"))
        if "dura" in goma and "media" not in goma:
            detalle = "goma dura: devuelve toda la velocidad en golpes fuertes, pero exige técnica y brazo"
        elif "blanda" in goma:
            detalle = "goma blanda: más salida de bola con menos esfuerzo, ideal para potencia sin castigar el brazo"
        else:
            detalle = "goma de dureza media: equilibrio entre pegada y salida de bola en golpes lentos"
        return f'Potencia {str(p["puntos"]["potencia"]).replace(".", ",")}/10 · {_c(p, "Cara") or "cara de carbono"} y {detalle}.'
    return "mejores-palas-potencia.html", _pagina_guia(
        cfg, estado, h, "mejores-palas-potencia.html", f"Mejores palas de potencia {ANIO}",
        f"Las mejores palas de pádel de potencia de {ANIO}, ordenadas por potencia y control, con su precio actualizado.",
        intro, sel, motivo, metodo)


def guia_codo(cfg, palas, estado, h):
    def apta(p):
        dureza = normalizar(_c(p, "Dureza"))
        balance = normalizar(_c(p, "Balance"))
        return dureza and "dura" not in dureza and balance and "alto" not in balance
    sel = _top(palas, apta, lambda p: p["puntos"]["salida"] + p["puntos"]["manejo"] - p["puntos"]["dureza"] * 0.5)
    intro = '''<p class="intro">La epicondilitis o "codo de tenista" es una molestia frecuente entre jugadores de pádel. Ninguna
pala cura una lesión. Lo que se suele aconsejar a quien tiene molestias es elegir una pala que transmita menos
vibraciones y no obligue a forzar el golpe. En esta guía te explicamos qué características se suelen recomendar y
te mostramos las palas de nuestro catálogo que las cumplen.</p>
<h2>Qué características se suelen recomendar</h2>
<ul>
  <li><strong>Goma blanda o media</strong> (Soft EVA, foam, multicapa): absorbe más vibración y la bola sale con menos esfuerzo.</li>
  <li><strong>Balance bajo o medio</strong>: con el peso más cerca de la mano, la pala resulta más fácil de mover.</li>
  <li><strong>Peso moderado</strong>: evita los extremos; muchas marcas tienen versiones "light" o "comfort".</li>
  <li><strong>Forma redonda o lágrima</strong>: punto dulce más grande, menos golpes descentrados que vibran.</li>
  <li><strong>Evita</strong> las palas muy rígidas de goma dura y balance alto, aunque sean las de tu jugador favorito.</li>
</ul>
<p class="nota">⚠️ Esta guía es orientativa y no sustituye el consejo de un médico o fisioterapeuta. Si el dolor
persiste, consulta a un profesional antes de seguir jugando.</p>'''
    metodo = '''<p>Solo incluimos palas con <strong>goma blanda o media</strong> y <strong>balance bajo o medio</strong>
según sus características publicadas. Después las ordenamos dando prioridad a la <strong>salida de bola</strong> y el
<strong>manejo</strong> (cuanto más fácil sale la bola, menos fuerza hay que hacer) y penalizando la
<strong>dureza</strong>.</p>'''
    def motivo(p):
        cara = normalizar(_c(p, "Cara"))
        if "vidrio" in cara or "glass" in cara:
            material = "cara de fibra de vidrio, más flexible y que transmite menos vibración"
        elif "carbon" in cara:
            material = "cara de carbono, algo más rígida pero compensada por la goma"
        else:
            material = f'cara de {_c(p, "Cara").lower() or "material mixto"}'
        return (f'Goma {_c(p, "Dureza").lower()}, balance {_c(p, "Balance").lower()} y {material}. '
                f'Salida de bola {str(p["puntos"]["salida"]).replace(".", ",")}/10.')
    return "palas-codo-de-tenista.html", _pagina_guia(
        cfg, estado, h, "palas-codo-de-tenista.html", "Palas de pádel para el codo de tenista",
        "Qué pala de pádel elegir si tienes codo de tenista (epicondilitis): características a buscar y palas recomendadas con su precio.",
        intro, sel, motivo, metodo)


def guia_baratas(cfg, palas, estado, h, limite=100):
    sel = [p for p in palas if p["mejor"]["precio"] < limite]
    sel.sort(key=lambda p: p.get("popularidad", 999))
    sel = sel[:10]
    intro = f'''<p class="intro">No hace falta gastar 300 € para tener una buena pala. Por debajo de {limite} € hay palas
muy completas, sobre todo modelos de temporadas anteriores que han bajado de precio y palas pensadas para iniciación y
nivel intermedio. Estas son las palas de menos de {limite} € que aparecen antes en el listado de nuestra tienda de
referencia, con el precio más bajo que hemos encontrado hoy en las tiendas que comparamos.</p>'''
    metodo = f'''<p>Seleccionamos las palas cuyo <strong>precio más bajo</strong> en alguna de las tiendas comparadas está
por debajo de {limite} € y las ordenamos por su <strong>posición en el listado de palas de Padel Nuestro</strong>,
nuestra tienda de referencia (no son datos de ventas). Como los precios cambian cada día, esta lista también: una pala
puede entrar o salir según las ofertas. Nadie paga por aparecer en esta lista.</p>'''
    cierre = '''<p>¿No sabes si elegir control, híbrida o potencia? Lee nuestra
<a href="guia-elegir-pala.html">guía para elegir pala</a> o compara varias en el
<a href="comparador.html">comparador gráfico</a>.</p>'''
    motivo = lambda p: (f'{TIPOS[p["tipo"]]["nombre"]} para nivel {", ".join(NIVELES[n]["nombre"] for n in p["niveles"]).lower()}'
                        f'{" · comparada en " + str(len(p["ofertas"])) + " tiendas" if len(p["ofertas"]) > 1 else ""}.')
    return f"palas-padel-menos-de-{limite}-euros.html", _pagina_guia(
        cfg, estado, h, f"palas-padel-menos-de-{limite}-euros.html", f"Mejores palas de pádel por menos de {limite} €",
        f"Palas de pádel destacadas por menos de {limite} €, con el precio más bajo de hoy en las tiendas que comparamos.",
        intro, sel, motivo, metodo, cierre)


def guia_vertex(cfg, palas, estado, h):
    """Comparativa Vertex 04 (2025) vs Vertex 05 (2026), solo si ambas están en el catálogo."""
    e, euros = h["e"], h["euros"]
    por_id = {p["id"]: p for p in palas}
    a, b = por_id.get("bullpadel-vertex-04-25"), por_id.get("bullpadel-vertex-05")
    if not (a and b):
        return "vertex-04-vs-vertex-05.html", None
    filas = [("Tipo", TIPOS[a["tipo"]]["nombre"], TIPOS[b["tipo"]]["nombre"])]
    for k in ("Forma", "Balance", "Núcleo", "Dureza", "Cara", "Superfície"):
        filas.append((k.replace("Superfície", "Superficie"), _c(a, k) or "—", _c(b, k) or "—"))
    for k, nombre in EJES:
        filas.append((nombre, str(a["puntos"][k]).replace(".", ","), str(b["puntos"][k]).replace(".", ",")))
    filas.append(("Mejor precio", f'{euros(a["mejor"]["precio"])} ({e(a["mejor"]["tienda"]["nombre"])})',
                  f'{euros(b["mejor"]["precio"])} ({e(b["mejor"]["tienda"]["nombre"])})'))
    tabla = "".join(f"<tr><th>{e(n)}</th><td>{va}</td><td>{vb}</td></tr>" for n, va, vb in filas)
    diferencia = b["mejor"]["precio"] - a["mejor"]["precio"]
    cambios = [n for n, va, vb in filas[1:7] if va != vb]
    if cambios:
        resumen_cambios = "Según las fichas técnicas, cambian: " + ", ".join(c.lower() for c in cambios) + "."
    else:
        resumen_cambios = ("Según las fichas técnicas publicadas, comparten forma, balance, núcleo, dureza y material: "
                           "las diferencias están en detalles de construcción y diseño que las tiendas no detallan.")
    if diferencia > 25:
        veredicto = (f"La Vertex 04 cuesta ahora <strong>{euros(diferencia)} menos</strong>. Si buscas la sensación Vertex "
                     f"sin pagar la novedad, la 04 es la compra inteligente; la 05 tiene sentido si quieres lo último "
                     f"o te gustan sus cambios.")
    elif diferencia < -5:
        veredicto = "Ahora mismo la Vertex 05 está más barata que la 04, así que la versión anterior no aporta ventaja de precio."
    else:
        veredicto = "Ahora mismo cuestan casi lo mismo, así que la Vertex 05, al ser la versión más reciente, es la opción lógica."
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › <a href="guias.html">Guías</a> › Vertex 04 vs Vertex 05</nav>
<article class="texto guia">
  <h1>Bullpadel Vertex 04 vs Vertex 05: ¿merece la pena cambiar?</h1>
  <p class="intro">La Vertex es una de las líneas de palas de potencia de Bullpadel, asociada al jugador Juan Tello.
  Bullpadel suele renovarla cada temporada y la versión anterior tiende a bajar de precio, así que surge la pregunta: ¿compensa
  pagar más por la Vertex 05 (2026) o es mejor aprovechar la Vertex 04 (2025)? Comparamos sus datos y su precio de hoy.</p>
  <div class="g-versus">
    <a href="pala-{a["id"]}.html">{h["figura"](a, "foto-guia", 220)}<strong>{e(a["nombre"])}</strong><span>desde {euros(a["mejor"]["precio"])}</span></a>
    <span class="g-vs">VS</span>
    <a href="pala-{b["id"]}.html">{h["figura"](b, "foto-guia", 220)}<strong>{e(b["nombre"])}</strong><span>desde {euros(b["mejor"]["precio"])}</span></a>
  </div>
  <h2>Comparativa de características</h2>
  <div class="tabla-scroll"><table class="tabla-comparar g-tabla"><thead><tr><th></th><th>Vertex 04 (2025)</th><th>Vertex 05 (2026)</th></tr></thead>
  <tbody>{tabla}</tbody></table></div>
  <p>{resumen_cambios}</p>
  <h2>¿Cuál compro?</h2>
  <p>{veredicto}</p>
  <p>Ten en cuenta que ambas son palas exigentes, de potencia y nivel avanzado. Si estás empezando o tienes molestias en
  el codo, mira mejor nuestras <a href="mejores-palas-control.html">palas de control</a> o la guía de
  <a href="palas-codo-de-tenista.html">palas para el codo de tenista</a>.</p>
  <p><a class="boton boton-principal" href="comparador.html?p={a["id"]},{b["id"]}">📊 Ver las dos en el comparador gráfico</a></p>
  <p class="nota">Puntuaciones estimadas por {e(cfg["nombre_web"])} a partir de las características publicadas; no son pruebas en pista.
  Precios actualizados automáticamente.</p>
  <p><a href="guias.html">← Ver todas las guías</a></p>
</article>'''
    return "vertex-04-vs-vertex-05.html", h["pagina"](
        cfg, "vertex-04-vs-vertex-05.html", f'Vertex 04 vs Vertex 05: comparativa y precio · {cfg["nombre_web"]}',
        "Bullpadel Vertex 04 (2025) frente a Vertex 05 (2026): diferencias técnicas, puntuaciones y cuál compensa comprar según su precio de hoy.",
        cuerpo, estado)


GUIAS = [
    ("mejores-palas-control.html", "Mejores palas de control", "Para empezar, defender y colocar la bola.", guia_control),
    ("mejores-palas-potencia.html", "Mejores palas de potencia", "Para atacar y definir desde la red.", guia_potencia),
    ("palas-codo-de-tenista.html", "Palas para el codo de tenista", "Qué buscar si te molesta el codo.", guia_codo),
    ("palas-padel-menos-de-100-euros.html", "Palas por menos de 100 €", "Destacadas sin gastar de más.", guia_baratas),
    ("vertex-04-vs-vertex-05.html", "Vertex 04 vs Vertex 05", "¿Compensa la nueva o la del año pasado?", guia_vertex),
]


def generar(cfg, palas, estado, h):
    """Devuelve {archivo: html} con todas las guías y el índice guias.html."""
    salida, disponibles = {}, []
    for ruta, titulo, sub, fn in GUIAS:
        nombre, html = fn(cfg, palas, estado, h)
        if html:
            salida[nombre] = html
            disponibles.append((nombre, titulo, sub))
    disponibles.append(("guia-elegir-pala.html", "Cómo elegir pala de pádel", "Forma, balance, núcleo, peso y nivel explicados."))
    tarjetas = "".join(f'<a class="g-tarjeta" href="{r}"><strong>{h["e"](t)}</strong><span>{h["e"](s)}</span></a>'
                       for r, t, s in disponibles)
    cuerpo = f'''<nav class="migas"><a href="index.html">Inicio</a> › Guías</nav>
<h1>Guías de compra de palas de pádel</h1>
<p class="intro">Guías prácticas para elegir pala según tu juego, tu nivel y tu presupuesto. Las selecciones de palas
se actualizan automáticamente con los precios de las tiendas.</p>
<div class="g-tarjetas">{tarjetas}</div>'''
    salida["guias.html"] = h["pagina"](cfg, "guias.html", f'Guías de compra de palas de pádel · {cfg["nombre_web"]}',
                                       "Guías para elegir pala de pádel: mejores palas de control y potencia, codo de tenista, palas baratas y comparativas.",
                                       cuerpo, estado)
    return salida, disponibles
