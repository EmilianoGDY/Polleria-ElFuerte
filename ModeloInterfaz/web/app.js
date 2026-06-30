/* app.js — Interactividad. No calcula nada: le pide todo al servidor Python. */

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

async function pedir(url, opciones) {
  const resp = await fetch(url, opciones);
  return { ok: resp.ok, datos: await resp.json().catch(() => ({})) };
}

const plata = (n) => "$" + n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const plataR = (n) => "$" + Math.round(n).toLocaleString("es-AR");   // sin centavos (tabla compacta)
const num = (n, dec = 2) => (n === null || n === undefined ? "—" : Number(n).toFixed(dec));
function hora(min) {                 // minutos desde las 08:00 -> "HH:MM"
  if (min === null || min === undefined) return "—";
  const t = Math.round(8 * 60 + min);
  return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0");
}

let toastTimer;
function toast(msg, tipo = "ok") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = `toast mostrar ${tipo}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = "toast"), 2500);
}

// Navegación por tabs (y pantallas sin tab, como Stock óptimo)
function irA(vistaId, tabData = null) {
  $$(".vista").forEach((v) => v.classList.remove("activa"));
  $("#" + vistaId).classList.add("activa");
  $$(".tab").forEach((t) => t.classList.toggle("activo", t.dataset.vista === tabData));
}
$$(".tab").forEach((tab) =>
  tab.addEventListener("click", () => irA("vista-" + tab.dataset.vista, tab.dataset.vista)));

// ---------- Estado (parámetros + restricciones) ----------
async function cargarEstado() {
  const { datos } = await pedir("/api/estado");
  dibujarParametros(datos);
  dibujarRestricciones(datos.restricciones);
}

function dibujarParametros(estado) {
  $("#tabla-param").querySelector("tbody").innerHTML = estado.parametros.map((p) => `
    <tr>
      <td class="p-label">${p.etiqueta}</td>
      <td class="p-unidad">${p.unidad || ""}</td>
      <td class="p-box"><input type="number" step="${p.tipo === "int" ? "1" : "any"}" value="${p.valor}" data-clave="${p.clave}"></td>
    </tr>`).join("");
  $$("#tabla-param input").forEach((inp) =>
    inp.addEventListener("change", () => guardarParametro(inp.dataset.clave, inp.value)));
  $("#derivados").innerHTML =
    `Precio por milanesa: <b>${plata(estado.derivados.precio_milanesa)}</b> &nbsp;·&nbsp; ` +
    `Margen neto por milanesa: <b>${plata(estado.derivados.margen_milanesa)}</b>`;
}

async function guardarParametro(clave, valor) {
  const { ok, datos } = await pedir("/api/parametros", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clave, valor }),
  });
  toast(datos.mensaje || (ok ? "Guardado" : "Error"), ok ? "ok" : "error");
  if (datos.estado) { dibujarParametros(datos.estado); dibujarRestricciones(datos.estado.restricciones); }
}

function dibujarRestricciones(r) {
  $("#lista-restricciones").innerHTML = `
    <div class="restriccion">
      <div><h4>Cierre de jornada (Tf)</h4><p>Atención hasta ${r.Tf} min (cierre 12:30)</p></div>
      <span class="estado-fijo">● ACTIVA (fija)</span>
    </div>
    <div class="restriccion">
      <div><h4>Límite de ingreso (TI)</h4><p>No entran clientes después de ${r.TI} min (12:20)</p></div>
      <span class="estado-fijo">● ACTIVA (fija)</span>
    </div>
    <div class="restriccion">
      <div><h4>Abandono por tolerancia de espera</h4><p>El cliente se retira si la espera supera ${r.tolerancia} min</p></div>
      <label class="switch"><input type="checkbox" id="sw-tol" ${r.tolerancia_activa ? "checked" : ""}><span class="slider"></span></label>
    </div>
    <div class="estado-tol ${r.tolerancia_activa ? "verde" : "muted"}">
      ${r.tolerancia_activa ? "Con tolerancia" : "Sin tolerancia"}
    </div>`;
  $("#sw-tol").addEventListener("change", (e) => toggleTolerancia(e.target.checked));
}

async function toggleTolerancia(valor) {
  const { datos } = await pedir("/api/restricciones", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ valor }),
  });
  if (datos.estado) dibujarRestricciones(datos.estado.restricciones);
}

// ---------- Simulación ----------
async function correr(url, boton) {
  const texto = boton.textContent;
  $$(".btn, .btn-chico").forEach((b) => (b.disabled = true));
  boton.textContent = "Calculando…";

  const { datos } = await pedir(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });

  $("#placeholder-sim").classList.add("oculto");
  $("#resultado-sim").classList.remove("oculto");
  pintarMuestra(datos);
  if (datos.replicas) pintarReplicas(datos.replicas);   // /api/simular trae réplicas; /api/muestra no

  $$(".btn, .btn-chico").forEach((b) => (b.disabled = false));
  $("#btn-otra").disabled = false;
  boton.textContent = texto;
}

// Una corrida de muestra: número de corrida, tarjetas chicas y tabla.
function pintarMuestra(d) {
  const r = d.jornada.resumen;
  const ingreso = r.ganancia_bruta, costoMP = r.costo_total;

  $("#muestra-nro").textContent =
    `· corrida N° ${d.muestra_nro} de ${d.total_corridas} · S=${d.stock}` +
    (d.stock === 0 ? " (sin pre-elaboración)" : "");

  // Tarjetas chicas de la corrida mostrada (el último campo opcional es una sub-línea)
  const cards = [
    ["Atendidos", r.atendidos, "cyan"],
    ["Se retiraron", r.perdidos_tolerancia, "rojo"],
    ["Ingreso", plata(ingreso), ""],
    ["Costo materia prima", plata(costoMP), "amarillo"],
    ["Ganancia neta", plata(r.ganancia_neta), "verde"],
    ["Costo oportunidad", plata(r.perdida_oportunidad), "rojo"],
    ["Espera máx.", num(r.espera_maxima, 1) + " min", ""],
    ["Stock rem. y desperdicio",
      `${Math.ceil(r.stock_remanente)} <span class="costo-inline">= ${plata(r.desperdicio)}</span>`, "amarillo"],
  ];
  $("#cards-resumen").innerHTML = cards.map(([k, v, c]) =>
    `<div class="card ${c}"><div class="etiqueta">${k}</div><div class="valor ${c}">${v}</div></div>`).join("");

  // Tabla traza (los que se retiran: fila resaltada y TE en rojo)
  $("#tabla-jornada tbody").innerHTML = d.jornada.filas.map((f) => {
    const te = f.atendido ? num(f.TE, 1) : `<span class="badge-rojo">${num(f.TE, 1)}</span>`;
    return `
    <tr class="${f.atendido ? "" : "retiro"}">
      <td>${f.N}</td>
      <td>${num(f.r1, 7)}</td>
      <td>${num(f.TA, 1)}</td>
      <td>${hora(f.HL)}</td>
      <td>${num(f.r2, 7)}</td>
      <td>${f.M}</td>
      <td>${num(f.TP, 1)}</td>
      <td>${f.NC}</td>
      <td>${hora(f.HI)}</td>
      <td>${te}</td>
      <td>${hora(f.HF)}</td>
      <td>${f.stock}</td>
      <td class="${f.atendido ? "verde" : "rojo"}">${f.atendido ? "Atendido" : "Se retiró"}</td>
    </tr>`;
  }).join("");
}

// Datos resultantes de las N réplicas. Una tabla con, por variable de respuesta:
// media, semiancho positivo (media ± semiancho) e intervalo de confianza del 95%.
// El separador "Dinero" divide los conteos/tiempos de las variables en pesos.
const FILAS_DATOS = [
  ["Milanesas vendidas",   "milanesas_vendidas",  num,   ""],
  ["Stock remanente",      "stock_remanente",     num,   ""],
  ["Clientes atendidos",   "atendidos",           num,   ""],
  ["Se retiraron",         "perdidos_tolerancia", num,   ""],
  ["Espera media (min)",   "espera_promedio",     num,   ""],
  ["Espera máxima (min)",  "espera_maxima",       num,   ""],
  ["Espera mínima (min)",  "espera_minima",       num,   ""],
  ["__SUB__",              "Dinero",              null,  ""],
  ["Ingreso",              "ganancia_bruta",      plata, ""],
  ["Costo materia prima",  "costo_total",         plata, "amarillo"],
  ["Costo de desperdicio", "desperdicio",         plata, "rojo"],
  ["Costo de oportunidad", "perdida_oportunidad", plata, "rojo"],
  ["Ganancia neta",        "ganancia_neta",       plata, "verde"],
];

function pintarReplicas(rep) {
  $("#rep-n").textContent = rep.corridas;
  const ic = rep.intervalos || {};
  $("#tabla-datos tbody").innerHTML = FILAS_DATOS.map(([etiqueta, clave, fmt, color]) => {
    if (etiqueta === "__SUB__") {
      return `<tr class="sub-datos"><td colspan="4">${clave}</td></tr>`;
    }
    const e = ic[clave];
    if (!e) return "";
    return `<tr>
      <td class="col-var ${color}">${etiqueta}</td>
      <td class="${color}">${fmt(e.media)}</td>
      <td>± ${fmt(e.semiancho)}</td>
      <td>[ ${fmt(e.ic_bajo)} ; ${fmt(e.ic_alto)} ]</td>
    </tr>`;
  }).join("");
}

$("#btn-correr").addEventListener("click", (e) => correr("/api/simular", e.currentTarget));
$("#btn-otra").addEventListener("click", (e) => correr("/api/simular", e.currentTarget));
$("#btn-muestra").addEventListener("click", (e) => correr("/api/muestra", e.currentTarget));

// ---------- Stock óptimo (barrido) ----------
$("#btn-optimo").addEventListener("click", () => irA("vista-optimo"));
$("#btn-volver").addEventListener("click", () => irA("vista-simular", "simular"));

// No permitir más de 8000 corridas por stock.
$("#opt-corridas").addEventListener("input", (e) => {
  if (+e.target.value > 8000) e.target.value = 8000;
});

async function encontrarOptimo(boton) {
  const desde = parseInt($("#opt-desde").value, 10) || 0;
  const hasta = parseInt($("#opt-hasta").value, 10) || 0;
  const corridas = Math.min(parseInt($("#opt-corridas").value, 10) || 1, 8000);
  if (hasta < desde) { toast("El 'hasta' debe ser mayor o igual al 'desde'.", "error"); return; }

  const texto = boton.textContent;
  boton.disabled = true;
  boton.textContent = `Probando ${hasta - desde + 1} stocks…`;
  const { datos } = await pedir("/api/barrido", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ desde, hasta, corridas }),
  });
  dibujarBarrido(datos);
  boton.disabled = false;
  boton.textContent = texto;
}

// Columnas del barrido: [nombre completo, clave, formateador, claseColor].
// Cada celda muestra "media ± semiancho" centrada en la columna (media a la
// izquierda del centro, semiancho positivo a la derecha).
const COLS_BARRIDO = [
  ["Atendidos",            "atendidos",           num,    ""],
  ["Milanesas vendidas",   "milanesas_vendidas",  num,    ""],
  ["Retirados",            "perdidos_tolerancia", num,    ""],
  ["Espera media (min)",   "espera_promedio",     num,    ""],
  ["Stock remanente",      "stock_remanente",     num,    ""],
  ["Ingreso",              "ganancia_bruta",      plataR, ""],
  ["Costo materia prima",  "costo_total",         plataR, "amarillo"],
  ["Desperdicio",          "desperdicio",         plataR, "rojo"],
  ["Costo de oportunidad", "perdida_oportunidad", plataR, "rojo"],
  ["Ganancia neta",        "ganancia_neta",       plataR, "verde"],
];

function semiDe(f, clave) {
  return f.intervalos && f.intervalos[clave] ? f.intervalos[clave].semiancho : 0;
}

function celdaMS(f, clave, fmt, color) {
  return `<td class="celda-ms ${color}">` +
    `<span class="ms-media">${fmt(f[clave])}</span>` +
    `<span class="ms-semi">± ${fmt(semiDe(f, clave))}</span></td>`;
}

function dibujarBarrido(d) {
  $("#opt-placeholder").classList.add("oculto");
  $("#opt-resultado").classList.remove("oculto");
  $("#nota-corridas").textContent = `Se hacen ${d.corridas} corridas por cada stock.`;

  // Stock óptimo: 4 cuadritos chicos (entran en una línea), cada uno con su semiancho.
  const opt = d.filas[d.optimo_indice];
  const destacados = [
    ["Ganancia neta",      "ganancia_neta",       plata, "verde"],
    ["Clientes atendidos", "atendidos",           num,   ""],
    ["Costo oportunidad",  "perdida_oportunidad", plata, "rojo"],
    ["Desperdicio",        "desperdicio",         plata, "amarillo"],
  ];
  $("#opt-destacado").innerHTML =
    `<div class="titulo-promedio">Stock óptimo: ${opt.stock}</div>` +
    `<div class="grid-chicas">` +
    destacados.map(([label, clave, fmt, color]) =>
      `<div class="metrica metrica-chica ${color}">` +
      `<span class="k">${label}</span>` +
      `<span class="v ${color}">${fmt(opt[clave])}</span>` +
      `<span class="semi">± ${fmt(semiDe(opt, clave))}</span></div>`).join("") +
    `</div>`;

  // Encabezado (nombres completos, centrados) + filas con media ± semiancho.
  $("#tabla-barrido thead").innerHTML =
    `<tr><th class="col-stock">Stock</th>` +
    COLS_BARRIDO.map(([label]) => `<th>${label}</th>`).join("") + `</tr>`;

  $("#tabla-barrido tbody").innerHTML = d.filas.map((f, i) =>
    `<tr class="${i === d.optimo_indice ? "optima" : ""}">` +
    `<td class="col-stock">${f.stock}</td>` +
    COLS_BARRIDO.map(([, clave, fmt, color]) => celdaMS(f, clave, fmt, color)).join("") +
    `</tr>`).join("");
}

$("#btn-encontrar").addEventListener("click", (e) => encontrarOptimo(e.currentTarget));

cargarEstado();
