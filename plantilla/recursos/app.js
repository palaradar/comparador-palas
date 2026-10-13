// Filtros de la rejilla de palas y fechas relativas ("hace 2 horas").
(function () {
  function haceCuanto(iso) {
    var t = Date.parse(iso);
    if (!t) return "";
    var min = Math.round((Date.now() - t) / 60000);
    if (min < 1) return "ahora mismo";
    if (min < 60) return "hace " + min + " min";
    var h = Math.round(min / 60);
    if (h < 24) return "hace " + h + " h";
    var d = Math.round(h / 24);
    return "hace " + d + (d === 1 ? " día" : " días");
  }
  document.querySelectorAll("td.hora[data-fecha]").forEach(function (el) {
    el.textContent = haceCuanto(el.dataset.fecha);
  });
  var pie = document.querySelector(".actualizado[data-fecha]");
  if (pie && pie.dataset.fecha) pie.textContent = "Precios actualizados " + haceCuanto(pie.dataset.fecha) + ".";

  // Reviews de YouTube: el reproductor (modo sin cookies) solo se carga al pulsar la miniatura
  document.querySelectorAll(".video[data-video]").forEach(function (b) {
    b.addEventListener("click", function () {
      var marco = document.createElement("iframe");
      marco.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(b.dataset.video) + "?autoplay=1&rel=0";
      marco.title = b.getAttribute("aria-label") || "Review en YouTube";
      marco.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      marco.allowFullscreen = true;
      var mini = b.querySelector(".video-mini");
      mini.innerHTML = "";
      mini.appendChild(marco);
      b.classList.add("reproduciendo");
    }, { once: true });
  });

  var form = document.getElementById("filtros");
  var rejilla = document.getElementById("rejilla");
  if (!form || !rejilla) return;
  var tarjetas = Array.prototype.slice.call(rejilla.querySelectorAll(".tarjeta"));
  var contador = document.getElementById("contador");

  function valor(nombre) {
    var campo = form.elements[nombre];
    return campo ? campo.value : "";
  }

  function aplicar() {
    var tipo = valor("tipo"), nivel = valor("nivel"), marca = valor("marca");
    var precio = parseFloat(valor("precio")) || Infinity, orden = valor("orden");
    var visibles = 0;
    tarjetas.forEach(function (t) {
      var ok = (!tipo || t.dataset.tipo === tipo) &&
        (!nivel || t.dataset.niveles.split(" ").indexOf(nivel) >= 0) &&
        (!marca || t.dataset.marca === marca) &&
        parseFloat(t.dataset.precio) <= precio;
      t.hidden = !ok;
      if (ok) visibles++;
    });
    var clave = {
      pop: function (t) { return +t.dataset.pop; },
      precio: function (t) { return +t.dataset.precio; },
      potencia: function (t) { return -t.dataset.indice; },
      control: function (t) { return +t.dataset.indice; }
    }[orden] || function (t) { return +t.dataset.pop; };
    tarjetas.slice().sort(function (a, b) { return clave(a) - clave(b); })
      .forEach(function (t) { rejilla.appendChild(t); });
    if (contador) contador.textContent = visibles + (visibles === 1 ? " pala encontrada" : " palas encontradas");
  }

  // Recuerda los filtros de la portada en la URL para poder compartirlos
  var params = new URLSearchParams(location.search);
  params.forEach(function (v, k) { if (form.elements[k]) form.elements[k].value = v; });
  form.addEventListener("change", function () {
    var q = new URLSearchParams();
    Array.prototype.forEach.call(form.elements, function (c) { if (c.name && c.value && !(c.name === "orden" && c.value === "pop")) q.set(c.name, c.value); });
    history.replaceState(null, "", q.toString() ? "?" + q : location.pathname);
    aplicar();
  });
  aplicar();
})();
