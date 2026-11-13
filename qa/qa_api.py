"""Corre los casos de API del informe (Sprint 1 + Sprint 2) contra el servidor local y reporta cada resultado."""
import json
import sys
import time
import urllib.request as u
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
A = "http://127.0.0.1:8000"
stamp = str(int(time.time()))
results = []

def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = u.Request(A + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        r = u.urlopen(req)
        return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw

def check(case, desc, got, expected):
    ok = got == expected
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {case} {desc} -> {got!r}" + ("" if ok else f" (esperado {expected!r})"))

# --- Usuarios e Ingreso ------------------------------------------------------
fam_mail, ad_mail = f"fam{stamp}@test.com", f"ad{stamp}@test.com"
s, fam = call("POST", "/usuarios/", {"nombre": "Lucía QA", "email": fam_mail, "rol": "familiar"})
check("API-01", "registrar familiar", s, 200)
s, ad = call("POST", "/usuarios/", {"nombre": "Rosa QA", "email": ad_mail, "rol": "adulto_mayor"})
check("API-02", "registrar adulto mayor", s, 200)
s, _ = call("POST", "/usuarios/", {"nombre": "Otra", "email": ad_mail, "rol": "familiar"})
check("API-03", "email repetido", s, 400)
s, d = call("GET", f"/usuarios/{ad['id']}")
check("API-04", "obtener usuario", (s, d["email"]), (200, ad_mail))
s, _ = call("GET", "/usuarios/999999")
check("API-05", "usuario inexistente", s, 404)
s, d = call("POST", "/usuarios/ingresar/", {"email": "  " + ad_mail.upper() + " "})
check("API-06", "ingresar ignora mayúsculas y espacios", (s, d.get("id")), (200, ad["id"]))
s, _ = call("POST", "/usuarios/ingresar/", {"email": "nadie@test.com"})
check("API-07", "ingresar con correo desconocido", s, 404)

# --- Vínculos QR (HU-01 + correcciones D-05 y D-06) --------------------------
s, d = call("POST", "/vinculos/generar-qr/", {"familiar_id": fam["id"], "adulto_id": ad["id"]})
vinculo = d.get("vinculo_id")
check("API-08", "vínculo con QR y vinculo_id (D-05)", (s, bool(d.get("qr_imagen_base64")), bool(vinculo)), (200, True, True))
s, d_dup = call("POST", "/vinculos/generar-qr/", {"familiar_id": fam["id"], "adulto_id": ad["id"]})
check("API-33", "reutiliza el mismo vínculo si el par ya existe (D-06)", (s, d_dup.get("vinculo_id")), (200, vinculo))
s, _ = call("POST", "/vinculos/generar-qr/", {"familiar_id": ad["id"], "adulto_id": fam["id"]})
check("API-09", "vínculo con roles invertidos", s, 400)

# --- Alertas de Ayuda y Notificaciones Push (HU-02 + SCRUM-49) ---------------
s, d_ayuda = call("POST", "/solicitudes/pedir-ayuda/", {"usuario_id": ad["id"]})
solicitud_id = d_ayuda.get("solicitud_id")
check("API-10", "pedir ayuda como adulto mayor", s, 200)
s, _ = call("POST", "/solicitudes/pedir-ayuda/", {"usuario_id": fam["id"]})
check("API-11", "pedir ayuda como familiar", s, 400)
s, pend_ayuda = call("GET", "/solicitudes/pendientes/")
check("API-36", "listar alertas pendientes para notificación Push (SCRUM-49)", (s, any(x["solicitud_id"] == solicitud_id and x["adulto_nombre"] == "Rosa QA" for x in pend_ayuda)), (200, True))
s, d_at = call("PUT", f"/solicitudes/{solicitud_id}/atender/")
check("API-37", "atender alerta de ayuda (SCRUM-49)", (s, d_at.get("estado")), (200, "atendida"))

# --- Sesiones Remotas (HU-03 + correcciones D-02 y D-03) ---------------------
s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo})
primera = d["sesion_id"]
s_dup, _ = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo})
check("API-34", "bloquea pedidos duplicados pendientes en el mismo vínculo (D-03)", s_dup, 409)

s, lista = call("GET", f"/sesiones/pendientes/{ad['id']}")
check("API-12", "pendientes muestra nombre del familiar", (s, lista[0]["familiar_nombre"]), (200, "Lucía QA"))
s, d = call("PUT", f"/sesiones/{primera}/responder/?aceptar=true")
check("API-13", "aceptar solicitud", (s, d.get("estado")), (200, "activa"))
s, _ = call("PUT", f"/sesiones/{primera}/responder/?aceptar=false")
check("API-14", "responder dos veces", s, 409)
s, d = call("PUT", f"/sesiones/{primera}/finalizar/?autor=familiar")
check("API-15", "finalizar sesión activa", (s, d.get("estado")), (200, "finalizada"))
s, _ = call("PUT", f"/sesiones/{primera}/finalizar/")
check("API-16", "finalizar dos veces", s, 409)
s, _ = call("PUT", "/sesiones/999999/finalizar/")
check("API-17", "finalizar sesión inexistente", s, 404)
s, _ = call("POST", "/sesiones/solicitar/", {"vinculo_id": 999999})
check("API-18", "solicitar con vínculo inexistente", s, 404)

