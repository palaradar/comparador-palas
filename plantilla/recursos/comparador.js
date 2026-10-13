// Comparador gráfico: radar de 5 ejes + tabla enfrentada de hasta 3 palas.
(function () {
  var PALAS = window.PALAS || [];
  var porId = {}, porNombre = {};
  PALAS.forEach(function (p) { porId[p.id] = p; porNombre[p.nombre.toLowerCase()] = p; });

  var EJES = [["potencia", "POTENCIA"], ["control", "CONTROL"], ["manejo", "MANEJO"],
    ["salida", "SALIDA DE BOLA"], ["dureza", "DUREZA"]];
  var R = 100, NS = "http://www.w3.org/2000/svg";
  var entradas = [0, 1, 2].map(function (i) { return document.getElementById("pala" + i); });
  var sel = [null, null, null];

  // Selección inicial: ?p=id1,id2,id3 y, si faltan, las palas por defecto
  var pedidas = (new URLSearchParams(location.search).get("p") || "").split(",").filter(function (id) { return porId[id]; });
  var candidatas = pedidas.concat(window.POR_DEFECTO || []);
  candidatas.forEach(function (id) {
    var libre = sel.indexOf(null);
    if (libre >= 0 && sel.indexOf(id) < 0) sel[libre] = id;
  });

  function punto(eje, valor) {
    var ang = (-90 + eje * 72) * Math.PI / 180, r = R * valor / 10;
    return [r * Math.cos(ang), r * Math.sin(ang)];
  }
  function el(nombre, attrs, padre) {
    var n = document.createElementNS(NS, nombre);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (padre) padre.appendChild(n);
    return n;
  }
  function euros(n) { return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"; }
  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  function dibujarRadar() {
    var svg = document.getElementById("radar");
    svg.innerHTML = "";
    [2, 4, 6, 8, 10].forEach(function (v) {
      el("polygon", { "class": "radar-anillo", points: EJES.map(function (_, i) { return punto(i, v).join(","); }).join(" ") }, svg);
    });
    EJES.forEach(function (eje, i) {
      var p = punto(i, 10), t = punto(i, 12.4);
      el("line", { "class": "radar-eje", x1: 0, y1: 0, x2: p[0], y2: p[1] }, svg);
      var txt = el("text", { "class": "radar-etiqueta", x: t[0], y: t[1] + 4,
        "text-anchor": Math.abs(t[0]) < 5 ? "middle" : t[0] > 0 ? "start" : "end" }, svg);
      txt.textContent = eje[1];
    });
    sel.forEach(function (id, s) {
      if (!id) return;
      var pala = porId[id];
      var pts = EJES.map(function (eje, i) { return punto(i, pala.puntos[eje[0]]); });
      el("polygon", { "class": "radar-serie serie-" + s, points: pts.map(function (p) { return p.join(","); }).join(" ") }, svg);
      pts.forEach(function (p) { el("circle", { "class": "radar-punto serie-" + s, cx: p[0], cy: p[1], r: 3.5 }, svg); });
    });
  }

  function dibujarTabla() {
    var activas = sel.map(function (id, s) { return id ? { p: porId[id], s: s } : null; }).filter(Boolean);
    var tabla = document.getElementById("tabla-comparar");
    if (!activas.length) { tabla.innerHTML = ""; return; }
    var h = "<thead><tr><th></th>" + activas.map(function (a) {
      return '<th class="serie-' + a.s + '"><span class="serie-raya"></span><small>' + esc(a.p.marca) +
        "</small><br>" + esc(a.p.nombre) + "</th>";
    }).join("") + "</tr></thead><tbody>";
    var texto = [["Tipo", "tipo"], ["Nivel", "nivel"], ["Forma", "forma"], ["Balance", "balance"],
      ["Cara", "cara"], ["Goma", "nucleo"], ["Dureza goma", "dureza_txt"]];
    texto.forEach(function (f) {
      h += "<tr><th>" + f[0] + "</th>" + activas.map(function (a) { return "<td>" + esc(a.p[f[1]]) + "</td>"; }).join("") + "</tr>";
    });
    EJES.forEach(function (eje) {
      var vals = activas.map(function (a) { return a.p.puntos[eje[0]]; });
      var max = Math.max.apply(null, vals);
      h += '<tr class="fila-nota"><th>' + eje[1].charAt(0) + eje[1].slice(1).toLowerCase() + "</th>" + activas.map(function (a, i) {
        var mejor = activas.length > 1 && vals[i] === max;
        return '<td class="nota-num' + (mejor ? " gana serie-" + a.s : "") + '">' + String(vals[i]).replace(".", ",") + "</td>";
      }).join("") + "</tr>";
    });
    var precios = activas.map(function (a) { return a.p.precio; });
    var min = Math.min.apply(null, precios);
    h += '<tr class="fila-precio"><th>Mejor precio</th>' + activas.map(function (a) {
      var mejor = activas.length > 1 && a.p.precio === min;
      return '<td class="' + (mejor ? "gana serie-" + a.s : "") + '"><strong>' + euros(a.p.precio) + "</strong><br><small>en " +
        esc(a.p.tienda) + '</small><br><a class="boton" href="pala-' + a.p.id + '.html">Ver precios</a></td>';
    }).join("") + "</tr></tbody>";
    tabla.innerHTML = h;
  }

  function dibujarHuecos() {
    sel.forEach(function (id, s) {
      var fig = entradas[s].parentNode.querySelector(".hueco-figura");
      entradas[s].value = id ? porId[id].nombre : "";
      if (!id) { fig.innerHTML = '<span class="hueco-vacio">+</span>'; return; }
      var p = porId[id], dibujo = window.SILUETAS[p.silueta];
      var imagen = p.foto
        ? '<a class="foto foto-comparador" href="pala-' + p.id + '.html"><img src="' + esc(p.foto) + '" alt="' + esc(p.nombre) +
          '" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add(\'foto-error\')">' + dibujo + "</a>"
        : dibujo;
      fig.innerHTML = imagen + '<span class="hueco-tipo">' + esc(p.tipo) + "</span>";
    });
  }

  function actualizar() {
    dibujarHuecos(); dibujarRadar(); dibujarTabla();
    var ids = sel.filter(Boolean).join(",");
    history.replaceState(null, "", ids ? "?p=" + ids : location.pathname);
  }

  entradas.forEach(function (input, s) {
    input.addEventListener("change", function () {
      var pala = porNombre[input.value.trim().toLowerCase()];
      if (pala && sel.indexOf(pala.id) >= 0 && sel[s] !== pala.id) pala = null; // ya está en otro hueco
      sel[s] = pala ? pala.id : (input.value.trim() ? sel[s] : null);
      actualizar();
    });
    input.addEventListener("focus", function () { input.select(); });
  });

  var boton = document.getElementById("compartir");
  if (boton) boton.addEventListener("click", function () {
    var hecho = function () { boton.textContent = "¡Enlace copiado!"; setTimeout(function () { boton.textContent = "Copiar enlace de esta comparativa"; }, 2000); };
    if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(hecho, function () { prompt("Copia este enlace:", location.href); });
    else prompt("Copia este enlace:", location.href);
  });

  actualizar();
})();
