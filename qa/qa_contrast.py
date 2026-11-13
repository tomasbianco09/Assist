"""Calcula el contraste WCAG de los pares de color que usa la interfaz."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

def lum(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    vals = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in vals]
    return .2126 * r + .7152 * g + .0722 * b

def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)

N = dict(bg="#F4EEE3", surface="#FFFCF6", ink="#1C2B2D", ink2="#4D5B5C", primary="#245C43", pink="#FFFFFF",
         stop="#A8321F", wait="#9A5B0B", ok="#E3EEE6", err="#F8E4DE", alert="#B5470B", line="#D9CEBC")
H = dict(bg="#000000", ink="#FFFFFF", primary="#FFE600", pink="#000000", stop="#FFB4A6", alert="#FFB870", wait="#FFE600")

pairs = [
    ("Normal", "texto sobre fondo", N["ink"], N["bg"]),
    ("Normal", "texto secundario sobre fondo", N["ink2"], N["bg"]),
    ("Normal", "texto secundario sobre tarjeta", N["ink2"], N["surface"]),
    ("Normal", "botón principal", N["pink"], N["primary"]),
    ("Normal", "botón rojo", N["pink"], N["stop"]),
    ("Normal", "botón pedir ayuda (panel)", N["pink"], N["alert"]),
    ("Normal", "insignia 'Esperando' (panel)", N["wait"], N["bg"]),
    ("Normal", "texto en aviso verde", N["ink"], N["ok"]),
    ("Normal", "texto en aviso de error", N["ink"], N["err"]),
    ("Normal", "borde de tarjeta sobre fondo (no texto)", N["line"], N["bg"]),
    ("Alto", "texto sobre fondo", H["ink"], H["bg"]),
    ("Alto", "botón principal", H["pink"], H["primary"]),
    ("Alto", "botón rojo", H["pink"], H["stop"]),
    ("Alto", "botón pedir ayuda (panel)", H["pink"], H["alert"]),
    ("Alto", "acento amarillo sobre fondo", H["primary"], H["bg"]),
    ("Alto", "borde coral sobre fondo", H["stop"], H["bg"]),
]
for tema, nombre, fg, bg in pairs:
    print(f"{tema:7} {nombre:42} {fg} / {bg}  {ratio(fg, bg):5.2f}:1")
