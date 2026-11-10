# -*- coding: utf-8 -*-
"""
motor.py - Motor matemático del Solucionador de Sistemas Lineales (3x3 y 4x4)

Resuelve A·x = b por cuatro métodos, mostrando cada operación paso a paso:
    1. Eliminación de Gauss (escalonada + sustitución hacia atrás)
    2. Gauss-Jordan (forma escalonada reducida)
    3. Regla de Cramer (determinantes)
    4. Matriz inversa (Gauss-Jordan sobre [A | I])

Todo el cálculo usa fracciones exactas (fractions.Fraction), por lo que no hay
errores de redondeo: 1/3 se mantiene como 1/3.
"""
from fractions import Fraction
from dataclasses import dataclass, field
import time


class ErrorSistema(Exception):
    """Error de validación de las entradas del usuario."""


# ----------------------------------------------------------------------------
# Utilidades de formato
# ----------------------------------------------------------------------------
def fmt(x):
    """Fracción -> texto ('5' o '7/3')."""
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def fmt_val(x):
    """Valor con aproximación decimal si no es entero."""
    x = Fraction(x)
    if x.denominator == 1:
        return fmt(x)
    return f"{fmt(x)} ≈ {float(x):.4f}"


def fp(x):
    """Número entre paréntesis si es negativo."""
    s = fmt(x)
    return f"({s})" if s.startswith("-") else s


def fq(x):
    """Número entre paréntesis si es negativo o fraccionario (para cocientes)."""
    t = fmt(x)
    return f"({t})" if (t.startswith("-") or "/" in t) else t


def mat_str(M, sep=None, indent="    "):
    """Matriz alineada. sep = índice de columna antes del cual se dibuja '|'."""
    strs = [[fmt(v) for v in fila] for fila in M]
    nc = len(M[0])
    w = [max(len(strs[i][j]) for i in range(len(M))) for j in range(nc)]
    out = []
    for fila in strs:
        celdas = []
        for j, s in enumerate(fila):
            if sep is not None and j == sep:
                celdas.append("|")
            celdas.append(s.rjust(w[j]))
        out.append(indent + "[ " + " ".join(celdas) + " ]")
    return "\n".join(out)


def _termino(coef, nombre):
    coef = Fraction(coef)
    if coef == 1:
        return nombre
    if coef == -1:
        return "-" + nombre
    return f"{fmt(coef)}·{nombre}"


def ecuacion_str(coefs, rhs, primera_var=0):
    """'2·x1 + 3·x2 = 7' omitiendo términos nulos."""
    partes = []
    for j, c in enumerate(coefs):
        if c == 0:
            continue
        t = _termino(abs(c), f"x{primera_var + j + 1}")
        if not partes:
            partes.append(("-" if c < 0 else "") + t)
        else:
            partes.append(("- " if c < 0 else "+ ") + t)
    lado = " ".join(partes) if partes else "0"
    return f"{lado} = {fmt(rhs)}"


def describir_sistema(A, b):
    return "\n".join(f"  Ec.{i + 1}:  {ecuacion_str(A[i], b[i])}" for i in range(len(A)))


# ----------------------------------------------------------------------------
# Expresiones lineales en parámetros (para soluciones con infinitas soluciones)
# ----------------------------------------------------------------------------
class Lin:
    """c + sum(coef_k * t_k)."""
    __slots__ = ("c", "t")

    def __init__(self, c=0, t=None):
        self.c = Fraction(c)
        self.t = {k: Fraction(v) for k, v in (t or {}).items() if v != 0}

    def __add__(self, o):
        o = o if isinstance(o, Lin) else Lin(o)
        t = dict(self.t)
        for k, v in o.t.items():
            t[k] = t.get(k, 0) + v
        return Lin(self.c + o.c, t)

    def __sub__(self, o):
        o = o if isinstance(o, Lin) else Lin(o)
        return self + o * -1

    def __mul__(self, k):
        k = Fraction(k)
        return Lin(self.c * k, {a: v * k for a, v in self.t.items()})

    __rmul__ = __mul__

    def __truediv__(self, k):
        return self * (1 / Fraction(k))

    def __eq__(self, o):
        o = o if isinstance(o, Lin) else Lin(o)
        return self.c == o.c and self.t == o.t

    def __str__(self):
        partes = []
        if self.c != 0 or not self.t:
            partes.append(fmt(self.c))
        for k in sorted(self.t):
            v = self.t[k]
            mag = abs(v)
            term = ("" if mag == 1 else fmt(mag) + "·") + f"t{k}"
            if not partes:
                partes.append(("-" if v < 0 else "") + term)
            else:
                partes.append(("- " if v < 0 else "+ ") + term)
        return " ".join(partes)

    def valor(self):
        return self.c


