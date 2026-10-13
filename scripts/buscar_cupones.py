"""Revisa la portada de cada tienda buscando códigos promocionales visibles.

Los códigos detectados automáticamente se guardan en datos/cupones.json con el texto donde
aparecían. Los cupones que añadas a mano en datos/cupones_manual.json siempre se muestran.
"""
import html
import re
from datetime import datetime, timezone

from comun import descargar, guardar_json, leer_json

PATRON = re.compile(
    r"(?:c[oó]digo|cup[oó]n|code)\s*(?:promocional|descuento)?\s*[:\-–]?\s*[\"'“«]?\s*([A-Z][A-Z0-9]{3,14})\b",
    re.I)
NO_CODIGO = {"PROMOCIONAL", "DESCUENTO", "POSTAL", "CODIGO", "CUPON", "ENVIO", "GRATIS", "PEDIDO", "COMPRA",
             "AQUI", "VALIDO", "CLIENTE", "REGALO", "ACTIVO", "INTRODUCE", "APLICA", "SECRETO", "NUEVO"}


def texto_visible(pagina):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", pagina, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def main():
    ahora = datetime.now(timezone.utc).isoformat(timespec="minutes")
    cupones = []
    for tienda in leer_json("tiendas.json"):
        if tienda["modo"] == "solo_enlace":
            continue
        _, pag = descargar(tienda["web"])
        if not pag:
            continue
        texto = texto_visible(pag)
        vistos = set()
        for m in PATRON.finditer(texto):
            codigo = m.group(1)
            # Un código real va en mayúsculas en la web y suele mezclar letras y números o ser una palabra corta
            if not codigo.isupper() or codigo.upper() in NO_CODIGO or codigo in vistos:
                continue
            vistos.add(codigo)
            contexto = texto[max(0, m.start() - 80): m.end() + 10].strip()
            pct = re.search(r"(\d{1,2})\s?%", contexto)
            descripcion = f"{pct.group(1)} % de descuento" if pct else "Código promocional publicado en la web de la tienda"
            cupones.append({"tienda": tienda["id"], "codigo": codigo, "descripcion": descripcion,
                            "texto": contexto, "origen": "automatico", "detectado": ahora})
        print(f"{tienda['nombre']}: {len(vistos)} código(s)")
    guardar_json("cupones.json", cupones)


if __name__ == "__main__":
    main()
