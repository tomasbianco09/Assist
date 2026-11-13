const params = new URLSearchParams(location.search);

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

let usuario = loadUser();
let sesiones = [];
let ubicaciones = [];
let sesionActivaPrevia = null;
let current = '';
let busy = false;
let pausePolling = false;
let timer = null;

const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inicial = nombre => esc(String(nombre).trim().charAt(0).toUpperCase() || '?');
const primerNombre = nombre => String(nombre).trim().split(/\s+/)[0];

async function api(path, options) {
  let res;
  try {
    res = await fetch(API + path, options);
  } catch (err) {
    throw new Error('No pudimos conectarnos con el servidor. Revisa tu conexión a internet.');
  }
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) || 'Error ' + res.status);
  return data;
}

const json = body => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function show(key, html, focusSel) {
  if (!$screen || key === current) return;
  current = key;
  $screen.innerHTML = html;
  const el = $screen.querySelector(focusSel || 'h1');
  if (el) {
    if (!el.hasAttribute('tabindex') && !el.matches('input,button')) el.tabIndex = -1;
    el.focus({ preventScroll: false });
  }
}

function setBusy(on) {
  busy = on;
  if ($screen) $screen.querySelectorAll('.btn').forEach(b => b.disabled = on);
}

function showInlineError(msg) {
  const e = document.getElementById('err');
  if (e) { e.textContent = msg; e.hidden = false; }
}

const eyeIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const stopIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
const pinIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-5.5-7-11a7 7 0 1 1 14 0c0 5.5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>';

function ensureHistorySection() {
  let sec = document.getElementById('historySection');
  if (!sec && $opts) {
    sec = document.createElement('section');
    sec.className = 'account';
    sec.id = 'historySection';
    sec.hidden = true;
    sec.innerHTML = '<h3>Historial de asistencias</h3><ul class="rules" id="mobileHistoryList"><li><span>Todavía no hay sesiones registradas.</span></li></ul>';
    const acc = document.getElementById('account');
    if (acc && acc.parentNode === $opts) {
      $opts.insertBefore(sec, acc);
    } else {
      $opts.appendChild(sec);
    }
  }
  return sec;
}

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
  sesionActivaPrevia = null;
  store('usuario', null);
  store('adulto', null);
  renderAccount();
}

function renderAccount() {
  const acc = document.getElementById('account');
  const hist = ensureHistorySection();
  if (acc) acc.hidden = !usuario;
  if (hist) hist.hidden = !usuario;
  if (usuario) {
    const accName = document.getElementById('accName');
    const accEmail = document.getElementById('accEmail');
    if (accName) accName.textContent = usuario.nombre;
    if (accEmail) accEmail.textContent = usuario.email || '';
  }
}

async function cargarHistorialMovil() {
  if (!usuario) return;
  ensureHistorySection();
  try {
    const lista = await api(`/sesiones/historial/?adulto_id=${usuario.id}`);
    const ul = document.getElementById('mobileHistoryList');
    if (!ul) return;
    if (!lista || lista.length === 0) {
      ul.innerHTML = '<li><span>Todavía no hay sesiones registradas.</span></li>';
      return;
    }
    ul.innerHTML = lista.slice(0, 5).map(s => {
      const dur = s.duracion_segundos != null ? `${s.duracion_segundos} s` : 'en curso';
      return `<li><span class="ic yes" aria-hidden="true">•</span><span><strong>${esc(s.familiar_nombre)}</strong> · ${esc(s.estado)} (${dur})</span></li>`;
    }).join('');
  } catch (e) {}
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
  const form = document.getElementById('loginForm');
  if (form) form.onsubmit = ingresar;
}

function guideHtml() {
  const pasos = [
    ['Tu familiar te pide ayuda', 'Puede pedirte ver tu pantalla o saber dónde estás. Tú también puedes avisarle con el botón “Pedir ayuda a mi familia”.'],
    ['Tú decides', 'Te preguntamos antes. Toca Permitir o No permitir. Si no aceptas, no se comparte nada.'],
    ['Paras cuando quieras', 'Mientras compartes, el botón rojo “Dejar de compartir” siempre está a la vista.']
  ];
  return `
    <section class="guide" aria-labelledby="guideTitle">
      <h2 id="guideTitle">Así funciona</h2>
      <ol class="rules guide-steps" role="list">
        ${pasos.map((p, i) => `<li><span class="ic yes" aria-hidden="true">${i + 1}</span><span class="guide-text"><strong>${p[0]}</strong><span>${p[1]}</span></span></li>`).join('')}
      </ol>
    </section>`;
}