# ----------------------------------------------------------------------------
# Resultado y contador de operaciones
# ----------------------------------------------------------------------------
class Ops:
    """Cuenta multiplicaciones y divisiones (medida clásica de costo)."""

    def __init__(self):
        self.n = 0


@dataclass
class Resultado:
    metodo: str
    tipo: str                 # 'unico' | 'infinito' | 'inconsistente' | 'no_aplicable'
    x: list = field(default_factory=list)      # lista de Lin
    pasos: list = field(default_factory=list)
    ops: int = 0
    detalle: str = ""         # tipo real del sistema cuando 'no_aplicable'
    tiempo_ms: float = 0.0

    def texto(self):
        return "\n".join(self.pasos)

    def solucion_str(self):
        if self.tipo == "unico":
            return ", ".join(f"x{i + 1}={fmt(v.c)}" for i, v in enumerate(self.x))
        if self.tipo == "infinito":
            return "; ".join(f"x{i + 1}={v}" for i, v in enumerate(self.x))
        return "—"


TIPOS = {
    "unico": "compatible determinado (solución única)",
    "infinito": "compatible indeterminado (infinitas soluciones)",
    "inconsistente": "incompatible (sin solución)",
}


# ----------------------------------------------------------------------------
# Validación de entradas
# ----------------------------------------------------------------------------
def _a_fraccion(t):
    return Fraction(str(t).strip().replace(",", "."))


def validar_entradas(filas):
    """
    filas: lista de n listas con n+1 textos/números (n coeficientes + término
    independiente). Devuelve (A, b) con fracciones o lanza ErrorSistema.
    """
    n = len(filas)
    if n not in (3, 4):
        raise ErrorSistema(f"Dimensión inválida: el sistema debe ser 3x3 o 4x4 (recibido {n} ecuaciones).")
    errores = []
    A, b = [], []
    for i, fila in enumerate(filas):
        if len(fila) != n + 1:
            raise ErrorSistema(f"Dimensión inválida: la fila {i + 1} tiene {len(fila)} valores y se esperaban {n + 1}.")
        vals = []
        for j, t in enumerate(fila):
            donde = f"fila {i + 1}, columna {j + 1}" if j < n else f"fila {i + 1}, término independiente"
            if str(t).strip() == "":
                errores.append(f"Campo vacío en {donde}.")
                continue
            try:
                vals.append(_a_fraccion(t))
            except (ValueError, ZeroDivisionError):
                errores.append(f"Valor no numérico en {donde}: '{t}'. Use enteros, decimales (2.5) o fracciones (1/3).")
        if len(vals) == n + 1:
            A.append(vals[:n])
            b.append(vals[n])
    if errores:
        raise ErrorSistema("\n".join(errores))
    return A, b


# ----------------------------------------------------------------------------
# Diagnóstico silencioso (rangos, determinante)
# ----------------------------------------------------------------------------
def _rango(M, ncoef):
    M = [list(f) for f in M]
    fila = 0
    for col in range(ncoef):
        p = next((i for i in range(fila, len(M)) if M[i][col] != 0), None)
        if p is None:
            continue
        M[fila], M[p] = M[p], M[fila]
        for i in range(fila + 1, len(M)):
            f = M[i][col] / M[fila][col]
            M[i] = [M[i][j] - f * M[fila][j] for j in range(len(M[0]))]
        fila += 1
        if fila == len(M):
            break
    return fila


def _det_silencioso(A):
    M = [list(f) for f in A]
    n = len(M)
    det = Fraction(1)
    for c in range(n):
        p = next((i for i in range(c, n) if M[i][c] != 0), None)
        if p is None:
            return Fraction(0)
        if p != c:
            M[c], M[p] = M[p], M[c]
            det = -det
        det *= M[c][c]
        for i in range(c + 1, n):
            f = M[i][c] / M[c][c]
            M[i] = [M[i][j] - f * M[c][j] for j in range(n)]
    return det


