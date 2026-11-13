/* Assist móvil - celular del adulto mayor
   - Ingreso con el email registrado y salida de la cuenta (con confirmación).
   - Pantalla de consentimiento (HU-03) y botón para dejar de compartir.
   - Alto contraste (se recuerda en el celular).
   Usa la misma API y la misma base de datos (assist.db) que el panel web. */

const params = new URLSearchParams(location.search);

// --- Configuración -------------------------------------------------------
// ?api=http://192.168.0.10:8000  -> API en otra máquina (ej. probando desde el celular)
// ?adulto=2                      -> entra directo como ese adulto mayor (atajo para probar)
// ?demo=1                        -> muestra el modo prueba
function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem('assist_' + key);
    if (value === null) localStorage.removeItem('assist_' + key);
    else localStorage.setItem('assist_' + key, value);
  } catch (e) { return null; }
}
function setting(key, fallback) {
  const fromUrl = params.get(key);
  if (fromUrl) { store(key, fromUrl); return fromUrl; }
  return store(key) || fallback;
}
const defaultApi = location.protocol.startsWith('http')
  ? `${location.protocol}//${location.hostname}:8000`
  : 'http://localhost:8000';
const API = setting('api', defaultApi).replace(/\/$/, '');
const POLL_MS = 3000;

const $screen = document.getElementById('screen');
const $opts = document.getElementById('opts');
const $hc = document.getElementById('hcSwitch');
let usuario = loadUser(); // { id, nombre, email } del adulto mayor que usa este celular
let sesiones = [];        // última respuesta de /sesiones/pendientes
let current = '';         // clave de la pantalla actual (evita re-dibujar sin cambios)
let busy = false;         // hay una petición del usuario en curso
let pausePolling = false;
let timer = null;

// --- Utilidades ----------------------------------------------------------
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inicial = nombre => esc(String(nombre).trim().charAt(0).toUpperCase() || '?');
const primerNombre = nombre => String(nombre).trim().split(/\s+/)[0];

async function api(path, options) {
  const res = await fetch(API + path, options);
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) || 'Error ' + res.status);
  return data;
}
const json = body => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function show(key, html, focusSel) {
  if (key === current) return;
  current = key;
  $screen.innerHTML = html;
  const el = $screen.querySelector(focusSel || 'h1');
  if (el) { if (!el.hasAttribute('tabindex') && !el.matches('input,button')) el.tabIndex = -1; el.focus({ preventScroll: false }); }
}

function setBusy(on) {
  busy = on;
  $screen.querySelectorAll('.btn').forEach(b => b.disabled = on);
}
function showInlineError(msg) {
  const e = document.getElementById('err');
  if (e) { e.textContent = msg; e.hidden = false; }
}

const eyeIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const stopIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';

// --- Cuenta --------------------------------------------------------------
function loadUser() {
  try { return JSON.parse(store('usuario')) || null; } catch (e) { return null; }
}
function saveUser(u) {
  usuario = { id: u.id, nombre: u.nombre, email: u.email };
  store('usuario', JSON.stringify(usuario));
  renderAccount();
}
function clearUser() {
  usuario = null;
  store('usuario', null);
  store('adulto', null); // versión anterior guardaba solo el ID
  renderAccount();
}
function renderAccount() {
  document.getElementById('account').hidden = !usuario;
  if (usuario) {
    document.getElementById('accName').textContent = usuario.nombre;
    document.getElementById('accEmail').textContent = usuario.email || '';
  }
}

function startPolling() {
  stopPolling();
  pausePolling = false;
  current = '';
  refresh();
  timer = setInterval(refresh, POLL_MS);
}
function stopPolling() {
  clearInterval(timer);
  timer = null;
}