s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); rech = d["sesion_id"]
s, d = call("PUT", f"/sesiones/{rech}/responder/?aceptar=false")
check("API-19", "rechazar solicitud", (s, d.get("estado")), (200, "rechazada"))
s, lista = call("GET", f"/sesiones/pendientes/{ad['id']}")
check("API-20", "rechazada ya no figura en pendientes", lista, [])

# --- Salida de la cuenta y bloqueo con cuenta cerrada (D-02) -----------------
s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); act = d["sesion_id"]
call("PUT", f"/sesiones/{act}/responder/?aceptar=true")
s, d = call("POST", f"/usuarios/{ad['id']}/salir/")
check("API-21", "salir cierra las sesiones abiertas", (s, d.get("sesiones_cerradas")), (200, 1))
check("API-22", "la activa queda finalizada", call("GET", f"/sesiones/{act}")[1]["estado"], "finalizada")

s_closed, _ = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo})
check("API-35", "impide solicitar pantalla si el adulto salió de su cuenta (D-02)", s_closed, 409)

call("POST", "/usuarios/ingresar/", {"email": ad_mail})
s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); pen = d["sesion_id"]
call("POST", f"/usuarios/{ad['id']}/salir/")
check("API-23", "la pendiente queda rechazada al salir", call("GET", f"/sesiones/{pen}")[1]["estado"], "rechazada")
s, _ = call("POST", "/usuarios/999999/salir/")
check("API-24", "salir con usuario inexistente", s, 404)

call("POST", "/usuarios/ingresar/", {"email": ad_mail})
s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); f_act = d["sesion_id"]
call("PUT", f"/sesiones/{f_act}/responder/?aceptar=true")
s, d = call("POST", f"/usuarios/{fam['id']}/salir/")
check("API-25", "salir como familiar también corta", (s, d.get("sesiones_cerradas")), (200, 1))

# --- Historial y Auditoría de Sesiones (HU-04 / HU-08) -----------------------
s, hist = call("GET", f"/sesiones/historial/?adulto_id={ad['id']}")
item_hist = next((x for x in hist if x["sesion_id"] == primera), None)
check("API-38", "historial registra duración, fechas y quién cerró (HU-08)", (s, bool(item_hist), item_hist.get("cerrada_por"), isinstance(item_hist.get("duracion_segundos"), int)), (200, True, "familiar", True))

# --- Geolocalización bajo Demanda (HU-06 / SCRUM-35) -------------------------
s, d_geo = call("POST", "/ubicaciones/solicitar/", {"vinculo_id": vinculo})
geo_id = d_geo.get("ubicacion_id")
s_pend, lista_geo = call("GET", f"/ubicaciones/pendientes/{ad['id']}")
check("API-39", "solicitar ubicación y listar pendiente (HU-06)", (s, s_pend, any(x["ubicacion_id"] == geo_id for x in lista_geo)), (200, 200, True))
s_gdup, _ = call("POST", "/ubicaciones/solicitar/", {"vinculo_id": vinculo})
check("API-40", "bloquea solicitud de ubicación duplicada pendiente", s_gdup, 409)
s, d_gresp = call("PUT", f"/ubicaciones/{geo_id}/responder/", {"aceptar": True, "latitud": -32.8895, "longitud": -68.8458})
check("API-41", "aceptar ubicación guarda coordenadas (HU-06)", (s, d_gresp.get("estado"), d_gresp.get("latitud")), (200, "compartida", -32.8895))

s, d_geo2 = call("POST", "/ubicaciones/solicitar/", {"vinculo_id": vinculo})
geo_id2 = d_geo2.get("ubicacion_id")
s, d_grech = call("PUT", f"/ubicaciones/{geo_id2}/responder/", {"aceptar": False})
check("API-42", "rechazar ubicación no comparte coordenadas (HU-06)", (s, d_grech.get("estado"), d_grech.get("latitud")), (200, "rechazada", None))

# --- Archivos estáticos y seguridad ------------------------------------------
for path, case in [("/mobile/", "API-26"), ("/panel", "API-27"), ("/panel.css", "API-28")]:
    check(case, f"sirve {path}", u.urlopen(A + path).status, 200)
for path, case in [("/assist.db", "API-29"), ("/main.py", "API-30"), ("/mobile/../main.py", "API-31"), ("/mobile/%2e%2e/main.py", "API-32")]:
    try:
        code = u.urlopen(A + path).status
    except urllib.error.HTTPError as e:
        code = e.code
    check(case, f"no expone {path}", code, 404)

print(f"\n{sum(results)}/{len(results)} OK")