def diagnostico(A, b):
    """Devuelve (rango A, rango [A|b], det A, tipo)."""
    n = len(A)
    aug = [list(A[i]) + [b[i]] for i in range(n)]
    rA, rAb = _rango(A, n), _rango(aug, n + 1)
    det = _det_silencioso(A)
    if rA < rAb:
        tipo = "inconsistente"
    elif rA == n:
        tipo = "unico"
    else:
        tipo = "infinito"
    return rA, rAb, det, tipo


def verificacion_previa(A, b):
    """Texto para que el usuario revise el sistema ANTES de resolverlo."""
    n = len(A)
    rA, rAb, det, tipo = diagnostico(A, b)
    L = [f"SISTEMA CONSTRUIDO ({n}x{n})", describir_sistema(A, b), "",
         "Matriz de coeficientes A y vector b:", mat_str([list(A[i]) + [b[i]] for i in range(n)], sep=n), "",
         "Verificación previa:",
         f"  • det(A) = {fmt(det)}",
         f"  • rango(A) = {rA},  rango([A|b]) = {rAb},  incógnitas = {n}",
         f"  • Clasificación: sistema {TIPOS[tipo]}."]
    if det == 0:
        L.append("  • Como det(A) = 0, la regla de Cramer y la matriz inversa NO son aplicables; use Gauss o Gauss-Jordan.")
    return "\n".join(L)


# ----------------------------------------------------------------------------
# Verificación de la solución por sustitución
# ----------------------------------------------------------------------------
def _verificar(A, b, x):
    n = len(A)
    lineas = ["", "VERIFICACIÓN (sustitución en el sistema original):"]
    ok_total = True
    unico = all(not v.t for v in x)
    for i in range(n):
        lhs = Lin(0)
        for j in range(n):
            lhs = lhs + x[j] * A[i][j]
        ok = (lhs == Lin(b[i]))
        ok_total &= ok
        if unico:
            expr = " + ".join(f"{fp(A[i][j])}·{fp(x[j].c)}" for j in range(n))
            lineas.append(f"  Ec.{i + 1}: {expr} = {fmt(lhs.c)}   (b = {fmt(b[i])})  {'✓' if ok else '✗'}")
        else:
            lineas.append(f"  Ec.{i + 1}: al sustituir la solución general se obtiene {lhs}   (b = {fmt(b[i])})  {'✓' if ok else '✗'}")
    lineas.append("  ➜ La solución satisface todas las ecuaciones." if ok_total else "  ➜ ¡La solución NO satisface el sistema!")
    return lineas, ok_total


# ----------------------------------------------------------------------------
# Núcleo: operaciones elementales por filas
# ----------------------------------------------------------------------------
def _op_str(i, k, f):
    if f > 0:
        coef = "" if f == 1 else f"{fmt(f)}·"
        return f"F{i + 1} ← F{i + 1} − {coef}F{k + 1}"
    coef = "" if f == -1 else f"{fmt(-f)}·"
    return f"F{i + 1} ← F{i + 1} + {coef}F{k + 1}"


def _reducir(M, ncoef, ops, pasos, jordan, sep):
    """
    Reduce M (in situ). jordan=False -> forma escalonada (Gauss).
    jordan=True -> forma escalonada reducida (Gauss-Jordan).
    Devuelve (pivotes[(fila,col)], intercambios, producto_de_pivotes).
    """
    nf, ncols = len(M), len(M[0])
    fila, pivotes, swaps, prod = 0, [], 0, Fraction(1)
    for col in range(ncoef):
        if fila >= nf:
            break
        p = next((i for i in range(fila, nf) if M[i][col] != 0), None)
        if p is None:
            pasos.append(f"Columna {col + 1}: no hay pivote (todos los elementos disponibles son 0) → x{col + 1} quedará como variable libre.")
            pasos.append("")
            continue
        if p != fila:
            M[fila], M[p] = M[p], M[fila]
            swaps += 1
            pasos.append(f"Intercambio  F{fila + 1} ↔ F{p + 1}   (el elemento en la posición ({fila + 1},{col + 1}) era 0)")
            pasos.append(mat_str(M, sep))
            pasos.append("")
        piv = M[fila][col]
        prod *= piv
        if jordan and piv != 1:
            M[fila] = [v / piv for v in M[fila]]
            ops.n += ncols - col
            pasos.append(f"F{fila + 1} ← F{fila + 1} / {fq(piv)}      (pivote de la columna {col + 1} → 1)")
            pasos.append(mat_str(M, sep))
            pasos.append("")
        filas_obj = range(nf) if jordan else range(fila + 1, nf)
        for i in filas_obj:
            if i == fila or M[i][col] == 0:
                continue
            f = M[i][col] / M[fila][col]
            ops.n += 1 + (ncols - col - 1)
            pasos.append(f"{_op_str(i, fila, f)}      [m = {fq(M[i][col])}/{fq(M[fila][col])} = {fmt(f)}]")
            M[i] = [M[i][j] - f * M[fila][j] for j in range(ncols)]
            pasos.append(mat_str(M, sep))
            pasos.append("")
        pivotes.append((fila, col))
        fila += 1
    return pivotes, swaps, prod