// --- Pantallas -----------------------------------------------------------
function viewLogin(aviso) {
  show('login' + (aviso ? '-aviso' : ''), `
    <div class="stack">
      <p class="kicker">Te damos la bienvenida</p>
      <h1>Entra a tu cuenta</h1>
      ${aviso ? `<p class="note" role="status">${esc(aviso)}</p>` : ''}
      <form class="form" id="loginForm" novalidate>
        <label for="email">Tu correo electrónico</label>
        <input class="field" id="email" type="email" autocomplete="email" inputmode="email"
               autocapitalize="off" spellcheck="false" placeholder="nombre@correo.com" required>
        <p class="error" id="err" role="alert" hidden></p>
        <div class="actions">
          <button class="btn primary" type="submit">Entrar</button>
        </div>
      </form>
      <p class="lead small">¿No tienes cuenta? Pídele a un familiar que te registre en Assist.</p>
    </div>`);
  document.getElementById('loginForm').onsubmit = ingresar;
}

function viewIdle() {
  show('idle', `
    <div class="stack center">
      <div class="phone" aria-hidden="true">${eyeIcon}</div>
      <p class="kicker">Hola, ${esc(primerNombre(usuario.nombre))}</p>
      <h1>Tu pantalla es solo tuya</h1>
      <p class="lead">Nadie puede verla ahora. Si un familiar quiere ayudarte, te vamos a preguntar antes.</p>
      <p class="status"><span class="dot" aria-hidden="true"></span> Esperando solicitudes</p>
    </div>`);
}

function viewConsent(s) {
  const nombre = esc(s.familiar_nombre);
  show('consent-' + s.sesion_id, `
    <div class="stack">
      <div class="request" aria-hidden="true">
        <div class="avatar">${inicial(s.familiar_nombre)}</div><div class="link"></div>
        <div class="phone">${eyeIcon}</div>
      </div>
      <h1>¿Permites que ${nombre} vea tu pantalla?</h1>
      <ul class="rules" aria-label="Qué significa permitir">
        <li><span class="ic yes" aria-hidden="true">✓</span><span>${nombre} podrá ver lo que aparece en tu pantalla.</span></li>
        <li><span class="ic no" aria-hidden="true">✕</span><span>No podrá tocar ni cambiar nada.</span></li>
        <li><span class="ic yes" aria-hidden="true">✓</span><span>Puedes dejar de compartir cuando quieras.</span></li>
      </ul>
      <p class="lead">Si no aceptas, ${nombre} no verá nada.</p>
      <p class="error" id="err" role="alert" hidden></p>
      <div class="actions">
        <button class="btn primary" id="yes" type="button">Permitir</button>
        <button class="btn" id="no" type="button">No permitir</button>
      </div>
    </div>`);
  document.getElementById('yes').onclick = () => responder(s, true);
  document.getElementById('no').onclick = () => responder(s, false);
}

function viewActive(s) {
  const nombre = esc(s.familiar_nombre);
  show('active-' + s.sesion_id, `
    <div class="stack">
      <div class="live" role="status"><span class="dot" aria-hidden="true"></span> ${nombre} está viendo tu pantalla</div>
      <div class="request" aria-hidden="true">
        <div class="avatar">${inicial(s.familiar_nombre)}</div>
        <div class="link on"></div>
        <div class="phone on">${eyeIcon}</div>
      </div>
      <h1>Estás compartiendo tu pantalla</h1>
      <p class="lead">${nombre} solo puede mirar. No puede tocar ni cambiar nada en tu teléfono.</p>
      <p class="error" id="err" role="alert" hidden></p>
      <div class="actions sticky">
        <button class="btn stop" id="stop" type="button">${stopIcon} Dejar de compartir</button>
      </div>
    </div>`, '.live');
  // Cortar tiene que ser inmediato: un solo toque, sin "¿estás seguro?".
  document.getElementById('stop').onclick = () => finalizar(s);
}

