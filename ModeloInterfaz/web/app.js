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

  // Mostrar el factor de afluencia actual en la pantalla de stock óptimo.
  const fa = estado.parametros.find((p) => p.clave === "FA");
  if (fa) {
    const etiqueta = fa.valor === 1 ? " (semana)" : fa.valor === 0.7 ? " (sábado)" : "";
    $("#nota-fa").textContent = fa.valor + etiqueta;
  }
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
let ultimoModo = null;

async function correr(url, modo, boton) {
  ultimoModo = modo;
  const texto = boton.textContent;
  $$(".btn, .btn-chico").forEach((b) => (b.disabled = true));
  boton.textContent = "Calculando…";

  const { datos } = await pedir(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modo }),
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
    `· corrida N° ${d.muestra_nro} de ${d.total_corridas} · ` +
    (d.modo === "con" ? `CON stock (S=${d.stock})` : "SIN stock (S=0)");

  // Tarjetas chicas de la corrida mostrada (el último campo opcional es una sub-línea)
  const cards = [
    ["Atendidos", r.atendidos, "cyan"],
    ["Se retiraron", r.perdidos_tolerancia, "rojo"],
    ["Ingreso", plata(ingreso), ""],
    ["Costo materia prima", plata(costoMP), "amarillo"],
    ["Ganancia neta", plata(r.ganancia_neta), "verde"],
    ["Costo oportunidad", plata(r.perdida_oportunidad), "rojo"],
    ["Espera prom.", num(r.espera_promedio, 1) + " min", ""],
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

// Promedio de las N corridas. Atendidos y milanesas: entero hacia arriba.
function pintarReplicas(rep) {
  $("#rep-n").textContent = rep.corridas;
  const metricas = [
    ["Clientes atendidos", Math.ceil(rep.atendidos), ""],
    ["Milanesas vendidas", Math.ceil(rep.milanesas_vendidas), ""],
    ["Se retiraron", Math.ceil(rep.perdidos_tolerancia), ""],
    ["Espera promedio (min)", num(rep.espera_promedio), ""],
    ["Espera máxima (min)", num(rep.espera_maxima), ""],
    ["Stock rem. y desperdicio",
      `${Math.ceil(rep.stock_remanente)} <span class="costo-inline">= ${plata(rep.desperdicio)}</span>`, "amarillo"],
    ["Ingreso", plata(rep.ganancia_bruta), ""],
    ["Costo materia prima", plata(rep.costo_total), "amarillo"],
    ["Costo oportunidad", plata(rep.perdida_oportunidad), "rojo"],
    ["Ganancia neta", plata(rep.ganancia_neta), "verde"],
  ];
  $("#grid-replicas").innerHTML = metricas.map(([k, v, c]) =>
    `<div class="metrica ${c}"><span class="k">${k}</span><span class="v ${c}">${v}</span></div>`).join("");
}

$("#btn-con").addEventListener("click", (e) => correr("/api/simular", "con", e.currentTarget));
$("#btn-sin").addEventListener("click", (e) => correr("/api/simular", "sin", e.currentTarget));
$("#btn-otra").addEventListener("click", (e) => { if (ultimoModo) correr("/api/simular", ultimoModo, e.currentTarget); });
$("#btn-muestra").addEventListener("click", (e) => { if (ultimoModo) correr("/api/muestra", ultimoModo, e.currentTarget); });

// ---------- Stock óptimo (barrido) ----------
$("#btn-optimo").addEventListener("click", () => irA("vista-optimo"));
$("#btn-volver").addEventListener("click", () => irA("vista-simular", "simular"));

async function encontrarOptimo(boton) {
  const desde = parseInt($("#opt-desde").value, 10) || 0;
  const hasta = parseInt($("#opt-hasta").value, 10) || 0;
  const corridas = parseInt($("#opt-corridas").value, 10) || 1;
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

function dibujarBarrido(d) {
  $("#opt-placeholder").classList.add("oculto");
  $("#opt-resultado").classList.remove("oculto");
  $("#nota-corridas").textContent = `Se hacen ${d.corridas} corridas por cada stock.`;

  const opt = d.filas[d.optimo_indice];
  $("#opt-destacado").innerHTML =
    `<div class="titulo-promedio">Stock óptimo: ${opt.stock}</div>` +
    `<div class="grid-replicas">` +
    `<div class="metrica verde"><span class="k">Ganancia neta</span><span class="v verde">${plata(opt.ganancia_neta)}</span></div>` +
    `<div class="metrica"><span class="k">Clientes atendidos</span><span class="v">${Math.ceil(opt.atendidos)}</span></div>` +
    `<div class="metrica rojo"><span class="k">Costo oportunidad</span><span class="v rojo">${plata(opt.perdida_oportunidad)}</span></div>` +
    `<div class="metrica amarillo"><span class="k">Desperdicio</span><span class="v">${plata(opt.desperdicio)}</span></div>` +
    `</div>`;

  $("#tabla-barrido tbody").innerHTML = d.filas.map((f, i) => `
    <tr class="${i === d.optimo_indice ? "optima" : ""}">
      <td>${f.stock}</td>
      <td>${Math.ceil(f.atendidos)}</td>
      <td>${Math.ceil(f.milanesas_vendidas)}</td>
      <td>${Math.ceil(f.perdidos_tolerancia)}</td>
      <td>${num(f.espera_promedio)}</td>
      <td>${num(f.espera_maxima)}</td>
      <td>${Math.ceil(f.stock_remanente)}</td>
      <td>${plataR(f.ganancia_bruta)}</td>
      <td>${plataR(f.costo_total)}</td>
      <td>${plataR(f.desperdicio)}</td>
      <td>${plataR(f.perdida_oportunidad)}</td>
      <td class="verde">${plataR(f.ganancia_neta)}</td>
    </tr>`).join("");
}

$("#btn-encontrar").addEventListener("click", (e) => encontrarOptimo(e.currentTarget));

cargarEstado();