def _contradiccion(M, n, rango):
    for i in range(rango, len(M)):
        if all(M[i][j] == 0 for j in range(n)) and M[i][n] != 0:
            return i
    return None


def _no_aplicable(res, A, b, motivo):
    rA, rAb, det, tipo = diagnostico(A, b)
    res.tipo = "no_aplicable"
    res.detalle = tipo
    res.pasos += ["", motivo,
                  f"Diagnóstico: rango(A) = {rA}, rango([A|b]) = {rAb} → el sistema es {TIPOS[tipo]}.",
                  "Recomendación: resolver con Gauss o Gauss-Jordan, que sí clasifican y resuelven este caso."]
    return res


def _cierre_eliminacion(res, A, b, M, piv, jordan, ops):
    """Clasifica, resuelve (sustitución/lectura) y verifica. Rellena res."""
    n = len(A)
    rango = len(piv)
    pasos = res.pasos
    pasos += ["Matriz final:", mat_str(M, n), ""]
    fila_mala = _contradiccion(M, n, rango)
    if fila_mala is not None:
        res.tipo = "inconsistente"
        pasos += [f"ANÁLISIS: la fila {fila_mala + 1} queda  0·x1 + … + 0·xn = {fmt(M[fila_mala][n])}  con {fmt(M[fila_mala][n])} ≠ 0,",
                  "lo cual es una contradicción.", "",
                  f"RESULTADO: el sistema es {TIPOS['inconsistente']}. No existe ningún vector x que cumpla todas las ecuaciones.",
                  f"(rango(A) = {rango}, rango([A|b]) = {rango + 1})"]
        res.ops = ops.n
        return res
    if rango == n:
        res.tipo = "unico"
        if jordan:
            x = [M[i][n] for i in range(n)]
            pasos.append("ANÁLISIS: la parte izquierda es la identidad → la solución se lee directamente de la última columna.")
        else:
            pasos.append(f"ANÁLISIS: rango(A) = rango([A|b]) = {n} = número de incógnitas → solución única.")
            pasos += ["", "FASE 2 · Sustitución hacia atrás", ""]
            x = [None] * n
            for r in range(n - 1, -1, -1):
                pasos.append(f"De la fila {r + 1}:  {ecuacion_str(M[r][:n], M[r][n])}")
                s = sum((M[r][j] * x[j] for j in range(r + 1, n)), Fraction(0))
                x[r] = (M[r][n] - s) / M[r][r]
                ops.n += (n - 1 - r) + 1
                if r == n - 1:
                    pasos.append(f"   x{n} = {fq(M[r][n])} / {fq(M[r][r])} = {fmt_val(x[r])}")
                else:
                    terms = " - ".join(f"{fp(M[r][j])}·{fp(x[j])}" for j in range(r + 1, n) if M[r][j] != 0)
                    num = f"{fmt(M[r][n])} - {terms}" if terms else fmt(M[r][n])
                    pasos.append(f"   x{r + 1} = ({num}) / {fq(M[r][r])} = {fmt_val(x[r])}")
        res.x = [Lin(v) for v in x]
        pasos += ["", "RESULTADO: solución única", "  " + "\n  ".join(f"x{i + 1} = {fmt_val(v)}" for i, v in enumerate(x))]
    else:
        res.tipo = "infinito"
        pcols = [c for _, c in piv]
        libres = [c for c in range(n) if c not in pcols]
        pasos.append(f"ANÁLISIS: rango(A) = rango([A|b]) = {rango} < {n} incógnitas → infinitas soluciones "
                     f"({n - rango} grado(s) de libertad).")
        pasos += ["", ("Sustitución hacia atrás con parámetros" if not jordan else "Lectura de la forma reducida con parámetros"), ""]
        x = [None] * n
        for k, c in enumerate(libres, 1):
            x[c] = Lin(0, {k: 1})
            pasos.append(f"   x{c + 1} = t{k}   (variable libre)")
        for r, c in reversed(piv):
            expr = Lin(M[r][n])
            for j in range(c + 1, n):
                if M[r][j] != 0:
                    expr = expr - x[j] * M[r][j]
            x[c] = expr / M[r][c]
            ops.n += 1
            pasos.append(f"   x{c + 1} = {x[c]}")
        res.x = x
        pasos += ["", "RESULTADO: solución general (t1, t2… ∈ ℝ)", "  " + "\n  ".join(f"x{i + 1} = {v}" for i, v in enumerate(x))]
    lineas, _ = _verificar(A, b, res.x)
    pasos += lineas
    res.ops = ops.n
    return res


