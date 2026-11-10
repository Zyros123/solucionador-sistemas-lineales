# -*- coding: utf-8 -*-
"""
programa.py - Solucionador de Sistemas de Ecuaciones Lineales 3x3 y 4x4
Curso: Álgebra Lineal · CECAR · Proyecto ABP (equipo mixto Ing. Industrial + Ing. de Sistemas)

Uso:
    python programa.py             -> interfaz gráfica (Tkinter)
    python programa.py --consola   -> modo consola

El usuario construye o edita el sistema, lo verifica y elige el método
(Gauss, Gauss-Jordan, Regla de Cramer, Matriz inversa o comparar los cuatro).
"""
import sys
from fractions import Fraction
import motor
from motor import ErrorSistema, METODOS, fmt, fmt_val

# ----------------------------------------------------------------------------
# Casos predefinidos (el usuario puede editarlos después de cargarlos)
# ----------------------------------------------------------------------------
CASOS = {
    "1. Industrial · Producción en planta de muebles (3x3)": {
        "descripcion": ("Una planta fabrica sillas (x1), mesas (x2) y escritorios (x3). Cada unidad consume horas en tres "
                        "estaciones: corte, ensamblaje y acabado. Se desea saber cuántas unidades producir para usar "
                        "EXACTAMENTE las horas disponibles: 140 h de corte, 65 h de ensamblaje y 80 h de acabado."),
        "variables": [("Sillas", "unidades"), ("Mesas", "unidades"), ("Escritorios", "unidades")],
        "A": [[2, 3, 4], [1, 2, 1], [3, 1, 2]], "b": [140, 65, 80]},
    "2. Sistemas · Carga de un clúster de servidores (4x4)": {
        "descripcion": ("Un centro de datos procesa cuatro tipos de tarea: consultas SQL (x1), transacciones web (x2), "
                        "reportes batch (x3) y respaldos (x4), en lotes por hora. Cada lote consume CPU, RAM, E/S de disco "
                        "y red. Se busca la carga que agota exactamente la capacidad: CPU 28, RAM 55, disco 50, red 25."),
        "variables": [("Consultas SQL", "lotes/h"), ("Transacciones web", "lotes/h"),
                      ("Reportes batch", "lotes/h"), ("Respaldos", "lotes/h")],
        "A": [[2, 1, 1, 0], [1, 3, 2, 1], [0, 1, 4, 2], [1, 0, 1, 3]], "b": [28, 55, 50, 25]},
    "3. Demostración · Infinitas soluciones (3x3)": {
        "descripcion": "La tercera ecuación es la suma de las dos primeras: sistema compatible indeterminado (det A = 0).",
        "variables": [("x1", ""), ("x2", ""), ("x3", "")],
        "A": [[1, 1, 1], [2, 3, 1], [3, 4, 2]], "b": [6, 14, 20]},
    "4. Demostración · Sistema inconsistente (3x3)": {
        "descripcion": "Misma matriz que el caso 3 pero con b3 = 21: las ecuaciones se contradicen (sin solución).",
        "variables": [("x1", ""), ("x2", ""), ("x3", "")],
        "A": [[1, 1, 1], [2, 3, 1], [3, 4, 2]], "b": [6, 14, 21]},
    "5. Demostración · Pivoteo con pivote 0 (4x4)": {
        "descripcion": "El elemento a11 es 0: el método debe intercambiar filas para continuar.",
        "variables": [("x1", ""), ("x2", ""), ("x3", ""), ("x4", "")],
        "A": [[0, 2, 1, 1], [1, 1, 0, 2], [2, 0, 1, 1], [1, 1, 1, 0]], "b": [11, 11, 9, 6]},
}


def interpretar(caso, res):
    """Lectura de la solución en el contexto del caso cargado."""
    if caso is None:
        return ""
    L = ["", "INTERPRETACIÓN EN EL CONTEXTO DEL CASO", caso["descripcion"], ""]
    if res.tipo == "unico":
        for (nombre, unidad), v in zip(caso["variables"], res.x):
            L.append(f"  • {nombre}: {fmt_val(v.c)} {unidad}".rstrip())
        if any(v.c < 0 for v in res.x):
            L.append("  ⚠ Hay valores negativos: matemáticamente válidos, pero no factibles como cantidades físicas.")
        elif any(v.c.denominator != 1 for v in res.x) and caso["variables"][0][1] == "unidades":
            L.append("  ⚠ Hay valores fraccionarios: en producción se deberían redondear a unidades enteras.")
        else:
            L.append("  ➜ Solución factible: todas las cantidades son no negativas.")
    elif res.tipo == "infinito":
        L.append("  Existen infinitas combinaciones que satisfacen las restricciones; se necesita un criterio adicional")
        L.append("  (costo mínimo, utilidad máxima, etc.) para elegir una.")
    elif res.tipo == "inconsistente":
        L.append("  Las restricciones son contradictorias: no es posible cumplirlas todas a la vez; hay que revisar los datos del modelo.")
    return "\n".join(L)


