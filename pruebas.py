# -*- coding: utf-8 -*-
"""pruebas.py - Validación automática del motor (python pruebas.py)"""
import random
from fractions import Fraction
from motor import *

random.seed(2026)
def mat_por_vec(A, x): return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]

ok = fallos = 0
def check(cond, msg):
    global ok, fallos
    if cond: ok += 1
    else: fallos += 1; print("FALLO:", msg)

# 1) Sistemas aleatorios con solución conocida (3x3 y 4x4): los 4 métodos deben acertar
for n in (3, 4):
    for _ in range(300):
        A = [[Fraction(random.randint(-9, 9)) for _ in range(n)] for _ in range(n)]
        x = [Fraction(random.randint(-9, 9), random.choice([1, 1, 2, 3])) for _ in range(n)]
        b = mat_por_vec(A, x)
        _, _, det, tipo = diagnostico(A, b)
        if det != 0:
            for nombre, f in METODOS.items():
                r = f(A, b)
                check(r.tipo == "unico" and [v.c for v in r.x] == x, f"{nombre} {n}x{n} {A} {b}")
        else:
            for nombre in ("Gauss", "Gauss-Jordan"):
                r = METODOS[nombre](A, b)
                check(r.tipo in ("infinito",), f"{nombre} singular consistente {A}")
            for nombre in ("Regla de Cramer", "Matriz inversa"):
                check(METODOS[nombre](A, b).tipo == "no_aplicable", f"{nombre} debe no aplicar")

# 2) Infinitas soluciones e inconsistente
A = [[1, 1, 1], [2, 3, 1], [3, 4, 2]]
A = [[Fraction(v) for v in f] for f in A]
r = resolver_gauss(A, [Fraction(v) for v in (6, 14, 20)])
check(r.tipo == "infinito", "infinito Gauss")
r2 = resolver_gauss_jordan(A, [Fraction(v) for v in (6, 14, 20)])
check(r.solucion_str() == r2.solucion_str(), "misma solución general")
check(resolver_gauss(A, [Fraction(v) for v in (6, 14, 21)]).tipo == "inconsistente", "inconsistente")
check(resolver_gauss_jordan(A, [Fraction(v) for v in (6, 14, 21)]).tipo == "inconsistente", "inconsistente GJ")

# 3) Validación de entradas
for malo in ([[1, 2], [3, 4]], [[1, 2, 3, 4]] * 5):
    try: validar_entradas(malo); check(False, "dimensión inválida aceptada")
    except ErrorSistema: check(True, "")
try: validar_entradas([["1", "a", "3", "4"], ["", "2", "3", "4"], ["1", "2", "3", "4"]]); check(False, "texto aceptado")
except ErrorSistema as e: check("no numérico" in str(e) and "vacío" in str(e), "mensajes")
A, b = validar_entradas([["1/2", "0,5", "2", "1"], [1, 0, 0, 1], [0, 1, 0, 1]]); check(A[0][0] == Fraction(1, 2) and A[0][1] == Fraction(1, 2), "fracciones/decimales")

print(f"Pruebas OK: {ok}   Fallos: {fallos}")