# ----------------------------------------------------------------------------
# Método 1: Gauss
# ----------------------------------------------------------------------------
def resolver_gauss(A, b):
    t0 = time.perf_counter()
    n, ops = len(A), Ops()
    M = [list(A[i]) + [b[i]] for i in range(n)]
    res = Resultado("Gauss", "unico")
    res.pasos += ["MÉTODO DE GAUSS  (eliminación hacia adelante + sustitución hacia atrás)", "",
                  "Sistema:", describir_sistema(A, b), "",
                  "Matriz aumentada [A | b]:", mat_str(M, n), "",
                  "FASE 1 · Eliminación hacia adelante (se busca una matriz escalonada)", ""]
    piv, _, _ = _reducir(M, n, ops, res.pasos, False, n)
    _cierre_eliminacion(res, A, b, M, piv, False, ops)
    res.tiempo_ms = (time.perf_counter() - t0) * 1000
    return res


# ----------------------------------------------------------------------------
# Método 2: Gauss-Jordan
# ----------------------------------------------------------------------------
def resolver_gauss_jordan(A, b):
    t0 = time.perf_counter()
    n, ops = len(A), Ops()
    M = [list(A[i]) + [b[i]] for i in range(n)]
    res = Resultado("Gauss-Jordan", "unico")
    res.pasos += ["MÉTODO DE GAUSS-JORDAN  (reducción a la forma escalonada reducida)", "",
                  "Sistema:", describir_sistema(A, b), "",
                  "Matriz aumentada [A | b]:", mat_str(M, n), "",
                  "Reducción: cada pivote se lleva a 1 y se anulan los elementos de su columna (arriba y abajo).", ""]
    piv, _, _ = _reducir(M, n, ops, res.pasos, True, n)
    _cierre_eliminacion(res, A, b, M, piv, True, ops)
    res.tiempo_ms = (time.perf_counter() - t0) * 1000
    return res


