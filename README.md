# Solucionador de Sistemas Lineales 3x3 y 4x4

Proyecto ABP de **Álgebra Lineal** – CECAR (periodo 2026-2). Equipo mixto de Ingeniería Industrial e Ingeniería de Sistemas.

Programa en Python que construye sistemas de ecuaciones lineales de 3x3 y 4x4 y los resuelve **paso a paso** por el método que el usuario elija:

1. Eliminación de Gauss
2. Gauss-Jordan
3. Regla de Cramer
4. Matriz inversa

Además verifica la solución por sustitución, compara los cuatro métodos (operaciones y tiempo) y clasifica el sistema: solución única, infinitas soluciones o sin solución.

## Características

- Aritmética exacta con fracciones (`fractions.Fraction`): sin errores de redondeo.
- Interfaz gráfica (Tkinter) y modo consola.
- Validación de entradas: dimensión, campos vacíos, texto no numérico; acepta enteros, decimales (`2.5` o `2,5`) y fracciones (`1/3`).
- Verificación previa del sistema: ecuaciones, det(A), rangos y clasificación esperada.
- Manejo de pivote cero (intercambio de filas) y de sistemas singulares (Cramer e inversa avisan que no aplican).
- Casos predefinidos: producción en planta de muebles (3x3, industrial), carga de un clúster de servidores (4x4, sistemas) y tres demostraciones (infinitas soluciones, inconsistente, pivote cero).
- Interpretación del resultado en el contexto del caso y exportación a `.txt` desde la interfaz.

## Página web (GitHub Pages)

El repositorio incluye `index.html`, una página con el resumen del proyecto, los casos, los métodos, los ejemplos de salida y una versión interactiva del programa que ejecuta `motor.py` en el navegador con Pyodide.

Para publicarla: en GitHub entra a **Settings → Pages**, elige **Deploy from a branch**, rama `main` y carpeta `/ (root)`. En unos minutos quedará en `https://TU_USUARIO.github.io/TU_REPO/`. Para verla en tu equipo (no abre con doble clic): `python -m http.server` y entra a http://localhost:8000.

Los enlaces del informe y las diapositivas apuntan a `docs/informe.pdf` y `docs/diapositivas.pdf`; exporta esos archivos y colócalos en la carpeta `docs/`.

## Requisitos

Python 3.8 o superior, sin dependencias externas. Tkinter viene incluido en Windows y macOS; en Linux: `sudo apt install python3-tk`.

## Uso

```bash
python programa.py             # interfaz gráfica
python programa.py --consola   # modo consola
python pruebas.py              # pruebas automáticas (debe terminar con "Fallos: 0")
```

## Estructura

| Archivo | Descripción |
|---|---|
| `motor.py` | Motor matemático: validación, los cuatro métodos, determinantes, diagnóstico, verificación y comparación |
| `programa.py` | Interfaz gráfica, modo consola y casos predefinidos |
| `pruebas.py` | Pruebas automáticas (sistemas aleatorios 3x3 y 4x4, casos especiales y validaciones) |
| `ejemplos/` | Salidas de ejemplo del programa |
| `index.html` | Página web del proyecto con el programa en línea (Pyodide) |
| `docs/` | Informe y diapositivas en PDF (los agrega el equipo) |

## Ejemplo (caso industrial, Gauss)

Sistema: `2x1 + 3x2 + 4x3 = 140`, `x1 + 2x2 + x3 = 65`, `3x1 + x2 + 2x3 = 80`

Resultado: x1 = 10 sillas, x2 = 20 mesas, x3 = 15 escritorios. La salida completa está en [`ejemplos/caso1_industrial_gauss.txt`](ejemplos/caso1_industrial_gauss.txt).

## Comparación de métodos (multiplicaciones y divisiones)

| Método | 3x3 | 4x4 | Aplica si det(A) = 0 |
|---|---|---|---|
| Gauss | 17 | 31 | Sí |
| Gauss-Jordan | 27 | 51 | Sí |
| Matriz inversa | 54 | 112 | No |
| Regla de Cramer | 51 | 212 | No |

## Autores

[Nombres de los integrantes] · Docente: Javier Andrés Castro Rodríguez
