// Comparador gráfico: radar de 5 ejes + tabla enfrentada de hasta 3 palas.
(function () {
  var PALAS = window.PALAS || [];
  var porId = {};
  PALAS.forEach(function (p) { porId[p.id] = p; });

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
        esc(a.p.tienda) + '</small><br><a class="boton" href="pala-' + a.p.id + '.html">Ver precios<span class="solo-lectores"> de ' + esc(a.p.nombre) + '</span></a></td>';
    }).join("") + "</tr></tbody>";
    tabla.innerHTML = h;
  }

  function dibujarHuecos() {
    sel.forEach(function (id, s) {
      var fig = entradas[s].closest(".hueco-pala").querySelector(".hueco-figura");
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

  // ---------- Buscador con sugerencias ----------
  // Sin tildes ni mayúsculas, y todas las palabras escritas en cualquier orden ("tapia at10").
  function normal(t) {
    return String(t).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }
  PALAS.forEach(function (p, i) { p._texto = normal(p.nombre + " " + p.marca + " " + p.tipo); p._pop = i; });
  var MAX_SUGERENCIAS = 8;

  function buscar(consulta, s) {
    var palabras = normal(consulta).split(" ").filter(Boolean);
    var ocupadas = sel.filter(function (id, i) { return id && i !== s; });
    var res = PALAS.filter(function (p) {
      return ocupadas.indexOf(p.id) < 0 && palabras.every(function (w) { return p._texto.indexOf(w) >= 0; });
    });
    if (palabras.length) {
      var q = normal(consulta);
      res.sort(function (a, b) {  // primero las que empiezan por lo escrito, luego por popularidad
        var pa = normal(a.nombre).indexOf(q) === 0 ? 0 : 1, pb = normal(b.nombre).indexOf(q) === 0 ? 0 : 1;
        return pa - pb || a._pop - b._pop;
      });
    }
    return res.slice(0, MAX_SUGERENCIAS);
  }

  function resaltar(nombre, consulta) {
    var palabras = normal(consulta).split(" ").filter(Boolean);
    return esc(nombre).split(" ").map(function (w) {
      return palabras.some(function (q) { return normal(w).indexOf(q) >= 0; }) ? "<mark>" + w + "</mark>" : w;
    }).join(" ");
  }

  entradas.forEach(function (input, s) {
    var lista = document.createElement("ul");
    lista.className = "sugerencias";
    lista.id = "sugerencias-" + s;
    lista.setAttribute("role", "listbox");
    lista.hidden = true;
    input.parentNode.insertBefore(lista, input.nextSibling);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", lista.id);
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("list");
    var actuales = [], activa = -1;

    function abrir() {
      actuales = buscar(input.value, s);
      activa = actuales.length && input.value.trim() ? 0 : -1;
      if (!actuales.length) {
        lista.innerHTML = '<li class="sin-resultados">No encontramos esa pala. Prueba con la marca o el modelo.</li>';
      } else {
        var titulo = input.value.trim() ? "" : '<li class="sugerencias-titulo">Destacadas</li>';
        lista.innerHTML = titulo + actuales.map(function (p, i) {
          var foto = p.foto ? '<img src="' + esc(p.foto) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.visibility=\'hidden\'">' : "";
          return '<li role="option" id="op-' + s + "-" + i + '" data-i="' + i + '"' + (i === activa ? ' aria-selected="true"' : "") + ">" +
            '<span class="sug-foto">' + foto + "</span>" +
            '<span class="sug-texto"><span class="sug-nombre">' + resaltar(p.nombre, input.value) + "</span>" +
            '<span class="sug-meta">' + esc(p.tipo) + " · " + esc(p.nivel) + "</span></span>" +
            '<span class="sug-precio">' + euros(p.precio) + "</span></li>";
        }).join("");
      }
      lista.hidden = false;
      input.setAttribute("aria-expanded", "true");
      marcar();
    }
    function cerrar() {
      lista.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function marcar() {
      [].forEach.call(lista.querySelectorAll("[role=option]"), function (li) {
        var on = +li.dataset.i === activa;
        if (on) { li.setAttribute("aria-selected", "true"); li.scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", li.id); }
        else li.removeAttribute("aria-selected");
      });
    }
    function elegir(p) {
      sel[s] = p ? p.id : null;
      cerrar();
      actualizar();
      input.blur();
    }

    input.addEventListener("focus", function () { input.select(); abrir(); });
    input.addEventListener("input", abrir);
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        if (lista.hidden) abrir();
        if (actuales.length) activa = (activa + (ev.key === "ArrowDown" ? 1 : -1) + actuales.length) % actuales.length;
        marcar();
        ev.preventDefault();
      } else if (ev.key === "Enter") {
        if (!lista.hidden && actuales[activa]) elegir(actuales[activa]);
        else if (!input.value.trim()) elegir(null);
        ev.preventDefault();
      } else if (ev.key === "Escape") {
        cerrar();
        input.value = sel[s] ? porId[sel[s]].nombre : "";
        input.blur();
      }
    });
    // mousedown (no click) para elegir antes de que el campo pierda el foco
    lista.addEventListener("mousedown", function (ev) {
      var li = ev.target.closest("[role=option]");
      ev.preventDefault();
      if (li) elegir(actuales[+li.dataset.i]);
    });
    input.addEventListener("blur", function () {
      setTimeout(function () {
        if (lista.hidden) return;
        cerrar();
        if (!input.value.trim()) elegir(null);                       // campo vaciado: hueco libre
        else input.value = sel[s] ? porId[sel[s]].nombre : "";        // texto a medias: se restaura
      }, 120);
    });
  });

  var boton = document.getElementById("compartir");
  if (boton) boton.addEventListener("click", function () {
    var hecho = function () { boton.textContent = "¡Enlace copiado!"; setTimeout(function () { boton.textContent = "Copiar enlace de esta comparativa"; }, 2000); };
    if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(hecho, function () { prompt("Copia este enlace:", location.href); });
    else prompt("Copia este enlace:", location.href);
  });

  actualizar();
})();
