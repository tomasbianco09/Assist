/* Assist móvil - Pantalla de consentimiento (HU-03)
   Usa la misma API y la misma base de datos (assist.db) que el panel web. */

const params = new URLSearchParams(location.search);

// --- Configuración -------------------------------------------------------
// ?api=http://192.168.0.10:8000  -> API en otra máquina (ej. probando desde el celular)
// ?adulto=2                      -> ID del adulto mayor dueño de este celular
// ?demo=1                        -> muestra el modo prueba
function setting(key, fallback) {
  const fromUrl = params.get(key);
  if (fromUrl) { try { localStorage.setItem('assist_' + key, fromUrl); } catch (e) {} return fromUrl; }
  try { return localStorage.getItem('assist_' + key) || fallback; } catch (e) { return fallback; }
}
const defaultApi = location.protocol.startsWith('http')
  ? `${location.protocol}//${location.hostname}:8000`
  : 'http://localhost:8000';
const API = setting('api', defaultApi).replace(/\/$/, '');
const ADULTO_ID = parseInt(setting('adulto', '2'), 10);
const POLL_MS = 3000;

const $screen = document.getElementById('screen');
const $who = document.getElementById('who');
let current = '';      // clave de la pantalla actual (evita re-dibujar sin cambios)
let busy = false;      // hay una petición del usuario en curso
let pausePolling = false;

// --- Utilidades ----------------------------------------------------------
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path, options) {
  const res = await fetch(API + path, options);
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) || 'Error ' + res.status);
  return data;
}

function show(key, html, focusSel) {
  if (key === current) return;
  current = key;
  $screen.innerHTML = html;
  const el = focusSel && $screen.querySelector(focusSel);
  if (el) el.focus();
}

const eyeIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/></svg>';

// --- Pantallas -----------------------------------------------------------
function viewIdle() {
  show('idle', `
    <div class="stack center">
      <div class="phone" aria-hidden="true">${eyeIcon}</div>
      <h1>Tu pantalla es solo tuya</h1>
      <p class="lead">Nadie puede verla ahora. Si un familiar quiere ayudarte, te vamos a preguntar antes.</p>
      <p class="status"><span class="dot" aria-hidden="true"></span> Esperando solicitudes</p>
    </div>`);
}

function viewConsent(s) {
  const nombre = esc(s.familiar_nombre);
  const inicial = esc(s.familiar_nombre.trim().charAt(0).toUpperCase() || '?');
  show('consent-' + s.sesion_id, `
    <div class="stack">
      <div class="request" aria-hidden="true">
        <div class="avatar">${inicial}</div><div class="link"></div>
        <div class="phone">${eyeIcon}</div>
      </div>
      <h1 id="q" tabindex="-1">¿Permites que ${nombre} vea tu pantalla?</h1>
      <ul class="rules" aria-label="Qué significa permitir">
        <li><span class="ic yes" aria-hidden="true">✓</span><span>${nombre} podrá ver lo que aparece en tu pantalla.</span></li>
        <li><span class="ic no" aria-hidden="true">✕</span><span>No podrá tocar ni cambiar nada.</span></li>
        <li><span class="ic yes" aria-hidden="true">✓</span><span>Puedes dejar de compartir cuando quieras.</span></li>
      </ul>
      <p class="lead">Si no aceptas, ${nombre} no verá nada.</p>
      <div class="actions">
        <button class="btn permit" id="yes" type="button">Permitir</button>
        <button class="btn" id="no" type="button">No permitir</button>
      </div>
      <p class="error" id="err" role="alert" hidden></p>
    </div>`, '#q');
  document.getElementById('yes').onclick = () => responder(s, true);
  document.getElementById('no').onclick = () => responder(s, false);
}

function viewActive(s) {
  const nombre = esc(s.familiar_nombre);
  show('active-' + s.sesion_id, `
    <div class="stack">
      <div class="live" role="status"><span class="dot" aria-hidden="true"></span> ${nombre} está viendo tu pantalla</div>
      <div class="request" aria-hidden="true">
        <div class="avatar">${esc(s.familiar_nombre.trim().charAt(0).toUpperCase() || '?')}</div>
        <div class="link" style="border-color:var(--permit)"></div>
        <div class="phone on">${eyeIcon}</div>
      </div>
      <p class="lead">${nombre} solo puede mirar. No puede tocar ni cambiar nada en tu teléfono.</p>
      <div class="actions">
        <button class="btn stop" id="stop" type="button">Dejar de compartir</button>
      </div>
      <p class="error" id="err" role="alert" hidden></p>
    </div>`, '.live');
  document.getElementById('stop').onclick = () => finalizar(s);
}