# ----------------------------------------------------------------------------
# Determinantes con pasos (Sarrus 3x3, cofactores para 4x4)
# ----------------------------------------------------------------------------
def det_pasos(M, ops):
    n = len(M)
    if n == 1:
        return M[0][0], [f"det = {fmt(M[0][0])}"]
    if n == 2:
        a, b, c, d = M[0][0], M[0][1], M[1][0], M[1][1]
        v = a * d - b * c
        ops.n += 2
        return v, [f"det = {fp(a)}·{fp(d)} - {fp(b)}·{fp(c)} = {fmt(a * d)} - ({fmt(b * c)}) = {fmt(v)}"]
    if n == 3:
        a, b, c = M[0]
        d, e, f = M[1]
        g, h, i = M[2]
        t = [a * e * i, b * f * g, c * d * h, c * e * g, a * f * h, b * d * i]
        ops.n += 12
        v = t[0] + t[1] + t[2] - t[3] - t[4] - t[5]
        l1 = (f"Sarrus: {fp(a)}·{fp(e)}·{fp(i)} + {fp(b)}·{fp(f)}·{fp(g)} + {fp(c)}·{fp(d)}·{fp(h)} "
              f"- {fp(c)}·{fp(e)}·{fp(g)} - {fp(a)}·{fp(f)}·{fp(h)} - {fp(b)}·{fp(d)}·{fp(i)}")
        l2 = (f"     = {fp(t[0])} + {fp(t[1])} + {fp(t[2])} - {fp(t[3])} - {fp(t[4])} - {fp(t[5])} = {fmt(v)}")
        return v, [l1, l2]
    lineas = [f"Desarrollo por cofactores a lo largo de la fila 1 (determinante {n}x{n}):"]
    total, partes = Fraction(0), []
    for j in range(n):
        a = M[0][j]
        signo = 1 if j % 2 == 0 else -1
        if a == 0:
            lineas.append(f"  a1{j + 1} = 0 → el término vale 0 (no hace falta calcular el menor M1{j + 1}).")
            continue
        minor = [fila[:j] + fila[j + 1:] for fila in M[1:]]
        mv, ml = det_pasos(minor, ops)
        lineas.append(f"  Menor M1{j + 1} (se elimina la fila 1 y la columna {j + 1}):")
        lineas += mat_str(minor, indent="        ").split("\n")
        lineas += ["        " + s for s in ml]
        ops.n += 1
        total += signo * a * mv
        partes.append(f"{'+' if signo > 0 else '-'} {fp(a)}·{fp(mv)}")
    expr = " ".join(partes)
    if expr.startswith("+ "):
        expr = expr[2:]
    lineas.append(f"  det = {expr} = {fmt(total)}")
    return total, lineas


# ----------------------------------------------------------------------------
# Método 3: Regla de Cramer
# ----------------------------------------------------------------------------
def resolver_cramer(A, b):
    t0 = time.perf_counter()
    n, ops = len(A), Ops()
    res = Resultado("Cramer", "unico")
    P = res.pasos
    P += ["REGLA DE CRAMER   x_i = det(A_i) / det(A)", "",
          "donde A_i es la matriz A con la columna i reemplazada por el vector b.", "",
          "Sistema:", describir_sistema(A, b), "",
          "Matriz de coeficientes A:", mat_str(A), "",
          "Paso 1 · Cálculo de det(A)"]
    dA, ls = det_pasos(A, ops)
    P += ["  " + s for s in ls]
    P.append(f"  ➜ det(A) = {fmt(dA)}")
    if dA == 0:
        _no_aplicable(res, A, b, "det(A) = 0 → la regla de Cramer NO es aplicable (exige det(A) ≠ 0).")
        res.ops = ops.n
        res.tiempo_ms = (time.perf_counter() - t0) * 1000
        return res
    P += ["", "Paso 2 · Determinantes de las matrices A_i y cociente", ""]
    x = []
    for i in range(n):
        Ai = [list(fila) for fila in A]
        for r in range(n):
            Ai[r][i] = b[r]
        P += [f"A_{i + 1} (columna {i + 1} reemplazada por b):", mat_str(Ai)]
        di, ls = det_pasos(Ai, ops)
        P += ["  " + s for s in ls]
        xi = di / dA
        ops.n += 1
        P.append(f"  x{i + 1} = det(A_{i + 1}) / det(A) = {fmt(di)} / {fmt(dA)} = {fmt_val(xi)}")
        P.append("")
        x.append(xi)
    res.x = [Lin(v) for v in x]
    P += ["RESULTADO: solución única", "  " + "\n  ".join(f"x{i + 1} = {fmt_val(v)}" for i, v in enumerate(x))]
    lineas, _ = _verificar(A, b, res.x)
    P += lineas
    res.ops = ops.n
    res.tiempo_ms = (time.perf_counter() - t0) * 1000
    return res