def ejecutar(nombre_metodo, A, b, caso=None):
    """Devuelve el texto completo de la solución para el método elegido."""
    if nombre_metodo == "Comparar los 4 métodos":
        resumen, _ = motor.comparar(A, b)
        return resumen
    r = METODOS[nombre_metodo](A, b)
    return r.texto() + ("\n" + interpretar(caso, r) if r.tipo != "no_aplicable" else "")


# ----------------------------------------------------------------------------
# Modo consola
# ----------------------------------------------------------------------------
def _leer_sistema_consola():
    while True:
        t = input("Tamaño del sistema (3 o 4): ").strip()
        if t in ("3", "4"):
            n = int(t)
            break
        print("  ✗ Dimensión inválida: solo se admite 3x3 o 4x4.")
    print(f"Ingrese cada ecuación con {n + 1} números separados por espacio "
          f"({n} coeficientes y al final el término independiente). Acepta 2.5 o 1/3.")
    while True:
        filas = [input(f"  Ecuación {i + 1}: ").replace(",", ".").split() for i in range(n)]
        try:
            return motor.validar_entradas(filas)
        except ErrorSistema as e:
            print("  ✗ Datos inválidos:\n    " + str(e).replace("\n", "\n    ") + "\n  Vuelva a ingresar el sistema.")


def consola():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 70 + "\n SOLUCIONADOR DE SISTEMAS LINEALES 3x3 / 4x4 — Álgebra Lineal CECAR\n" + "=" * 70)
    while True:
        print("\n1) Cargar caso predefinido   2) Ingresar un sistema   3) Salir")
        op = input("Opción: ").strip()
        caso = None
        if op == "3":
            return
        if op == "1":
            nombres = list(CASOS)
            for i, k in enumerate(nombres, 1):
                print(f"  {i}) {k}")
            try:
                caso = CASOS[nombres[int(input("Caso: ")) - 1]]
            except (ValueError, IndexError):
                print("  ✗ Opción inválida.")
                continue
            A, b = motor.validar_entradas([f + [bb] for f, bb in zip(caso["A"], caso["b"])])
            print("\n" + caso["descripcion"])
        elif op == "2":
            A, b = _leer_sistema_consola()
        else:
            continue
        print("\n" + motor.verificacion_previa(A, b))
        nombres_m = list(METODOS) + ["Comparar los 4 métodos"]
        while True:
            print("\nMétodo de solución:")
            for i, m in enumerate(nombres_m, 1):
                print(f"  {i}) {m}")
            print("  6) Volver al menú principal")
            s = input("Opción: ").strip()
            if s == "6":
                break
            if s in ("1", "2", "3", "4", "5"):
                print("\n" + ejecutar(nombres_m[int(s) - 1], A, b, caso))
            else:
                print("  ✗ Opción inválida.")