function viewIdle(avisoAyuda) {
  show('idle' + (avisoAyuda ? '-ayuda' : ''), `
    <div class="stack center">
      <div class="phone" aria-hidden="true">${eyeIcon}</div>
      <p class="kicker">Hola, ${esc(primerNombre(usuario.nombre))}</p>
      <h1>Tu pantalla es solo tuya</h1>
      <p class="lead">Nadie puede verla ahora. Si un familiar quiere ayudarte, te vamos a preguntar antes.</p>
      ${avisoAyuda ? `<p class="note" role="status">${esc(avisoAyuda)}</p>` : ''}
      <p class="error" id="err" role="alert" hidden></p>
      <p class="status"><span class="dot" aria-hidden="true"></span> Esperando solicitudes</p>
      <div class="actions" style="width:100%">
        <button class="btn primary" id="helpBtn" type="button">🚨 Pedir ayuda a mi familia</button>
      </div>
    </div>
    ${guideHtml()}`);
  const helpBtn = document.getElementById('helpBtn');
  if (helpBtn) helpBtn.onclick = pedirAyudaMovil;
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

function viewLocationConsent(u) {
  const nombre = esc(u.familiar_nombre);
  show('loc-' + u.ubicacion_id, `
    <div class="stack">
      <div class="request" aria-hidden="true">
        <div class="avatar">${inicial(u.familiar_nombre)}</div><div class="link"></div>
        <div class="phone">${pinIcon}</div>
      </div>
      <h1>${nombre} solicita tu ubicación</h1>
      <ul class="rules" aria-label="Qué significa compartir ubicación">
        <li><span class="ic yes" aria-hidden="true">✓</span><span>${nombre} verá en un mapa dónde te encuentras ahora mismo.</span></li>
        <li><span class="ic yes" aria-hidden="true">✓</span><span>Se comparte una sola vez para saber que estás a salvo.</span></li>
      </ul>
      <p class="error" id="err" role="alert" hidden></p>
      <div class="actions">
        <button class="btn primary" id="yesLoc" type="button">Compartir mi ubicación</button>
        <button class="btn" id="noLoc" type="button">No compartir</button>
      </div>
    </div>`);
  document.getElementById('yesLoc').onclick = () => responderUbicacion(u, true);
  document.getElementById('noLoc').onclick = () => responderUbicacion(u, false);
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
  document.getElementById('stop').onclick = () => finalizar(s);
}

function viewEnded(kind, nombre) {
  let msg;
  if (kind === 'rechazada') {
    msg = ['No se compartió nada', `Le avisamos a ${esc(nombre)} que no aceptaste. Tu pantalla sigue siendo solo tuya.`];
  } else if (kind === 'cortada_familiar') {
    msg = ['La sesión terminó', `${esc(nombre)} finalizó la asistencia y ya no está viendo tu pantalla.`];
  } else if (kind === 'ubicacion_ok') {
    msg = ['Ubicación enviada', `${esc(nombre)} ya recibió tu ubicación actual en el mapa.`];
  } else if (kind === 'ubicacion_no') {
    msg = ['Ubicación no compartida', `No enviamos tu ubicación a ${esc(nombre)}.`];
  } else {
    msg = ['Dejaste de compartir', `${esc(nombre)} ya no puede ver tu pantalla.`];
  }
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

async function pedirAyudaMovil() {
  if (busy || !usuario) return;
  setBusy(true);
  try {
    await api('/solicitudes/pedir-ayuda/', json({ usuario_id: usuario.id }));
    setBusy(false);
    viewIdle('¡Avisamos a tu familia! Enseguida se comunicarán contigo.');
  } catch (e) {
    setBusy(false);
    showInlineError('No pudimos enviar la alerta. ' + e.message);
  }
}

async function salir() {
  if (busy) return;
  setBusy(true);
  try {
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
    if (aceptar) {
      sesionActivaPrevia = s;
      viewActive({ ...s, estado: 'activa' });
    } else {
      viewEnded('rechazada', s.familiar_nombre);
    }
  } catch (e) {
    setBusy(false);
    showInlineError('No se pudo guardar tu respuesta. ' + e.message + ' Inténtalo otra vez.');
  }
}

async function finalizar(s) {
  if (busy) return;
  setBusy(true);
  try {
    await api(`/sesiones/${s.sesion_id}/finalizar/?autor=adulto_mayor`, { method: 'PUT' });
    setBusy(false);
    sesionActivaPrevia = null;
    viewEnded('finalizada', s.familiar_nombre);
  } catch (e) {
    setBusy(false);
    showInlineError('No se pudo dejar de compartir. ' + e.message + ' Inténtalo otra vez.');
  }
}

function obtenerCoordenadas() {
  return new Promise(resolve => {
    if (!navigator.geolocation) {
      resolve({ latitud: -32.8895, longitud: -68.8458 });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ latitud: pos.coords.latitude, longitud: pos.coords.longitude }),
      () => resolve({ latitud: -32.8895, longitud: -68.8458 }),
      { enableHighAccuracy: true, timeout: 4000 }
    );
  });
}

