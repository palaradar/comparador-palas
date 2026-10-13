# PalaRadar · Comparador de palas de pádel

Web que compara precios de palas de pádel en las principales tiendas de España, las clasifica en
**potencia / híbrida / control** y por **nivel**, destaca la tienda más barata y muestra los códigos de descuento activos.

Funciona sola: cada 6 horas GitHub revisa los precios, busca cupones, regenera la web y la publica. Gratis.

---

## Qué hay en esta carpeta

| Carpeta / archivo | Para qué sirve | ¿Lo tocas tú? |
|---|---|---|
| `config.json` | Nombre de la web, tu dominio, tu ID de AdSense y tus datos legales | **Sí** |
| `datos/tiendas.json` | Las tiendas comparadas y tus códigos de afiliado | **Sí**, al darte de alta en afiliados |
| `datos/cupones_manual.json` | Cupones que quieras añadir a mano | Opcional |
| `datos/catalogo.json`, `precios.json`, `historial.json`, `cupones.json` | Datos que se actualizan solos | No |
| `scripts/` | Los programas que hacen el trabajo | No |
| `plantilla/` | Diseño y textos (guía, páginas legales) | Solo si quieres cambiar textos |
| `web/` | La web generada, lista para publicar | No (se regenera sola) |
| `ver-web-en-local.bat` | Doble clic: actualiza y abre la web en tu ordenador | Para probar |

---

## Puesta en marcha (una sola vez, unos 30 minutos)

### 1. Rellena `config.json`
Ábrelo con el Bloc de notas y cambia:
- `nombre_web`: el nombre que quieras darle.
- `dominio`: la dirección de tu web (ver paso 4). Mientras no tengas dominio, déjalo así.
- `titular`, `nif`, `email_contacto`: **obligatorio** por ley (LSSI) para el aviso legal, y AdSense lo revisa.