function viewEnded(kind, nombre) {
  const msg = kind === 'rechazada'
    ? [`No se compartió nada`, `Le avisamos a ${esc(nombre)} que no aceptaste. Tu pantalla sigue siendo solo tuya.`]
    : [`Dejaste de compartir`, `${esc(nombre)} ya no puede ver tu pantalla.`];
  pausePolling = true;
  show('ended-' + kind, `
    <div class="stack center">
      <div class="phone" aria-hidden="true">${eyeIcon}</div>
      <h1>${msg[0]}</h1>
      <p class="lead">${msg[1]}</p>
      <div class="actions" style="width:100%"><button class="btn" id="ok" type="button">Volver al inicio</button></div>
    </div>`);
  document.getElementById('ok').onclick = () => { pausePolling = false; current = ''; refresh(); };
}

// Salir de la cuenta: para una persona mayor, salir sin querer significa quedar
// desconectada de su familia. Por eso está dentro de "Opciones", se confirma en
// una pantalla completa y el botón principal (y el foco) es "Quedarme".
function viewLogoutConfirm() {
  pausePolling = true;
  const activa = sesiones.find(s => s.estado === 'activa');
  const pendiente = sesiones.find(s => s.estado === 'pendiente_consentimiento');
  show('logout', `
    <div class="stack">
      <h1>¿Quieres salir de tu cuenta?</h1>
      <ul class="rules" aria-label="Qué pasa si sales">
        ${activa ? `<li><span class="ic no" aria-hidden="true">✕</span><span>${esc(activa.familiar_nombre)} dejará de ver tu pantalla ahora mismo.</span></li>` : ''}
        ${pendiente ? `<li><span class="ic no" aria-hidden="true">✕</span><span>La solicitud de ${esc(pendiente.familiar_nombre)} quedará rechazada.</span></li>` : ''}
        <li><span class="ic no" aria-hidden="true">✕</span><span>Tus familiares no podrán pedirte ver tu pantalla hasta que vuelvas a entrar.</span></li>
        <li><span class="ic yes" aria-hidden="true">✓</span><span>Para volver a entrar vas a necesitar tu correo: <strong class="account-who">${esc(usuario.email || '')}</strong></span></li>
      </ul>
      <p class="error" id="err" role="alert" hidden></p>
      <div class="actions">
        <button class="btn primary" id="stay" type="button">Quedarme</button>
        <button class="btn" id="leave" type="button">Sí, salir</button>
      </div>
    </div>`, '#stay');
  document.getElementById('stay').onclick = () => { pausePolling = false; current = ''; refresh(); };
  document.getElementById('leave').onclick = salir;
}

function viewError(text) {
  show('error', `
    <div class="stack center">
      <h1>No pudimos conectarnos</h1>
      <p class="lead">Revisa tu conexión a internet. Lo intentaremos de nuevo solos.</p>
      <p class="lead"><small>${esc(text)}</small></p>
    </div>`);
}

// --- Acciones ------------------------------------------------------------
async function ingresar(ev) {
  ev.preventDefault();
  if (busy) return;
  const email = document.getElementById('email').value.trim();
  if (!email) { showInlineError('Escribe tu correo electrónico para entrar.'); return; }
  setBusy(true);
  try {
    const u = await api('/usuarios/ingresar/', json({ email }));
    if (u.rol !== 'adulto_mayor') {
      throw new Error('Ese correo es de un familiar. Esta app es para el celular de la persona que recibe ayuda.');
    }
    setBusy(false);
    saveUser(u);
    startPolling();
  } catch (e) {
    setBusy(false);
    showInlineError(e.message);
  }
}

async function salir() {
  if (busy) return;
  setBusy(true);
  try {
    // El servidor corta lo que haya abierto, así el familiar no queda esperando.
    await api(`/usuarios/${usuario.id}/salir/`, { method: 'POST' });
  } catch (e) {
    setBusy(false);
    showInlineError('No pudimos cerrar tu sesión. ' + e.message + ' Inténtalo otra vez.');
    return;
  }
  setBusy(false);
  stopPolling();
  clearUser();
  sesiones = [];
  viewLogin('Saliste de tu cuenta. Puedes volver a entrar cuando quieras.');
}