async function responderUbicacion(u, aceptar) {
  if (busy) return;
  setBusy(true);
  try {
    let coords = { latitud: null, longitud: null };
    if (aceptar) coords = await obtenerCoordenadas();
    await api(`/ubicaciones/${u.ubicacion_id}/responder/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aceptar, ...coords })
    });
    setBusy(false);
    viewEnded(aceptar ? 'ubicacion_ok' : 'ubicacion_no', u.familiar_nombre);
  } catch (e) {
    setBusy(false);
    showInlineError('No pudimos enviar tu respuesta. ' + e.message);
  }
}

async function refresh() {
  if (!usuario || busy || pausePolling) return;
  try {
    const dataSesiones = await api(`/sesiones/pendientes/${usuario.id}`);
    let dataUbicaciones = [];
    try {
      dataUbicaciones = await api(`/ubicaciones/pendientes/${usuario.id}`);
    } catch (e) {}

    if (!usuario || busy || pausePolling) return;
    sesiones = dataSesiones || [];
    ubicaciones = dataUbicaciones || [];

    const activa = sesiones.find(s => s.estado === 'activa');
    const pendiente = sesiones.find(s => s.estado === 'pendiente_consentimiento');
    const ubiPendiente = ubicaciones[0];

    if (!activa && sesionActivaPrevia) {
      const nombreFam = sesionActivaPrevia.familiar_nombre;
      sesionActivaPrevia = null;
      viewEnded('cortada_familiar', nombreFam);
      return;
    }

    if (activa) {
      sesionActivaPrevia = activa;
      viewActive(activa);
    } else if (pendiente) {
      viewConsent(pendiente);
    } else if (ubiPendiente) {
      viewLocationConsent(ubiPendiente);
    } else if (!current.startsWith('idle')) {
      viewIdle();
    }
  } catch (e) {
    viewError(e.message);
  }
}

function applyContrast(alto) {
  document.documentElement.dataset.contrast = alto ? 'high' : 'normal';
  if ($hc) $hc.setAttribute('aria-checked', String(alto));
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = alto ? '#000000' : '#F4EEE3';
}
applyContrast(document.documentElement.dataset.contrast === 'high');

if ($hc) {
  $hc.onclick = () => {
    const alto = $hc.getAttribute('aria-checked') !== 'true';
    applyContrast(alto);
    store('contraste', alto ? 'alto' : 'normal');
  };
}

matchMedia('(prefers-contrast: more)').addEventListener('change', e => {
  if (!store('contraste')) applyContrast(e.matches);
});

const optsBtn = document.getElementById('optsBtn');
if (optsBtn && $opts) {
  optsBtn.onclick = () => {
    cargarHistorialMovil();
    $opts.showModal();
  };
}

const optsClose = document.getElementById('optsClose');
if (optsClose && $opts) optsClose.onclick = () => $opts.close();

if ($opts) {
  $opts.addEventListener('click', e => {
    if (e.target !== $opts) return;
    const r = $opts.getBoundingClientRect();
    if (e.clientY < r.top || e.clientY > r.bottom || e.clientX < r.left || e.clientX > r.right) $opts.close();
  });
}

const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn && $opts) {
  logoutBtn.onclick = () => { $opts.close(); viewLogoutConfirm(); };
}

if (params.get('demo')) {
  const demoBox = document.getElementById('demo');
  const demoBtn = document.getElementById('demoBtn');
  if (demoBox) demoBox.hidden = false;
  if (demoBtn) {
    demoBtn.onclick = async () => {
      const msg = document.getElementById('demoMsg');
      try {
        const vinculo_id = parseInt(document.getElementById('demoVinculo').value, 10);
        const r = await api('/sesiones/solicitar/', json({ vinculo_id }));
        if (msg) msg.textContent = 'Solicitud #' + r.sesion_id + ' enviada.';
        refresh();
      } catch (e) {
        if (msg) msg.textContent = 'Error: ' + e.message;
      }
    };
  }
}

async function init() {
  renderAccount();
  const adultoParam = params.get('adulto');
  if (adultoParam) {
    params.delete('adulto');
    history.replaceState(null, '', location.pathname + (params.toString() ? '?' + params : '') + location.hash);
    try {
      const u = await api(`/usuarios/${parseInt(adultoParam, 10)}`);
      if (u.rol === 'adulto_mayor') saveUser(u);
    } catch (e) {}
  }
  if (usuario) startPolling();
  else viewLogin();
}

init();