### 2. Crea una cuenta en GitHub y sube el proyecto
1. Crea una cuenta gratuita en https://github.com
2. Instala **GitHub Desktop** (https://desktop.github.com): permite subir cambios con botones, sin comandos.
3. En GitHub Desktop: *File → Add local repository →* elige esta carpeta `comparador-palas` → te ofrecerá
   *create a repository*: acéptalo → botón **Publish repository** (puede ser público o privado; para GitHub Pages
   gratis tiene que ser **público**).

### 3. Activa la publicación automática
En la web de GitHub, dentro de tu repositorio:
1. **Settings → Pages →** en *Source* elige **GitHub Actions**.
2. **Settings → Actions → General →** en *Workflow permissions* marca **Read and write permissions** y guarda.
3. Pestaña **Actions →** "Actualizar precios y publicar web" → **Run workflow**.
   Tardará entre 15 y 40 minutos la primera vez. Al terminar, tu web estará en
   `https://TU-USUARIO.github.io/comparador-palas/`.

A partir de ahí se actualiza sola cada 6 horas. Los lunes añade también las palas nuevas del catálogo.

### 4. Ponle un dominio propio (recomendado, ~10 €/año)
Compra un `.es` o `.com` (Dondominio, Namecheap, Cloudflare…). En GitHub: **Settings → Pages → Custom domain**,
escribe tu dominio y sigue las instrucciones de DNS que te muestra. Después pon ese dominio en `config.json`.
AdSense pide que la web esté en un dominio propio, no sirve `github.io`.

---

## Ganar dinero

### Enlaces de afiliado (lo que más rinde)
Cada clic en "Ir a la tienda" puede darte una comisión de las ventas. Date de alta en:
- **Amazon Afiliados** (https://afiliados.amazon.es): cuando te acepten, pon tu etiqueta en `datos/tiendas.json`,
  en la tienda `amazon`: `"afiliado": "tag=TUETIQUETA-21"`.
- **Awin** (https://www.awin.com/es): busca allí Decathlon y tiendas de pádel. Awin te da un enlace del tipo
  `https://www.awin1.com/cread.php?awinmid=XXXX&awinaffid=YYYY&ued=` → ponlo en la tienda con `{url}` al final:
  `"afiliado": "https://www.awin1.com/cread.php?awinmid=XXXX&awinaffid=YYYY&ued={url}"`.
- Muchas tiendas de pádel tienen **programa propio** (busca "afiliados" al pie de su web) o están en
  **Tradedoubler / TradeTracker**. Mismo sistema: su enlace con `{url}` donde va la dirección del producto.

### Google AdSense
1. Espera a tener dominio propio y unas semanas de contenido indexado en Google.
2. Solicítalo en https://adsense.google.com. Cuando te den tu ID (`ca-pub-1234567890123456`), ponlo en
   `config.json` → `adsense_cliente`. La web añadirá sola el código de anuncios y el archivo `ads.txt`.
3. En AdSense, activa **Anuncios automáticos** y en **Privacidad y mensajes** activa el **mensaje de consentimiento
   para la UE (RGPD)**. Es obligatorio en España y así no necesitas un banner de cookies aparte.

**Consejo:** AdSense rechaza webs que son solo tablas de precios ("contenido de poco valor"). Cuantas más guías
propias haya (como `plantilla/guia-elegir-pala.html`), más probable es la aprobación y más visitas te mandará Google.
Ideas: "Mejores palas de control 2026", "Palas para el codo de tenista", "Pala de carbono o de fibra de vidrio".

---

## Cómo funciona por dentro

- **Catálogo**: se importa de Padel Nuestro, que publica las características técnicas de cada pala
  (forma, balance, núcleo, dureza, nivel…).
- **Precios**: en cada tienda se busca la misma pala y se lee el precio de la ficha del producto.
  Se comprueba que es exactamente el mismo modelo por **código EAN** o, si no lo hay, por nombre exacto
  (rechaza versiones de otro año, de mujer, junior, "light", "hybrid", de segunda mano…). Si hay duda, la tienda no
  aparece: es preferible a mostrar el precio de otra pala.
- **Clasificación**: índice propio de 0 (control) a 100 (potencia) a partir de forma, balance, dureza del núcleo y
  tipo de juego declarado. <38 = control, >62 = potencia, entre medias = híbrida.
- **Cupones**: se revisa la portada de cada tienda buscando "código …". Puedes añadir más a mano en
  `datos/cupones_manual.json`:
  ```json
  [{"tienda": "padelnuestro", "codigo": "PADEL10", "descripcion": "10 % en palas hasta el 31/12"}]
  ```

- **Fotos**: se muestran directamente desde los servidores de Padel Nuestro (no se copian), con el crédito
  "Imagen: Padel Nuestro" enlazado a su tienda. Los derechos de las fotos son de las marcas y tiendas: lo correcto a
  medio plazo es usar las imágenes de los feeds de afiliados, que incluyen permiso de uso. Si una tienda te pide
  retirarlas, pon `"mostrar_fotos": false` en `config.json` y la web volverá a mostrar las siluetas dibujadas.

- **Reviews en vídeo**: cada ficha muestra hasta 3 reviews de YouTube del modelo exacto (en español, de más de
  2 minutos). Se buscan con la API oficial de YouTube, que necesita una clave gratuita (ver abajo). Sin clave, la
  ficha muestra un botón "Ver más reviews en YouTube". También puedes fijar vídeos a mano en
  `datos/videos_manual.json` (tienen prioridad sobre los automáticos):
  ```json
  {"bullpadel-vertex-04-25": [{"id": "PKB-Z-gznIw", "titulo": "Review Vertex 04 2025", "canal": "Padel Market"}]}
  ```
  El `id` es lo que va detrás de `watch?v=` en la dirección del vídeo, y la clave de cada pala es el final de la
  dirección de su ficha (`pala-XXXX.html`).

#### Conseguir la clave de YouTube (gratis, 10 minutos)
1. Entra en https://console.cloud.google.com con tu cuenta de Google y crea un proyecto (p. ej. "PalaRadar").
2. Menú **APIs y servicios → Biblioteca** → busca **YouTube Data API v3** → **Habilitar**.
3. **APIs y servicios → Credenciales → Crear credenciales → Clave de API**. Copia la clave.
4. En la clave, pulsa **Restringir clave** → en *Restricciones de API* elige solo *YouTube Data API v3* → Guardar.
5. En GitHub, en tu repositorio: **Settings → Secrets and variables → Actions → New repository secret**.
   Nombre: `YOUTUBE_API_KEY`, valor: la clave. (Nunca la pongas en `config.json`: el repositorio es público.)
6. Para probarla en tu ordenador, crea un archivo `clave_youtube.txt` en esta carpeta con la clave dentro
   (ese archivo no se sube a GitHub).

La cuota gratuita da para unas 100 búsquedas al día; el sistema hace como mucho 80 y repite cada pala una vez al
mes, así que nunca cuesta dinero.

### Tiendas
| Tienda | Precio automático |
|---|---|
| Padel Nuestro, Padel Ibérico, Padel Point, Zona de Padel, Time2Padel, Padel Market | Sí |
| Amazon | No: Amazon prohíbe leer su web. Se mostrará botón "Consultar precio". Con la API de Amazon Afiliados (requiere ventas previas) se podría activar |
| Decathlon | No: bloquea la lectura. Se activaría con su feed de productos de Awin |

### Si algo falla
- Pestaña **Actions** en GitHub: cada ejecución en rojo muestra el error. Si una tienda cambia su web, puede dejar
  de leerse su precio; el resto sigue funcionando y el último precio conocido se oculta para no mostrar datos viejos.
- Las tiendas a veces bloquean servidores de EE. UU. (donde corre GitHub). Si una tienda deja de aparecer, puede
  ser eso.

### Buenas prácticas
La web consulta cada tienda con pausas de 2,5 segundos y solo cada 6 horas, una carga mínima. Si alguna tienda te
pide que dejes de leer su web, elimínala de `datos/tiendas.json` (o, mejor, pídele un feed de afiliado).