# ----------------------------------------------------------------------------
# Método 4: Matriz inversa
# ----------------------------------------------------------------------------
def resolver_inversa(A, b):
    t0 = time.perf_counter()
    n, ops = len(A), Ops()
    res = Resultado("Matriz inversa", "unico")
    P = res.pasos
    I = [[Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    M = [list(A[i]) + I[i] for i in range(n)]
    P += ["MÉTODO DE LA MATRIZ INVERSA   x = A⁻¹ · b", "",
          "Sistema:", describir_sistema(A, b), "",
          "Paso 1 · Calcular A⁻¹ aplicando Gauss-Jordan a la matriz ampliada [A | I]", "",
          "Matriz [A | I]:", mat_str(M, n), ""]
    piv, swaps, prod = _reducir(M, n, ops, P, True, n)
    if len(piv) < n:
        P += ["Matriz final:", mat_str(M, n)]
        _no_aplicable(res, A, b, "No se pudo obtener la identidad en el lado izquierdo → A es singular (det(A) = 0) y NO tiene inversa.")
        res.ops = ops.n
        res.tiempo_ms = (time.perf_counter() - t0) * 1000
        return res
    Ainv = [fila[n:] for fila in M]
    det = (-1) ** swaps * prod
    P += ["Matriz final [I | A⁻¹]:", mat_str(M, n), "",
          "A⁻¹ =", mat_str(Ainv), "",
          f"(det(A) = {fmt(det)} ≠ 0, producto de los pivotes con signo por intercambios)", ""]
    prod_ok = all(sum(A[i][k] * Ainv[k][j] for k in range(n)) == (1 if i == j else 0) for i in range(n) for j in range(n))
    P.append("Comprobación A·A⁻¹ = I:  " + ("✓ se obtiene la identidad" if prod_ok else "✗ falla"))
    P += ["", "Paso 2 · Multiplicar x = A⁻¹ · b", ""]
    x = []
    for i in range(n):
        s = sum((Ainv[i][j] * b[j] for j in range(n)), Fraction(0))
        ops.n += n
        expr = " + ".join(f"{fp(Ainv[i][j])}·{fp(b[j])}" for j in range(n))
        P.append(f"  x{i + 1} = {expr} = {fmt_val(s)}")
        x.append(s)
    res.x = [Lin(v) for v in x]
    P += ["", "RESULTADO: solución única", "  " + "\n  ".join(f"x{i + 1} = {fmt_val(v)}" for i, v in enumerate(x))]
    lineas, _ = _verificar(A, b, res.x)
    P += lineas
    res.ops = ops.n
    res.tiempo_ms = (time.perf_counter() - t0) * 1000
    return res


METODOS = {
    "Gauss": resolver_gauss,
    "Gauss-Jordan": resolver_gauss_jordan,
    "Regla de Cramer": resolver_cramer,
    "Matriz inversa": resolver_inversa,
}


# ----------------------------------------------------------------------------
# Comparación de los cuatro métodos
# ----------------------------------------------------------------------------
def comparar(A, b):
    """Ejecuta los 4 métodos y devuelve (texto_comparativo, lista_resultados)."""
    n = len(A)
    resultados = [f(A, b) for f in METODOS.values()]
    rA, rAb, det, tipo = diagnostico(A, b)
    L = ["COMPARACIÓN DE LOS CUATRO MÉTODOS", "",
         f"Sistema {n}x{n}: {TIPOS[tipo]}   (det(A) = {fmt(det)})", ""]
    w = 17
    L.append("Método".ljust(w) + "Estado".ljust(16) + "× y ÷".ljust(8) + "Tiempo(ms)".ljust(12) + "Solución")
    L.append("-" * 100)
    for r in resultados:
        estado = "No aplica" if r.tipo == "no_aplicable" else {"unico": "Única", "infinito": "Infinitas", "inconsistente": "Sin solución"}[r.tipo]
        sol = "—" if r.tipo == "no_aplicable" else r.solucion_str()
        L.append(r.metodo.ljust(w) + estado.ljust(16) + str(r.ops).ljust(8) + f"{r.tiempo_ms:.3f}".ljust(12) + sol)
    aplicables = [r for r in resultados if r.tipo != "no_aplicable"]
    L.append("")
    firmas = {(r.tipo, r.solucion_str()) for r in aplicables}
    if len(firmas) == 1:
        L.append(f"✓ Los {len(aplicables)} métodos aplicables coinciden en el resultado (validación cruzada).")
    else:
        L.append("✗ Los métodos no coinciden: revise los datos.")
    L.append("")
    L.append("Análisis:")
    if tipo == "unico":
        L.append("  • Los cuatro métodos son aplicables. Gauss suele requerir menos operaciones; Cramer crece muy rápido con n")
        L.append("    (calcula n+1 determinantes) y la inversa calcula más de lo necesario si solo se busca x.")
    else:
        L.append("  • Cramer y Matriz inversa no aplican (det(A)=0); solo Gauss y Gauss-Jordan clasifican el sistema")
        L.append("    como incompatible o indeterminado y, en este último caso, entregan la solución general.")
    return "\n".join(L), resultados
