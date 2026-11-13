"""Corre los casos de API del informe contra el servidor local y reporta cada resultado."""
import json, sys, time, urllib.request as u, urllib.error
sys.stdout.reconfigure(encoding="utf-8")
A = "http://127.0.0.1:8000"
stamp = str(int(time.time()))
results = []

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = u.Request(A + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        r = u.urlopen(req)
        return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw

def check(case, desc, got, expected):
    ok = got == expected
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {case} {desc} -> {got!r}" + ("" if ok else f" (esperado {expected!r})"))

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

s, d = call("POST", "/vinculos/generar-qr/", {"familiar_id": fam["id"], "adulto_id": ad["id"]})
check("API-08", "vínculo con QR", (s, bool(d.get("qr_imagen_base64"))), (200, True))
s, _ = call("POST", "/vinculos/generar-qr/", {"familiar_id": ad["id"], "adulto_id": fam["id"]})
check("API-09", "vínculo con roles invertidos", s, 400)
s, _ = call("POST", "/solicitudes/pedir-ayuda/", {"usuario_id": ad["id"]})
check("API-10", "pedir ayuda como adulto mayor", s, 200)
s, _ = call("POST", "/solicitudes/pedir-ayuda/", {"usuario_id": fam["id"]})
check("API-11", "pedir ayuda como familiar", s, 400)

# El endpoint de QR no devuelve el id del vínculo: se obtiene al probar ids hasta dar con el del familiar.
vinculo = None
for i in range(1, 500):
    s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": i})
    if s != 200:
        break
    s2, lista = call("GET", f"/sesiones/pendientes/{ad['id']}")
    if any(x["sesion_id"] == d["sesion_id"] for x in lista):
        vinculo = i
        primera = d["sesion_id"]
        break
    call("PUT", f"/sesiones/{d['sesion_id']}/finalizar/")
assert vinculo, "no se encontró el vínculo"

s, lista = call("GET", f"/sesiones/pendientes/{ad['id']}")
check("API-12", "pendientes muestra nombre del familiar", (s, lista[0]["familiar_nombre"]), (200, "Lucía QA"))
s, d = call("PUT", f"/sesiones/{primera}/responder/?aceptar=true")
check("API-13", "aceptar solicitud", (s, d.get("estado")), (200, "activa"))
s, _ = call("PUT", f"/sesiones/{primera}/responder/?aceptar=false")
check("API-14", "responder dos veces", s, 409)
s, d = call("PUT", f"/sesiones/{primera}/finalizar/")
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

s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); act = d["sesion_id"]
call("PUT", f"/sesiones/{act}/responder/?aceptar=true")
s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); pen = d["sesion_id"]
s, d = call("POST", f"/usuarios/{ad['id']}/salir/")
check("API-21", "salir cierra las dos sesiones abiertas", (s, d.get("sesiones_cerradas")), (200, 2))
check("API-22", "la activa queda finalizada", call("GET", f"/sesiones/{act}")[1]["estado"], "finalizada")
check("API-23", "la pendiente queda rechazada", call("GET", f"/sesiones/{pen}")[1]["estado"], "rechazada")
s, _ = call("POST", "/usuarios/999999/salir/")
check("API-24", "salir con usuario inexistente", s, 404)

s, d = call("POST", "/sesiones/solicitar/", {"vinculo_id": vinculo}); f_act = d["sesion_id"]
call("PUT", f"/sesiones/{f_act}/responder/?aceptar=true")
s, d = call("POST", f"/usuarios/{fam['id']}/salir/")
check("API-25", "salir como familiar también corta", (s, d.get("sesiones_cerradas")), (200, 1))

for path, case in [("/mobile/", "API-26"), ("/panel", "API-27"), ("/panel.css", "API-28")]:
    check(case, f"sirve {path}", u.urlopen(A + path).status, 200)
for path, case in [("/assist.db", "API-29"), ("/main.py", "API-30"), ("/mobile/../main.py", "API-31"), ("/mobile/%2e%2e/main.py", "API-32")]:
    try:
        code = u.urlopen(A + path).status
    except urllib.error.HTTPError as e:
        code = e.code
    check(case, f"no expone {path}", code, 404)

print(f"\n{sum(results)}/{len(results)} OK")