# ----------------------------------------------------------------------------
# Interfaz gráfica (Tkinter)
# ----------------------------------------------------------------------------
def gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    class App:
        def __init__(self, root):
            self.root = root
            root.title("Solucionador de Sistemas Lineales 3x3 / 4x4 — Álgebra Lineal CECAR")
            root.geometry("980x720")
            self.entradas = []
            self.caso = None

            top = ttk.Frame(root, padding=8)
            top.pack(fill="x")
            ttk.Label(top, text="Tamaño:").grid(row=0, column=0, sticky="w")
            self.var_n = tk.StringVar(value="3")
            cb = ttk.Combobox(top, textvariable=self.var_n, values=["3", "4"], width=4, state="readonly")
            cb.grid(row=0, column=1, padx=(4, 16))
            cb.bind("<<ComboboxSelected>>", lambda e: self.construir_rejilla())
            ttk.Label(top, text="Caso predefinido:").grid(row=0, column=2, sticky="w")
            self.var_caso = tk.StringVar()
            self.cb_caso = ttk.Combobox(top, textvariable=self.var_caso, values=list(CASOS), width=52, state="readonly")
            self.cb_caso.grid(row=0, column=3, padx=4)
            ttk.Button(top, text="Cargar caso", command=self.cargar_caso).grid(row=0, column=4, padx=4)

            self.marco = ttk.LabelFrame(root, text="Sistema A·x = b  (escriba enteros, decimales o fracciones como 1/3)", padding=8)
            self.marco.pack(fill="x", padx=8, pady=4)
            self.lbl_caso = ttk.Label(root, text="", wraplength=940, foreground="#1a4d7a")
            self.lbl_caso.pack(fill="x", padx=10)

            bar = ttk.Frame(root, padding=8)
            bar.pack(fill="x")
            ttk.Label(bar, text="Método:").pack(side="left")
            self.var_m = tk.StringVar(value="Gauss")
            ttk.Combobox(bar, textvariable=self.var_m, values=list(METODOS) + ["Comparar los 4 métodos"],
                         width=24, state="readonly").pack(side="left", padx=6)
            ttk.Button(bar, text="Verificar sistema", command=self.verificar).pack(side="left", padx=4)
            ttk.Button(bar, text="Resolver paso a paso", command=self.resolver).pack(side="left", padx=4)
            ttk.Button(bar, text="Limpiar", command=self.limpiar).pack(side="left", padx=4)
            ttk.Button(bar, text="Guardar resultado (.txt)", command=self.guardar).pack(side="left", padx=4)

            cont = ttk.Frame(root)
            cont.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.txt = tk.Text(cont, wrap="none", font=("Courier New", 10))
            sy = ttk.Scrollbar(cont, orient="vertical", command=self.txt.yview)
            sx = ttk.Scrollbar(cont, orient="horizontal", command=self.txt.xview)
            self.txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
            sy.pack(side="right", fill="y")
            sx.pack(side="bottom", fill="x")
            self.txt.pack(side="left", fill="both", expand=True)
            self.construir_rejilla()

        def construir_rejilla(self):
            for w in self.marco.winfo_children():
                w.destroy()
            n = int(self.var_n.get())
            self.entradas = []
            for j in range(n):
                ttk.Label(self.marco, text=f"x{j + 1}").grid(row=0, column=j, padx=4)
            ttk.Label(self.marco, text="b").grid(row=0, column=n + 1, padx=4)
            for i in range(n):
                fila = []
                for j in range(n + 1):
                    e = ttk.Entry(self.marco, width=9, justify="center")
                    e.grid(row=i + 1, column=j if j < n else n + 1, padx=3, pady=2)
                    e.bind("<Key>", lambda ev: self._editado())
                    fila.append(e)
                ttk.Label(self.marco, text="=").grid(row=i + 1, column=n)
                self.entradas.append(fila)

        def _editado(self):
            self.caso = None
            self.lbl_caso.config(text="")

        def cargar_caso(self):
            nombre = self.var_caso.get()
            if not nombre:
                messagebox.showinfo("Caso", "Seleccione un caso de la lista.")
                return
            c = CASOS[nombre]
            self.var_n.set(str(len(c["A"])))
            self.construir_rejilla()
            for i, f in enumerate(c["A"]):
                for j, v in enumerate(f + [c["b"][i]]):
                    self.entradas[i][j].insert(0, str(v))
            self.caso = c
            self.lbl_caso.config(text=c["descripcion"])

        def leer(self):
            filas = [[e.get() for e in f] for f in self.entradas]
            try:
                return motor.validar_entradas(filas)
            except ErrorSistema as ex:
                messagebox.showerror("Datos inválidos", str(ex))
                return None

        def mostrar(self, texto):
            self.txt.delete("1.0", "end")
            self.txt.insert("1.0", texto)

        def verificar(self):
            d = self.leer()
            if d:
                self.mostrar(motor.verificacion_previa(*d))

        def resolver(self):
            d = self.leer()
            if d:
                self.mostrar(ejecutar(self.var_m.get(), d[0], d[1], self.caso))

        def limpiar(self):
            for f in self.entradas:
                for e in f:
                    e.delete(0, "end")
            self.txt.delete("1.0", "end")
            self._editado()

        def guardar(self):
            contenido = self.txt.get("1.0", "end").strip()
            if not contenido:
                messagebox.showinfo("Guardar", "No hay resultado para guardar.")
                return
            ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
            if ruta:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(contenido)

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    if "--consola" in sys.argv:
        consola()
    else:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print("Tkinter no está disponible; se usa el modo consola.")
            consola()
        else:
            gui()
