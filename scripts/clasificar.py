"""Clasificación propia de cada pala: tipo de juego (potencia / híbrida / control) y nivel.

El índice de potencia (0 = control puro, 100 = potencia pura) combina:
  forma (peso 1), balance (peso 1), tipo de juego declarado por el fabricante/tienda (peso 1)
  y dureza del núcleo (peso 0,5).
"""
import re

from comun import normalizar

FORMA = {"redonda": -1, "lagrima": 0, "hibrida": 0, "diamante": 1}
BALANCE = {"bajo": -1, "medio": 0, "alto": 1}
DUREZA = {"blanda": -1, "media": 0, "dura": 1}
JUEGO = {"control": -1, "polivalente": 0, "potencia": 1}

TIPOS = {
    "potencia": {"nombre": "Potencia", "plural": "Palas de potencia", "pagina": "palas-de-potencia.html"},
    "hibrida": {"nombre": "Híbrida", "plural": "Palas híbridas", "pagina": "palas-hibridas.html"},
    "control": {"nombre": "Control", "plural": "Palas de control", "pagina": "palas-de-control.html"},
}
NIVELES = {
    "iniciacion": {"nombre": "Iniciación / Intermedio", "pagina": "palas-iniciacion-intermedio.html"},
    "avanzado": {"nombre": "Avanzado", "pagina": "palas-nivel-avanzado.html"},
    "profesional": {"nombre": "Profesional", "pagina": "palas-nivel-profesional.html"},
}


def _media(valor, tabla):
    """'Alto, Medio' -> media de ambos valores. None si no se reconoce."""
    if not valor:
        return None
    nums = [tabla[normalizar(v)] for v in valor.split(",") if normalizar(v) in tabla]
    return sum(nums) / len(nums) if nums else None


def clasificar(pala):
    c = pala.get("caracteristicas", {})
    partes = [(_media(c.get("Forma"), FORMA), 1), (_media(c.get("Balance"), BALANCE), 1),
              (_media(c.get("Tipo de Juego"), JUEGO), 1), (_media(c.get("Dureza"), DUREZA), 0.5)]
    partes = [(v, w) for v, w in partes if v is not None]
    puntuacion = sum(v * w for v, w in partes) / sum(w for _, w in partes) if partes else 0
    indice = round((puntuacion + 1) * 50)
    tipo = "potencia" if indice >= 62 else "control" if indice <= 38 else "hibrida"

    nivel_txt = normalizar(c.get("Nivel de Juego", ""))
    niveles = [k for k, clave in (("iniciacion", "principiante"), ("iniciacion", "iniciacion"),
                                  ("avanzado", "avanzado"), ("profesional", "profesional")) if clave in nivel_txt]
    if not niveles:  # sin dato: lo deducimos de dureza y material
        cara = normalizar(c.get("Cara", ""))
        blanda = (_media(c.get("Dureza"), DUREZA) or 0) < 0
        niveles = ["iniciacion"] if blanda or "vidrio" in cara or "glass" in cara else ["avanzado"]
    return {"indice": indice, "tipo": tipo, "niveles": sorted(set(niveles), key=list(NIVELES).index),
            "datos_usados": len(partes)}


def _material(cara):
    """Rigidez aproximada de la cara: 0 = fibra de vidrio, 1 = carbono, hasta 2 = carbono de muchas K."""
    cara = normalizar(cara)
    if not cara:
        return 0.5
    if "vidrio" in cara or "glass" in cara or "fibrix" in cara:
        return 0
    ks = [int(k) for k in re.findall(r"(\d+)\s*k", cara)]
    return 1 + min(max(ks, default=3) / 24, 1) if ("carbon" in cara or ks) else 0.5


def _medio_punto(x):
    return max(1.0, min(10.0, round(x * 2) / 2))


def puntuaciones(pala, clas):
    """Puntuaciones estimadas de 1 a 10 para el comparador gráfico.

    No son pruebas en pista: se deducen de las características técnicas publicadas.
      potencia      <- índice potencia/control + rigidez del material
      control       <- inverso del índice + dureza (una goma dura da más precisión)
      manejo        <- balance bajo y forma redonda = más manejable
      salida de bola<- goma blanda y fibra de vidrio = la bola sale con menos esfuerzo
      dureza        <- dureza del núcleo + rigidez del material
    """
    c = pala.get("caracteristicas", {})
    i = clas["indice"] / 100
    dureza = _media(c.get("Dureza"), DUREZA)
    dureza = 0 if dureza is None else dureza
    balance = _media(c.get("Balance"), BALANCE)
    balance = 0 if balance is None else balance
    forma = _media(c.get("Forma"), FORMA)
    forma = 0 if forma is None else forma
    mat = _material(c.get("Cara"))
    return {
        "potencia": _medio_punto(3 + 5.5 * i + 0.8 * mat),
        "control": _medio_punto(4 + 4.5 * (1 - i) + 0.8 * (dureza + 1) / 2 + 0.4 * mat),
        "manejo": _medio_punto(6 - 2 * balance - 1 * forma - 0.3 * mat),
        "salida": _medio_punto(6 - 2.5 * dureza - 1 * mat + 0.5),
        "dureza": _medio_punto(5.5 + 2.8 * dureza + 0.8 * mat),
    }


def explicar(pala, clas):
    """Frase en lenguaje llano que justifica la clasificación."""
    c = pala.get("caracteristicas", {})
    motivos = []
    if c.get("Forma"):
        motivos.append(f"forma {c['Forma'].lower()}")
    if c.get("Balance"):
        motivos.append(f"balance {c['Balance'].lower()}")
    if c.get("Dureza"):
        motivos.append(f"núcleo de dureza {c['Dureza'].lower()}")
    base = ", ".join(motivos) if motivos else "sus características"
    if clas["tipo"] == "potencia":
        efecto = "concentra el peso en la cabeza para ganar pegada en remates y bandejas, a cambio de algo de manejabilidad"
    elif clas["tipo"] == "control":
        efecto = "reparte el peso hacia el puño y ofrece un punto dulce amplio: perdona más los golpes descentrados y facilita colocar la bola"
    else:
        efecto = "busca el equilibrio: suficiente salida de bola para atacar sin perder precisión en defensa"
    return f"Por su {base}, esta pala {efecto}."