function viewEnded(kind, nombre) {
  const msg = kind === 'rechazada'
    ? [`No se compartió nada`, `Le avisamos a ${esc(nombre)} que no aceptaste. Tu pantalla sigue siendo solo tuya.`]
    : [`Dejaste de compartir`, `${esc(nombre)} ya no puede ver tu pantalla.`];
  show('ended-' + kind, `
    <div class="stack center">
      <div class="phone" aria-hidden="true">${eyeIcon}</div>
      <h1 id="t" tabindex="-1">${msg[0]}</h1>
      <p class="lead">${msg[1]}</p>
      <div class="actions" style="width:100%"><button class="btn" id="ok" type="button">Volver al inicio</button></div>
    </div>`, '#t');
  pausePolling = true;
  document.getElementById('ok').onclick = () => { pausePolling = false; current = ''; refresh(); };
}

function viewError(text) {
  show('error', `
    <div class="stack center">
      <h1 id="t" tabindex="-1">No pudimos conectarnos</h1>
      <p class="lead">Revisa tu conexión a internet. Lo intentaremos de nuevo solos.</p>
      <p class="lead"><small>${esc(text)}</small></p>
    </div>`, '#t');
}

// --- Acciones ------------------------------------------------------------
function showInlineError(msg) {
  const e = document.getElementById('err');
  if (e) { e.textContent = msg; e.hidden = false; }
}

async function responder(s, aceptar) {
  if (busy) return; busy = true;
  document.querySelectorAll('.btn').forEach(b => b.disabled = true);
  try {
    await api(`/sesiones/${s.sesion_id}/responder/?aceptar=${aceptar}`, { method: 'PUT' });
    busy = false;
    aceptar ? viewActive({ ...s, estado: 'activa' }) : viewEnded('rechazada', s.familiar_nombre);
  } catch (e) {
    busy = false;
    document.querySelectorAll('.btn').forEach(b => b.disabled = false);
    showInlineError('No se pudo guardar tu respuesta. ' + e.message + ' Inténtalo otra vez.');
  }
}

async function finalizar(s) {
  if (busy) return; busy = true;
  document.querySelectorAll('.btn').forEach(b => b.disabled = true);
  try {
    await api(`/sesiones/${s.sesion_id}/finalizar/`, { method: 'PUT' });
    busy = false;
    viewEnded('finalizada', s.familiar_nombre);
  } catch (e) {
    busy = false;
    document.querySelectorAll('.btn').forEach(b => b.disabled = false);
    showInlineError('No se pudo dejar de compartir. ' + e.message + ' Inténtalo otra vez.');
  }
}

// --- Ciclo principal -----------------------------------------------------
async function refresh() {
  if (busy || pausePolling) return;
  try {
    const sesiones = await api(`/sesiones/pendientes/${ADULTO_ID}`);
    if (busy || pausePolling) return;
    const activa = sesiones.find(s => s.estado === 'activa');
    const pendiente = sesiones.find(s => s.estado === 'pendiente_consentimiento');
    if (activa) viewActive(activa);
    else if (pendiente) viewConsent(pendiente);
    else viewIdle();
  } catch (e) {
    viewError(e.message);
  }
}

async function init() {
  try {
    const u = await api(`/usuarios/${ADULTO_ID}`);
    $who.textContent = u.nombre;
  } catch (e) { /* el error se muestra en refresh() */ }
  refresh();
  setInterval(refresh, POLL_MS);
}

// --- Modo prueba (?demo=1) -----------------------------------------------
if (params.get('demo')) {
  document.getElementById('demo').hidden = false;
  document.getElementById('demoBtn').onclick = async () => {
    const msg = document.getElementById('demoMsg');
    try {
      const vinculo_id = parseInt(document.getElementById('demoVinculo').value, 10);
      const r = await api('/sesiones/solicitar/', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vinculo_id })
      });
      msg.textContent = 'Solicitud #' + r.sesion_id + ' enviada.';
      refresh();
    } catch (e) { msg.textContent = 'Error: ' + e.message; }
  };
}

init();