async function responder(s, aceptar) {
  if (busy) return;
  setBusy(true);
  try {
    await api(`/sesiones/${s.sesion_id}/responder/?aceptar=${aceptar}`, { method: 'PUT' });
    setBusy(false);
    aceptar ? viewActive({ ...s, estado: 'activa' }) : viewEnded('rechazada', s.familiar_nombre);
  } catch (e) {
    setBusy(false);
    showInlineError('No se pudo guardar tu respuesta. ' + e.message + ' Inténtalo otra vez.');
  }
}

async function finalizar(s) {
  if (busy) return;
  setBusy(true);
  try {
    await api(`/sesiones/${s.sesion_id}/finalizar/`, { method: 'PUT' });
    setBusy(false);
    viewEnded('finalizada', s.familiar_nombre);
  } catch (e) {
    setBusy(false);
    showInlineError('No se pudo dejar de compartir. ' + e.message + ' Inténtalo otra vez.');
  }
}

// --- Ciclo principal -----------------------------------------------------
async function refresh() {
  if (!usuario || busy || pausePolling) return;
  try {
    const data = await api(`/sesiones/pendientes/${usuario.id}`);
    if (!usuario || busy || pausePolling) return;
    sesiones = data;
    const activa = data.find(s => s.estado === 'activa');
    const pendiente = data.find(s => s.estado === 'pendiente_consentimiento');
    if (activa) viewActive(activa);
    else if (pendiente) viewConsent(pendiente);
    else viewIdle();
  } catch (e) {
    viewError(e.message);
  }
}

async function init() {
  renderAccount();
  // Atajo para probar: ?adulto=ID entra directo. Se quita de la dirección para
  // que, después de salir, recargar la página no vuelva a entrar solo.
  const adultoParam = params.get('adulto');
  if (adultoParam) {
    params.delete('adulto');
    history.replaceState(null, '', location.pathname + (params.toString() ? '?' + params : '') + location.hash);
    try {
      const u = await api(`/usuarios/${parseInt(adultoParam, 10)}`);
      if (u.rol === 'adulto_mayor') saveUser(u);
    } catch (e) { /* si falla, se muestra el ingreso */ }
  }
  if (usuario) startPolling();
  else viewLogin();
}

// --- Opciones: alto contraste y cuenta -----------------------------------
function applyContrast(alto) {
  document.documentElement.dataset.contrast = alto ? 'high' : 'normal';
  $hc.setAttribute('aria-checked', String(alto));
  document.querySelector('meta[name="theme-color"]').content = alto ? '#000000' : '#F4EEE3';
}
applyContrast(document.documentElement.dataset.contrast === 'high');

$hc.onclick = () => {
  const alto = $hc.getAttribute('aria-checked') !== 'true';
  applyContrast(alto);
  store('contraste', alto ? 'alto' : 'normal');
};
// Si la persona nunca eligió, seguimos lo que diga el celular.
matchMedia('(prefers-contrast: more)').addEventListener('change', e => {
  if (!store('contraste')) applyContrast(e.matches);
});

document.getElementById('optsBtn').onclick = () => $opts.showModal();
document.getElementById('optsClose').onclick = () => $opts.close();
$opts.addEventListener('click', e => { // tocar afuera de la hoja la cierra
  if (e.target !== $opts) return;
  const r = $opts.getBoundingClientRect();
  if (e.clientY < r.top || e.clientY > r.bottom || e.clientX < r.left || e.clientX > r.right) $opts.close();
});
document.getElementById('logoutBtn').onclick = () => { $opts.close(); viewLogoutConfirm(); };

// --- Modo prueba (?demo=1) -----------------------------------------------
if (params.get('demo')) {
  document.getElementById('demo').hidden = false;
  document.getElementById('demoBtn').onclick = async () => {
    const msg = document.getElementById('demoMsg');
    try {
      const vinculo_id = parseInt(document.getElementById('demoVinculo').value, 10);
      const r = await api('/sesiones/solicitar/', json({ vinculo_id }));
      msg.textContent = 'Solicitud #' + r.sesion_id + ' enviada.';
      refresh();
    } catch (e) { msg.textContent = 'Error: ' + e.message; }
  };
}

init();
