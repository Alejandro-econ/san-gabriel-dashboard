# Autor: Alejandro Soto Antezana
# Código de matrícula: 2024200531K
# Tema 55: Riesgo del proyecto: simulación de Monte Carlo sobre precio, demanda y tipo de cambio
# Fecha de extracción: se registra automáticamente en log_ejecucion.txt al ejecutar
"""
ANÁLISIS: PRUEBAS ESTADÍSTICAS + SIMULACIÓN DE MONTE CARLO DEL VAN DE SAN GABRIEL
-------------------------------------------------------------------------------
Genera TODAS las tablas y figuras del artículo en la carpeta salidas/:
  Parte A. Historia diaria (datos reales): descriptivos, ADF, cointegración, correlaciones,
           regresión con errores Newey-West y causalidad de Granger.
  Parte B. Modelo del proyecto: flujo de caja calibrado con el informe técnico oficial (SEC)
           y validación contra el VAN oficial.
  Parte C. Monte Carlo (10 000 simulaciones, semilla 531): bootstrap por bloques de los
           rendimientos diarios reales del oro, la demanda, el tipo de cambio y el riesgo país.
  Parte D. Regresión de sensibilidad del VAN (prueba F y estadísticos t) y contraste de hipótesis.
"""

# ------------------------------------------------------------------
# BLOQUE 1. Librerías, rutas y parámetros fijos
# ------------------------------------------------------------------
import warnings
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller, coint, grangercausalitytests

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos_procesados"
SALIDAS = RAIZ / "salidas"
SALIDAS.mkdir(exist_ok=True)
LOG = RAIZ / "log_ejecucion.txt"

CODIGO = "2024200531K"
SEMILLA = 531          # 4 últimos dígitos del código de matrícula 2024200531K -> 0531
N_SIM = 10_000         # número de simulaciones
LARGO_BLOQUE = 21      # 21 días hábiles = 1 mes (conserva la dependencia de corto plazo)
DIAS_ANIO = 252        # días hábiles por año (12 bloques de 21 días)
ALFA = 0.05            # nivel de significancia

warnings.filterwarnings("ignore", category=FutureWarning)  # avisos de versiones futuras de statsmodels
AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#6b6a64"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def registrar(mensaje):
    ahora = datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ahora} (Lima) | 04_analisis | {mensaje}"
    print(linea)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def _escapar(texto):
    """Convierte un texto en texto seguro para LaTeX (%, $, &, _, <, >, |)."""
    reemplazos = {"\\": r"\textbackslash{}", "%": r"\%", "$": r"\$", "&": r"\&", "_": r"\_",
                  "#": r"\#", "<": r"$<$", ">": r"$>$", "|": r"$|$", "~": r"$\sim$"}
    return "".join(reemplazos.get(c, c) for c in str(texto))


def _celda(valor, columna, decimales):
    """Da formato de revista a un número: separador de miles fino, signo menos tipográfico,
    valores p como '<0.001' y notación científica para cantidades muy pequeñas."""
    if isinstance(valor, str):
        return _escapar(valor)
    if valor is None or pd.isna(valor):
        return ""
    v = float(valor)
    if "Valor p" in columna:
        return r"$<$0.001" if v < 0.001 else f"{v:.3f}"
    if v.is_integer() and abs(v) >= 1:
        texto = f"{abs(v):,.0f}"
    elif 0 < abs(v) < 0.001:
        mant, expo = f"{abs(v):.2e}".split("e")
        return rf"${'-' if v < 0 else ''}{mant}\times10^{{{int(expo)}}}$"
    else:
        dec = min(decimales, 2) if abs(v) >= 100 else decimales
        texto = f"{abs(v):,.{dec}f}"
    texto = texto.replace(",", r"\,")
    return ("$-$" if v < 0 else "") + texto


def _encabezado(texto, numerica):
    """Parte en dos líneas los encabezados largos de columnas numéricas: 'P5 (VaR 95 %)'."""
    t = _escapar(texto)
    if numerica and " (" in texto and len(texto) > 10:
        a, b = t.split(" (", 1)
        return rf"\makecell[r]{{{a}\\({b}}}"
    return t


def guardar(tabla, nombre, decimales=4, indice=False):
    """Guarda cada tabla en CSV (para revisar) y en .tex con formato de revista (para el artículo).
    Las columnas de texto largas se ajustan al ancho de la página (tabularx); los números van a la derecha."""
    tabla.to_csv(SALIDAS / f"{nombre}.csv", index=indice, encoding="utf-8")
    t = tabla.reset_index() if indice else tabla
    numericas = [pd.api.types.is_numeric_dtype(t[c]) for c in t.columns]
    largas = [not n and t[c].astype(str).str.len().max() > 18 for c, n in zip(t.columns, numericas)]
    spec = "".join(r">{\raggedright\arraybackslash}X" if l else ("r" if n else "l")
                   for n, l in zip(numericas, largas))
    ancha = sum(numericas) >= 6   # muchas columnas numéricas: tabla de ancho natural, reducida si no cabe
    if ancha:
        spec = "".join(r">{\raggedright\arraybackslash}p{3.2cm}" if not n and i == 0 else ("r" if n else "l")
                       for i, n in enumerate(numericas))
        inicio = [r"\begin{adjustbox}{max width=\linewidth}", rf"\begin{{tabular}}{{{spec}}}"]
        fin = [r"\end{tabular}", r"\end{adjustbox}"]
    else:
        if not any(largas):    # sin columnas largas: la primera columna de texto toma el espacio sobrante
            spec = r">{\raggedright\arraybackslash}X" + spec[1:]
        inicio = [rf"\begin{{tabularx}}{{\linewidth}}{{{spec}}}"]
        fin = [r"\end{tabularx}"]
    lineas = inicio + [r"\toprule",
              " & ".join(_encabezado(c, n) for c, n in zip(t.columns, numericas)) + r" \\", r"\midrule"]
    for _, fila in t.iterrows():
        lineas.append(" & ".join(_celda(fila[c], str(c), decimales) for c in t.columns) + r" \\")
    lineas += [r"\bottomrule"] + fin
    (SALIDAS / f"{nombre}.tex").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    TABLAS[nombre] = tabla


TABLAS = {}

# ------------------------------------------------------------------
# BLOQUE 2. Carga de la base diaria y de los parámetros del proyecto
# ------------------------------------------------------------------
base = pd.read_csv(PROCESADOS / f"datos_procesados_{CODIGO}.csv", parse_dates=["fecha"])
VAR_DEMANDA = "gld_monto_musd"   # demanda de inversión: monto negociado diario del fondo de oro GLD
registrar(f"Base: {len(base)} días, de {base['fecha'].min():%Y-%m-%d} a {base['fecha'].max():%Y-%m-%d}; "
          f"demanda medida con '{VAR_DEMANDA}'")

par = pd.read_csv(PROCESADOS / f"parametros_proyecto_{CODIGO}.csv").set_index("parametro")["valor"]
if par.isna().any():
    raise SystemExit("Faltan parámetros del informe técnico (ver salida del script 02). No se inventan valores.")

# ------------------------------------------------------------------
# PARTE A. HISTORIA DIARIA (DATOS REALES)
# ------------------------------------------------------------------
# A.1 Estadística descriptiva de niveles y rendimientos
niveles = {"Precio del oro (US$/oz)": "precio_oro",
           "Demanda: monto negociado del fondo GLD (US$ mm)": VAR_DEMANDA,
           "Tipo de cambio (S/ por US$)": "tc",
           "Tasa EE. UU. 10 años (%)": "ust10",
           "EMBIG Perú (pbs)": "embig_peru"}
rend = {"Rend. log. oro": "r_oro", "Rend. log. demanda": "r_demanda",
        "Rend. log. tipo de cambio": "r_tc", "Cambio riesgo país (p.p.)": "d_riesgo_pais"}
filas = []
for etiqueta, col in {**niveles, **rend}.items():
    x = base[col].dropna()
    filas.append({"Variable": etiqueta, "N": len(x), "Media": x.mean(), "Desv. est.": x.std(),
                  "Mínimo": x.min(), "Mediana": x.median(), "Máximo": x.max(),
                  "Asimetría": stats.skew(x), "Curtosis": stats.kurtosis(x)})
guardar(pd.DataFrame(filas), "tabla1_descriptivos")

# A.2 Prueba de raíz unitaria ADF (H0: la serie tiene raíz unitaria = no estacionaria)
filas = []
for etiqueta, serie in [("ln oro", np.log(base["precio_oro"])), ("ln demanda", np.log(base[VAR_DEMANDA])),
                        ("ln tipo de cambio", np.log(base["tc"])), ("Riesgo país (%)", base["riesgo_pais_tasa"]),
                        ("Rend. oro", base["r_oro"]), ("Rend. demanda", base["r_demanda"]),
                        ("Rend. tipo de cambio", base["r_tc"]), ("Cambio riesgo país", base["d_riesgo_pais"])]:
    est, p, rezagos, nobs, crit, _ = adfuller(serie.dropna(), autolag="AIC")
    filas.append({"Serie": etiqueta, "Estadístico ADF": est, "Valor p": p, "Rezagos": rezagos, "N": nobs,
                  "Valor crítico 5 %": crit["5%"],
                  "Conclusión": "Estacionaria" if p < ALFA else "Raíz unitaria"})
guardar(pd.DataFrame(filas), "tabla2_adf")

# A.3 Cointegración de Engle-Granger entre ln oro y ln demanda (¿relación de largo plazo?)
est, p, crit = coint(np.log(base["precio_oro"]), np.log(base[VAR_DEMANDA]))
guardar(pd.DataFrame([{"Relación": "ln oro ~ ln demanda", "Estadístico EG": est, "Valor p": p,
                       "Valor crítico 5 %": crit[1],
                       "Conclusión": "Cointegradas" if p < ALFA else "No cointegradas"}]), "tabla3_cointegracion")
COINTEGRADAS = p < ALFA

# A.4 Correlaciones de Pearson entre rendimientos diarios (con valor p)
R = base[["r_oro", "r_demanda", "r_tc", "d_riesgo_pais"]].dropna()
filas = []
nombres = {"r_oro": "Oro", "r_demanda": "Demanda", "r_tc": "Tipo de cambio", "d_riesgo_pais": "Riesgo país"}
cols = list(nombres)
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):
        r, p = stats.pearsonr(R[cols[i]], R[cols[j]])
        filas.append({"Par": f"{nombres[cols[i]]} - {nombres[cols[j]]}", "Correlación": r, "Valor p": p, "N": len(R)})
guardar(pd.DataFrame(filas), "tabla4_correlaciones")
corr_oro_tc, p_oro_tc = stats.pearsonr(R["r_oro"], R["r_tc"])

# A.5 Regresión diaria: rendimiento del oro explicado por demanda, tipo de cambio y riesgo país
#     En primeras diferencias (rendimientos) y con errores Newey-West (HAC, 5 rezagos)
X = sm.add_constant(R[["r_demanda", "r_tc", "d_riesgo_pais"]])
mod_hist = sm.OLS(R["r_oro"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
dw = sm.stats.durbin_watson(mod_hist.resid)
tabla5 = pd.DataFrame({"Coeficiente": mod_hist.params, "Error est. (NW)": mod_hist.bse,
                       "Estadístico z": mod_hist.tvalues, "Valor p": mod_hist.pvalues})
tabla5.index = ["Constante", "Rend. demanda", "Rend. tipo de cambio", "Cambio riesgo país"]
tabla5.loc["Prueba F (NW)", ["Coeficiente", "Valor p"]] = [float(mod_hist.fvalue), float(mod_hist.f_pvalue)]
tabla5.loc["R cuadrado", "Coeficiente"] = mod_hist.rsquared
tabla5.loc["Durbin-Watson", "Coeficiente"] = dw
tabla5.loc["N", "Coeficiente"] = mod_hist.nobs
guardar(tabla5.reset_index().rename(columns={"index": "Variable"}), "tabla5_regresion_historica")

# A.5b Diagnóstico del modelo econométrico (supuestos de MCO). Cada prueba dice si el supuesto se cumple;
#      si no se cumple, se explica cómo se corrige (por eso se usan errores Newey-West).
from statsmodels.stats.diagnostic import het_breuschpagan, het_arch, acorr_ljungbox, linear_reset
from statsmodels.stats.stattools import jarque_bera
from statsmodels.stats.outliers_influence import variance_inflation_factor

mod_mco = sm.OLS(R["r_oro"], X).fit()                       # mismo modelo, errores clásicos (para las pruebas)
residuos = mod_mco.resid
jb, jb_p, asim_res, curt_res = jarque_bera(residuos)
bp, bp_p, _, _ = het_breuschpagan(residuos, X)
arch, arch_p, _, _ = het_arch(residuos, nlags=5)
lb = acorr_ljungbox(residuos, lags=[10], return_df=True)
reset = linear_reset(mod_mco, power=2, use_f=True)
vifs = {n: variance_inflation_factor(X.values, i) for i, n in enumerate(X.columns) if n != "const"}
nombres_x = {"r_demanda": "Rend. demanda", "r_tc": "Rend. tipo de cambio", "d_riesgo_pais": "Cambio riesgo país"}


def fila_diag(prueba, supuesto, est, p, ok, si_falla):
    return {"Prueba": prueba, "Supuesto que revisa": supuesto, "Estadístico": est, "Valor p": p,
            "Resultado": "Se cumple" if ok else f"No se cumple: {si_falla}"}


tabla12 = pd.DataFrame([
    fila_diag("Jarque-Bera", "Residuos con distribución normal", jb, jb_p, jb_p >= ALFA,
              "colas pesadas (se usa bootstrap, no la normal)"),
    fila_diag("Breusch-Pagan", "Varianza constante del error", bp, bp_p, bp_p >= ALFA,
              "heterocedasticidad (errores Newey-West)"),
    fila_diag("ARCH-LM (5 rezagos)", "Volatilidad sin rachas", arch, arch_p, arch_p >= ALFA,
              "rachas de volatilidad (errores Newey-West y bloques de 21 días)"),
    fila_diag("Ljung-Box Q(10)", "Residuos sin autocorrelación", float(lb["lb_stat"].iloc[0]),
              float(lb["lb_pvalue"].iloc[0]), float(lb["lb_pvalue"].iloc[0]) >= ALFA, "autocorrelación (errores Newey-West)"),
    fila_diag("RESET de Ramsey", "Forma funcional lineal correcta", float(reset.fvalue), float(reset.pvalue),
              float(reset.pvalue) >= ALFA, "posible no linealidad"),
    {"Prueba": "Durbin-Watson", "Supuesto que revisa": "Autocorrelación de primer orden", "Estadístico": dw,
     "Valor p": np.nan, "Resultado": "Se cumple (cercano a 2)" if 1.5 < dw < 2.5 else "No se cumple"},
] + [{"Prueba": f"VIF: {nombres_x[n]}", "Supuesto que revisa": "Sin multicolinealidad", "Estadístico": v,
      "Valor p": np.nan, "Resultado": "Se cumple (VIF < 10)" if v < 10 else "No se cumple"} for n, v in vifs.items()])
guardar(tabla12, "tabla12_diagnostico_modelo", decimales=3)

# A.5c Robustez del modelo: misma ecuación en submuestras (¿los signos se mantienen?)
atipico = base.loc[R.index, [c for c in base.columns if c.startswith("atipico_")]].sum(axis=1) > 0
anio_R = base.loc[R.index, "fecha"].dt.year
muestras = {"Muestra completa": R.index == R.index,
            "Sin días atípicos": ~atipico.to_numpy(),
            "2004-2015": (anio_R <= 2015).to_numpy(),
            "2016-2026": (anio_R >= 2016).to_numpy()}
filas = []
for etiqueta, m in muestras.items():
    Rm = R[m]
    res = sm.OLS(Rm["r_oro"], sm.add_constant(Rm[["r_demanda", "r_tc", "d_riesgo_pais"]])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5})
    for v in ["r_demanda", "r_tc", "d_riesgo_pais"]:
        filas.append({"Muestra": etiqueta, "Variable": nombres_x[v], "Coeficiente": res.params[v],
                      "Error est. (NW)": res.bse[v], "Valor p": res.pvalues[v], "R2": res.rsquared, "N": int(res.nobs)})
tabla13 = pd.DataFrame(filas)
guardar(tabla13, "tabla13_robustez_modelo", decimales=4)

# A.6 Causalidad de Granger (5 rezagos): ¿la demanda anticipa al oro? ¿y al revés?
filas = []
for causa, efecto in [("r_demanda", "r_oro"), ("r_oro", "r_demanda")]:
    try:   # statsmodels >= 0.15 ya no usa el argumento verbose
        res_g = grangercausalitytests(R[[efecto, causa]], maxlag=5)
    except TypeError:
        res_g = grangercausalitytests(R[[efecto, causa]], maxlag=5, verbose=False)
    g = res_g[5][0]["ssr_ftest"]
    filas.append({"H0": f"{nombres[causa]} NO causa en sentido de Granger a {nombres[efecto]}",
                  "Estadístico F": g[0], "Valor p": g[1], "gl": f"({int(g[2])}, {int(g[3])})",
                  "Decisión": "Se rechaza H0" if g[1] < ALFA else "No se rechaza H0"})
guardar(pd.DataFrame(filas), "tabla6_granger")

# ------------------------------------------------------------------
# PARTE B. MODELO DEL PROYECTO CALIBRADO CON EL INFORME TÉCNICO (SEC)
# ------------------------------------------------------------------
Q_TOTAL = par["oro_pagable_koz"] * 1_000                  # onzas pagables en toda la vida de la mina
N_ANIOS = int(round(par["vida_mina_anios"]))              # años de producción (14.2 -> 14)
Q_ANIO = Q_TOTAL / N_ANIOS                                # perfil uniforme (supuesto declarado)
I0 = par["inversion_inicial_musd"] * 1e6                  # inversión pendiente en el año 0
CIERRE = par["costo_cierre_musd"] * 1e6                   # costo de cierre, al final
K0 = par["tasa_descuento_pct"] / 100                      # WACC usado por Buenaventura
P_TRS = par["precio_oro_trs_usd_oz"]
FC_ANTES = par["flujo_antes_impuestos_musd"] * 1e6
FC_DESP = par["flujo_despues_impuestos_musd"] * 1e6
# Costo unitario implícito: el que hace que el flujo antes de impuestos sea el oficial
C_UNIT = P_TRS - (FC_ANTES + I0 + CIERRE) / Q_TOTAL
# Tasa efectiva de impuestos sobre el flujo operativo (renta, regalías, IEM, participación)
TAU = 1 - (FC_DESP + I0 + CIERRE) / (FC_ANTES + I0 + CIERRE)


def calcular_van(precios, k, tc=None):
    """precios: matriz (simulaciones x años 1..N+1); k: tasa por simulación; tc: matriz (sim x años 0..N+1).
    Devuelve el VAN en US$ y, si se da el tipo de cambio, el VAN en soles."""
    t = np.arange(1, N_ANIOS + 1)
    margen = Q_ANIO * (precios[:, :N_ANIOS] - C_UNIT)
    flujo = margen - TAU * np.maximum(margen, 0)            # impuestos solo si hay ganancia
    desc = (1 + k[:, None]) ** t
    desc_cierre = (1 + k) ** (N_ANIOS + 1)
    van_usd = -I0 + (flujo / desc).sum(axis=1) - CIERRE / desc_cierre
    if tc is None:
        return van_usd, None
    van_pen = (-I0 * tc[:, 0] + (flujo * tc[:, 1:N_ANIOS + 1] / desc).sum(axis=1)
               - CIERRE * tc[:, N_ANIOS + 1] / desc_cierre)
    return van_usd, van_pen


van_base, _ = calcular_van(np.full((1, N_ANIOS + 1), P_TRS), np.array([K0]))

# Precio del oro de equilibrio: el precio constante que hace VAN = 0. Mientras el margen sea positivo,
# el VAN es una línea recta en el precio, así que basta evaluar dos precios y despejar.
_p1, _p2 = C_UNIT + 100, C_UNIT + 1000
_v1 = calcular_van(np.full((1, N_ANIOS + 1), _p1), np.array([K0]))[0][0]
_v2 = calcular_van(np.full((1, N_ANIOS + 1), _p2), np.array([K0]))[0][0]
P_EQUILIBRIO = _p1 - _v1 * (_p2 - _p1) / (_v2 - _v1)
P_MERCADO = base["precio_oro"].iloc[-1]
TC_MERCADO = base["tc"].iloc[-1]
FECHA_ULT = base["fecha"].iloc[-1].strftime("%Y-%m-%d")
tabla_val = pd.DataFrame([
    ("Oro pagable en la vida de la mina (koz)", par["oro_pagable_koz"], "TRS, Tabla 1-2"),
    ("Vida de la mina (años)", par["vida_mina_anios"], "TRS, sección 1.2"),
    ("Producción anual usada (koz/año)", Q_ANIO / 1000, "Cálculo: oro pagable / años"),
    ("Producción media anual según TRS (koz/año)", par["produccion_media_koz_anio"], "TRS, sección 1.2.2"),
    ("Inversión pendiente (US$ mm)", I0 / 1e6, "TRS, Tabla 1-2"),
    ("Costo de cierre (US$ mm)", CIERRE / 1e6, "TRS, sección 1.2.1.3"),
    ("Precio del oro del TRS (US$/oz)", P_TRS, "TRS, sección 1.2.2"),
    ("AISC del TRS (US$/oz)", par["aisc_usd_oz"], "TRS, sección 1.2.2"),
    ("Costo unitario implícito (US$/oz)", C_UNIT, "Cálculo con flujos del TRS"),
    ("Tasa efectiva de impuestos (%)", TAU * 100, "Cálculo con flujos del TRS"),
    ("Tasa de descuento WACC (%)", K0 * 100, "TRS, Tabla 1-2"),
    ("VAN después de impuestos oficial (US$ mm)", par["van_despues_impuestos_musd"], "TRS, Tabla 1-2"),
    ("VAN del modelo con precio TRS (US$ mm)", van_base[0] / 1e6, "Modelo propio"),
    ("Diferencia modelo vs. oficial (%)", (van_base[0] / 1e6 / par["van_despues_impuestos_musd"] - 1) * 100, "Validación"),
    ("Precio del oro de equilibrio, VAN = 0 (US$/oz)", P_EQUILIBRIO, "Cálculo con el modelo"),
    (f"Precio de mercado al {FECHA_ULT} (US$/oz)", P_MERCADO, "BCRP, serie PD04704XD"),
    ("Margen de seguridad del precio (%)", (1 - P_EQUILIBRIO / P_MERCADO) * 100, "Cálculo: 1 - equilibrio / mercado"),
], columns=["Concepto", "Valor", "Fuente"])
guardar(tabla_val, "tabla7_parametros_y_validacion", decimales=2)
registrar(f"Validación: VAN modelo {van_base[0]/1e6:,.1f} vs oficial {par['van_despues_impuestos_musd']:,.1f} US$ mm")

# ------------------------------------------------------------------
# PARTE C. MONTE CARLO: BOOTSTRAP POR BLOQUES DE LOS RENDIMIENTOS REALES
# ------------------------------------------------------------------
# Idea: para fabricar un "año futuro" se pegan 12 meses (bloques de 21 días) elegidos al azar
# de la historia real. Así se respeta la volatilidad, las colas gordas y la correlación
# que tuvieron juntas las 4 variables el MISMO día.
M = R[["r_oro", "r_demanda", "r_tc", "d_riesgo_pais"]].to_numpy()
# Escenario principal "sin tendencia" (martingala): se quita la media de cada rendimiento y, en las
# variables en logaritmos, también la mitad de su varianza, para que el precio ESPERADO futuro sea
# igual al de hoy (no se supone que el oro seguirá subiendo como en el pasado).
# La demanda (monto negociado) no es un precio: solo se le quita la media.
M_SIN_TENDENCIA = M - M.mean(axis=0)
for col in (0, 2):   # 0 = oro, 2 = tipo de cambio
    M_SIN_TENDENCIA[:, col] -= 0.5 * M[:, col].var()


def simular_bloques(matriz, anios, rng):
    """Devuelve un arreglo (N_SIM x anios x 4) con la suma anual de rendimientos diarios."""
    T = len(matriz)
    acum = np.vstack([np.zeros(matriz.shape[1]), np.cumsum(matriz, axis=0)])
    bloques_por_anio = DIAS_ANIO // LARGO_BLOQUE
    inicios = rng.integers(0, T - LARGO_BLOQUE, size=(N_SIM, anios, bloques_por_anio))
    sumas = acum[inicios + LARGO_BLOQUE] - acum[inicios]           # suma de cada bloque
    return sumas.sum(axis=2)


def escenario(nombre, matriz, p0, tc0, rng):
    anios = N_ANIOS + 1                                             # +1 para el año de cierre
    s = simular_bloques(matriz, anios, rng)
    precios = p0 * np.exp(np.cumsum(s[:, :, 0], axis=1))
    # Choque acumulado de demanda (en logaritmos, sin exponenciar): mide si en esa simulación
    # el monto negociado del fondo de oro terminó por encima (+) o por debajo (-) de lo normal
    demanda_idx = np.cumsum(s[:, :, 1], axis=1)
    tc = np.hstack([np.full((N_SIM, 1), tc0), tc0 * np.exp(np.cumsum(s[:, :, 2], axis=1))])
    k = np.maximum(K0 + s[:, 0, 3] / 100, 0.01)                     # WACC + cambio del riesgo país en 1 año
    van_usd, van_pen = calcular_van(precios, k, tc)
    return {"nombre": nombre, "precios": precios, "demanda": demanda_idx, "tc": tc, "k": k,
            "van_usd": van_usd / 1e6, "van_pen": van_pen / 1e6, "p0": p0, "tc0": tc0}


rng = np.random.default_rng(SEMILLA)
esc_B = escenario(f"B. Precio de mercado al {FECHA_ULT}", M_SIN_TENDENCIA, P_MERCADO, TC_MERCADO, rng)
esc_A = escenario("A. Precio del informe técnico", M_SIN_TENDENCIA, P_TRS, TC_MERCADO, rng)
esc_C = escenario("C. Estabilidad: B con tendencia histórica", M, P_MERCADO, TC_MERCADO, rng)
registrar(f"Monte Carlo: {N_SIM} simulaciones por escenario, semilla {SEMILLA}, "
          f"bloques de {LARGO_BLOQUE} días, P0 mercado = {P_MERCADO:,.2f} US$/oz, TC0 = {TC_MERCADO:.4f}")


def resumen(v):
    p5 = np.percentile(v, 5)
    return {"Media": v.mean(), "Desv. est.": v.std(ddof=1), "P5 (VaR 95 %)": p5,
            "Mediana": np.median(v), "P95": np.percentile(v, 95),
            "CVaR 95 %": v[v <= p5].mean(), "Prob. VAN < 0 (%)": (v < 0).mean() * 100}


filas = []
for e in [esc_A, esc_B, esc_C]:
    filas.append({"Escenario": e["nombre"], "Moneda": "US$ mm", **resumen(e["van_usd"])})
    filas.append({"Escenario": e["nombre"], "Moneda": "S/ mm", **resumen(e["van_pen"])})
guardar(pd.DataFrame(filas), "tabla8_distribucion_van", decimales=2)
pd.DataFrame({"van_usd_mm_A": esc_A["van_usd"], "van_usd_mm_B": esc_B["van_usd"], "van_pen_mm_B": esc_B["van_pen"],
              "van_usd_mm_C": esc_C["van_usd"], "wacc_B": esc_B["k"]}).to_csv(
    SALIDAS / "simulaciones_van.csv", index=False, float_format="%.4f")

# ------------------------------------------------------------------
# PARTE D. SENSIBILIDAD DEL VAN (PRUEBA F Y t) Y CONTRASTE DE HIPÓTESIS
# ------------------------------------------------------------------
# Cada simulación se resume en 4 "factores" y se regresiona el VAN en soles sobre ellos.
# Los factores se estandarizan (media 0, desv. 1): el coeficiente mide cuántos millones
# cambia el VAN cuando el factor sube 1 desviación estándar -> se pueden comparar entre sí.
fact = pd.DataFrame({
    "Precio del oro": np.log(esc_B["precios"][:, :N_ANIOS]).mean(axis=1),
    "Demanda": esc_B["demanda"][:, N_ANIOS - 1],
    "Tipo de cambio": np.log(esc_B["tc"][:, 1:]).mean(axis=1),
    "Riesgo país (WACC)": esc_B["k"],
})
Z = (fact - fact.mean()) / fact.std()
mod_sens = sm.OLS(esc_B["van_pen"], sm.add_constant(Z)).fit(cov_type="HC1")
tabla9 = pd.DataFrame({"Coef. estandarizado (S/ mm)": mod_sens.params, "Error est. (HC1)": mod_sens.bse,
                       "Estadístico t": mod_sens.tvalues, "Valor p": mod_sens.pvalues})
tabla9.loc["Prueba F", ["Coef. estandarizado (S/ mm)", "Valor p"]] = [float(mod_sens.fvalue), float(mod_sens.f_pvalue)]
tabla9.loc["R cuadrado", "Coef. estandarizado (S/ mm)"] = mod_sens.rsquared
tabla9.loc["N", "Coef. estandarizado (S/ mm)"] = mod_sens.nobs
guardar(tabla9.rename(index={"const": "Constante"}).reset_index().rename(columns={"index": "Factor"}),
        "tabla9_sensibilidad_van", decimales=3)

# Pruebas de las hipótesis
b = mod_sens.params.drop("const")
mayor = b.abs().idxmax()
van_trs = par["van_despues_impuestos_musd"]
t_media = stats.ttest_1samp(esc_B["van_usd"], van_trs, alternative="greater")
negativos = int((esc_B["van_usd"] < 0).sum())
binom = stats.binomtest(negativos, N_SIM, p=0.05, alternative="less")
coef_dem = mod_hist.params["r_demanda"]
p_dem = mod_hist.pvalues["r_demanda"]
p_corr_neg = p_oro_tc / 2 if corr_oro_tc < 0 else 1 - p_oro_tc / 2          # prueba de una cola
cv_usd = esc_B["van_usd"].std() / abs(esc_B["van_usd"].mean())
cv_pen = esc_B["van_pen"].std() / abs(esc_B["van_pen"].mean())

contraste = pd.DataFrame([
    {"Hipótesis": "HG: precio, demanda, TC y riesgo país explican conjuntamente el VAN",
     "Prueba": "F de la regresión de sensibilidad", "Estadístico": float(mod_sens.fvalue),
     "Valor p": float(mod_sens.f_pvalue), "Decisión": "Se rechaza H0" if mod_sens.f_pvalue < ALFA else "No se rechaza H0"},
    {"Hipótesis": "HE1: el precio del oro es el factor de mayor efecto sobre el VAN",
     "Prueba": f"t del coeficiente; mayor |coef.| = {mayor}", "Estadístico": float(mod_sens.tvalues["Precio del oro"]),
     "Valor p": float(mod_sens.pvalues["Precio del oro"]),
     "Decisión": "Se acepta H1" if (mayor == "Precio del oro" and mod_sens.pvalues["Precio del oro"] < ALFA) else "No se acepta H1"},
    {"Hipótesis": "HE2: la demanda de inversión en oro se asocia positivamente con su precio",
     "Prueba": "z (Newey-West) del coef. de demanda, regresión diaria", "Estadístico": float(mod_hist.tvalues["r_demanda"]),
     "Valor p": float(p_dem / 2 if coef_dem > 0 else 1 - p_dem / 2),
     "Decisión": "Se acepta H1" if (coef_dem > 0 and p_dem / 2 < ALFA) else "No se acepta H1"},
    {"Hipótesis": "HE3: el tipo de cambio se mueve en sentido contrario al oro (cobertura natural)",
     "Prueba": f"Correlación de Pearson (una cola); CV VAN S/ = {cv_pen:.3f} vs US$ = {cv_usd:.3f}",
     "Estadístico": corr_oro_tc, "Valor p": p_corr_neg,
     "Decisión": "Se acepta H1" if p_corr_neg < ALFA else "No se acepta H1"},
    {"Hipótesis": "HE4a: el VAN esperado a precios de mercado supera el VAN oficial",
     "Prueba": "t de una muestra (una cola)", "Estadístico": float(t_media.statistic),
     "Valor p": float(t_media.pvalue), "Decisión": "Se acepta H1" if t_media.pvalue < ALFA else "No se acepta H1"},
    {"Hipótesis": "HE4b: la probabilidad de VAN negativo es menor que 5 %",
     "Prueba": f"Binomial: {negativos} de {N_SIM} simulaciones con VAN < 0", "Estadístico": negativos / N_SIM,
     "Valor p": float(binom.pvalue), "Decisión": "Se acepta H1" if binom.pvalue < ALFA else "No se acepta H1"},
])
guardar(contraste, "tabla10_contraste_hipotesis", decimales=4)

# ------------------------------------------------------------------
# BLOQUE FIGURAS (estilo de revista: paneles con letra, colores validados para daltonismo,
# etiquetas directas, sin títulos dentro de la imagen; el título y la nota van en LaTeX, APA 7)
# Cada figura se guarda en PNG (300 dpi, para Word/Beamer) y en PDF vectorial (para LaTeX).
# ------------------------------------------------------------------
import logging
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, PercentFormatter
import matplotlib.dates as mdates

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
TINTA, TINTA2, REJILLA = "#1f1f1d", "#5f5e5a", "#e6e5e0"
AZUL, NARANJA, AQUA, AMARILLO, ROJO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948"
AZUL_CLARO, NARANJA_CLARO = "#cde2fb", "#fbd9c8"
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Lato", "Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 9.5, "axes.labelsize": 9.5, "axes.titlesize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA, "axes.linewidth": 0.7, "text.color": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "xtick.major.size": 3, "ytick.major.size": 3,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": REJILLA, "grid.linewidth": 0.6,
    "legend.frameon": False, "legend.fontsize": 8.5, "figure.dpi": 150,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
    "pdf.fonttype": 42, "axes.formatter.use_locale": False,
})
def num(x, dec=0, signo=False):
    """Número con separador de miles fino y signo menos tipográfico (estilo editorial)."""
    t = f"{x:+,.{dec}f}" if signo else f"{x:,.{dec}f}"
    return t.replace(",", "\u2009").replace("-", "\u2212")


miles = FuncFormatter(lambda x, _: num(x))   # 4 437 con separador fino


# Borra figuras de versiones anteriores del script que ya no se generan
(SALIDAS / "figura2_histograma_van.png").unlink(missing_ok=True)


def guardar_figura(fig, nombre):
    fig.savefig(SALIDAS / f"{nombre}.png")
    fig.savefig(SALIDAS / f"{nombre}.pdf")
    plt.close(fig)


def letra(ax, texto, titulo):
    """Letra del panel (a, b, ...) en negrita y subtítulo, alineados a la izquierda."""
    ax.text(0, 1.04, texto, transform=ax.transAxes, fontsize=10, fontweight="bold", color=TINTA, va="bottom")
    ax.text(0.045, 1.04, titulo, transform=ax.transAxes, fontsize=8, color=TINTA, va="bottom")


def nota_valor(ax, x, y, texto, color, dx=8, dy=0, ha="left"):
    ax.scatter([x], [y], s=16, color=color, zorder=5, edgecolor="white", linewidth=0.8)
    ax.annotate(texto, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8.5,
                color=TINTA, ha=ha, va="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85))


CRISIS = [("2008-09-15", "2009-03-31", "Crisis financiera\nglobal"), ("2020-03-01", "2020-06-30", "COVID-19")]

# ---- Utilidades de estilo "premium": relleno en degradado bajo una curva y chips de texto ----
from matplotlib.gridspec import GridSpec
from matplotlib.patches import PathPatch, FancyBboxPatch, Wedge
from matplotlib.colors import Normalize
import matplotlib.patheffects as pe
FONDO_PANEL = "#fbfaf7"
CONTORNO = [pe.withStroke(linewidth=2.6, foreground="white")]


def relleno_degradado(ax, x, y, cmap, norm, y0=0, alpha=1.0, zorder=2):
    """Pinta el área bajo la curva y(x) con un degradado de color que depende de x."""
    poly = ax.fill_between(x, y0, y, color="none", linewidth=0)
    trazo = PathPatch(poly.get_paths()[0], facecolor="none", edgecolor="none")
    ax.add_patch(trazo)
    img = ax.imshow(np.linspace(x.min(), x.max(), 600)[None, :], extent=[x.min(), x.max(), y0, y.max()],
                    aspect="auto", origin="lower", cmap=cmap, norm=norm, alpha=alpha, zorder=zorder)
    img.set_clip_path(trazo)
    return img


def chip(ax, x, y, texto, color, ha="right", transform=None, size=7.8):
    ax.text(x, y, texto, transform=transform or ax.transAxes, ha=ha, va="top", fontsize=size, color="white",
            fontweight="bold", bbox=dict(boxstyle="round,pad=0.32", facecolor=color, edgecolor="none"), zorder=9)


ROJO_Z, AMBAR_Z, VERDE_Z = "#d64541", "#f0a830", "#1f9e6e"


# ---- Figura 1: las cuatro variables diarias (paneles con su propia escala; nunca doble eje) ----
fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.8), sharex=True)
paneles = [("precio_oro", "a", "Precio del oro (US$ por onza) · BCRP", AZUL, False),
           (VAR_DEMANDA, "b", "Demanda: monto negociado GLD (US$ mm, log.) · Yahoo", AQUA, True),
           ("tc", "c", "Tipo de cambio (S/ por US$) · BCRP", NARANJA, False),
           ("riesgo_pais_tasa", "d", "Tasa EE. UU. 10 años + EMBIG Perú (%) · FRED, BCRP", ROJO, False)]
for i, (a, (col, l, tit, color, logy)) in enumerate(zip(ax.ravel(), paneles)):
    for ini, fin, etiqueta in CRISIS:
        a.axvspan(pd.Timestamp(ini), pd.Timestamp(fin), color="#f0efec", zorder=0)
        if i == 0:
            a.text(pd.Timestamp(ini), 1.0, " " + etiqueta, transform=a.get_xaxis_transform(),
                   fontsize=7.5, color=TINTA2, va="top", ha="left")
    serie = base.set_index("fecha")[col]
    if logy:
        a.plot(serie.index, serie, color=color, linewidth=0.35, alpha=0.35)
        a.plot(serie.index, serie.rolling(63).mean(), color=color, linewidth=1.3, label="Media móvil 3 meses")
        a.set_yscale("log")
        a.legend(loc="upper left", fontsize=8)
    else:
        piso_ = serie.min() - (serie.max() - serie.min()) * 0.06
        a.fill_between(serie.index, piso_, serie, color=color, alpha=0.16, linewidth=0, zorder=1)
        a.plot(serie.index, serie, color=color, linewidth=1.0, zorder=3)
        a.set_ylim(bottom=piso_)
        i_max = serie.values.argmax()
        a.scatter([serie.index[i_max]], [serie.iloc[i_max]], s=16, marker="^", color=TINTA, zorder=5)
        a.annotate(f"máx. {num(serie.iloc[i_max], 2 if serie.max() < 100 else 0)}", (serie.index[i_max], serie.iloc[i_max]),
                   xytext=(-8, -2), textcoords="offset points", ha="right", va="top", fontsize=7.5, color=TINTA,
                   path_effects=CONTORNO)
    a.set_facecolor(FONDO_PANEL)
    a.grid(axis="y", color="white", linewidth=0.9)
    nota_valor(a, serie.index[-1], serie.iloc[-1], num(serie.iloc[-1], 2), color, dx=-6, dy=(-18 if i == 0 else 10), ha="right")
    if not logy:
        a.yaxis.set_major_formatter(miles if serie.max() > 100 else FuncFormatter(lambda x, _: f"{x:.1f}"))
    letra(a, l, tit)
    a.xaxis.set_major_locator(mdates.YearLocator(4))
    a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout(h_pad=2.2, w_pad=2.0)
guardar_figura(fig, "figura1_series_diarias")

# ---- Figura 2: distribución del VAN simulado (degradado por zonas, caja de percentiles y chips) ----
ZONAS_VAN = {}
x_lo = min(np.percentile(esc_A["van_usd"], 0.2), -1_000)
x_hi = np.percentile(esc_B["van_usd"], 99.6)
xg = np.linspace(x_lo, x_hi, 1_400)
pos0, pos1 = (0 - x_lo) / (x_hi - x_lo), (van_trs - x_lo) / (x_hi - x_lo)
MAPA_VAN = LinearSegmentedColormap.from_list("van_zonas", [
    (0, "#8c1d1a"), (pos0 * 0.55, ROJO_Z), (pos0, "#f08a5d"), (pos1, AMBAR_Z),
    (min(pos1 + 0.06, 0.99), "#7cc49a"), (1, "#0f6b4a")])
norma_van = Normalize(x_lo, x_hi)
fig, ejes = plt.subplots(2, 1, figsize=(7.4, 5.2), sharex=True, gridspec_kw={"hspace": 0.38})
for a, e, nombre, letra_p, col in [(ejes[0], esc_A, f"Escenario A · el oro empieza en el precio del informe técnico (US$ {num(P_TRS)}/oz)", "a", NARANJA),
                                   (ejes[1], esc_B, f"Escenario B · el oro empieza en el precio de mercado del 31/08/2026 (US$ {num(P_MERCADO)}/oz)", "b", AZUL)]:
    v = e["van_usd"]
    dens = stats.gaussian_kde(v, bw_method=0.12)(xg)
    dens = dens / dens.max()
    a.set_facecolor(FONDO_PANEL)
    relleno_degradado(a, xg, dens, MAPA_VAN, norma_van, zorder=2)
    a.plot(xg, dens, color=TINTA, linewidth=1.1, zorder=3)
    # caja de percentiles debajo de la curva (P5-P95 fina, P25-P75 gruesa, mediana y media)
    yb = -0.13
    p5, p25, p50, p75, p95 = np.percentile(v, [5, 25, 50, 75, 95])
    a.plot([p5, p95], [yb, yb], color=TINTA2, linewidth=1.2, solid_capstyle="butt", zorder=4)
    a.plot([p25, p75], [yb, yb], color=TINTA, linewidth=6.5, solid_capstyle="butt", zorder=4)
    a.scatter([p50], [yb], s=26, color="white", edgecolor=TINTA, linewidth=1, zorder=5)
    a.scatter([v.mean()], [yb], s=40, marker="D", color=col, edgecolor="white", linewidth=0.8, zorder=6)
    for xv, t, ha_ in [(p5, f"P5 = VaR 95 %\n{num(p5)}", "left" if p5 > 0 else "right"), (p95, f"P95\n{num(p95)}", "center")]:
        a.text(xv, yb - 0.07, t, ha=ha_, va="top", fontsize=7.3, color=TINTA2)
    a.text(v.mean(), yb + 0.06, f"media {num(v.mean())}", ha="center", va="bottom", fontsize=7.6, color=col,
           fontweight="bold", path_effects=CONTORNO, zorder=7)
    # líneas de referencia
    a.axvline(0, color=ROJO_Z, linewidth=1.2, zorder=4)
    a.axvline(van_trs, color=TINTA2, linewidth=0.9, linestyle=(0, (2, 2)), zorder=4)
    a.text(van_trs, 1.08, f" VAN oficial {num(van_trs)}", fontsize=7.5, color=TINTA2, va="bottom", ha="left")
    a.text(0, 1.08, "VAN = 0 ", fontsize=7.5, color=ROJO_Z, va="bottom", ha="right", fontweight="bold")
    # chips con el % de cada zona
    zonas = [(v < 0).mean() * 100, ((v >= 0) & (v < van_trs)).mean() * 100, (v >= van_trs).mean() * 100]
    ZONAS_VAN[letra_p] = zonas
    chip(a, 0.995, 0.97, f"{zonas[0]:.1f} %  pierde dinero", ROJO_Z)
    chip(a, 0.995, 0.79, f"{zonas[1]:.1f} %  gana menos que el VAN oficial", AMBAR_Z)
    chip(a, 0.995, 0.61, f"{zonas[2]:.1f} %  gana más que el VAN oficial", VERDE_Z)
    a.text(0.995, 0.41, f"CVaR 95 %: {num(v[v <= p5].mean())}", transform=a.transAxes, ha="right", va="top",
           fontsize=7.5, color=TINTA)
    a.set_ylim(-0.42, 1.22)
    a.set_yticks([])
    a.spines["left"].set_visible(False)
    a.grid(False)
    letra(a, letra_p, nombre)
ejes[1].set_xlim(x_lo, x_hi)
ejes[1].xaxis.set_major_formatter(miles)
ejes[1].set_xlabel("VAN después de impuestos (US$ millones) · 10\u2009000 simulaciones por escenario · horizonte 2026–2041")
guardar_figura(fig, "figura2_distribucion_van")
pd.DataFrame(ZONAS_VAN, index=["Pérdida", "Entre 0 y VAN oficial", "Mayor o igual al VAN oficial"]).to_csv(
    SALIDAS / "zonas_van_por_escenario.csv")

# ---- Figura 3: probabilidad acumulada del VAN con la probabilidad de pérdida marcada ----
fig, a = plt.subplots(figsize=(7.2, 3.4))
for e, color, etiqueta in [(esc_A, NARANJA, "A · Precio del informe técnico"), (esc_B, AZUL, "B · Precio de mercado")]:
    v = np.sort(e["van_usd"])
    p = np.arange(1, len(v) + 1) / len(v)
    a.plot(v, p, color=color, linewidth=1.8, label=etiqueta)
    p0 = (v < 0).mean()
    a.scatter([0], [p0], s=18, color=color, zorder=5, edgecolor="white", linewidth=0.8)
    a.annotate(f"P(VAN < 0) = {p0*100:.1f} %", (0, p0), xytext=(60, 30) if color == AZUL else (-40, 14),
               textcoords="offset points", ha="left" if color == AZUL else "right", fontsize=8.5, fontweight="bold", color=color,
               arrowprops=dict(arrowstyle="-", color=color, linewidth=0.6))
    for q in (0.05, 0.95):
        xq = np.percentile(v, q * 100)
        a.scatter([xq], [q], s=12, color=color, zorder=4)
a.axvline(0, color=TINTA, linewidth=0.8)
a.set_xlim(min(esc_A["van_usd"].min(), -900) * 1.6, np.percentile(esc_B["van_usd"], 99.5))
a.axhline(0.05, color=REJILLA, linewidth=0.8)
a.axhline(0.95, color=REJILLA, linewidth=0.8)
a.text(a.get_xlim()[1], 0.05, "P5 ", ha="right", va="bottom", fontsize=8, color=TINTA2)
a.text(a.get_xlim()[1], 0.95, "P95 ", ha="right", va="bottom", fontsize=8, color=TINTA2)
a.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
a.xaxis.set_major_formatter(miles)
a.set_xlabel("VAN después de impuestos (US$ millones)")
a.set_ylabel("Probabilidad acumulada")
a.legend(loc="center right")
guardar_figura(fig, "figura3_distribucion_acumulada")

# ---- Figura 4: sensibilidad del VAN (barras con IC 95 %) + participación de cada factor (dona) ----
nombres_factor = {"Precio del oro": "Precio del oro", "Tipo de cambio": "Tipo de cambio (S/ por US$)",
                  "Riesgo país (WACC)": "Tasa de descuento (riesgo país)", "Demanda": "Demanda de inversión (GLD)"}
colores_factor = {"Precio del oro": "#d4a017", "Tipo de cambio": AZUL, "Riesgo país (WACC)": ROJO, "Demanda": AQUA}
orden = b.abs().sort_values().index
fig = plt.figure(figsize=(7.4, 3.3))
gs = GridSpec(1, 2, width_ratios=[2.2, 1.25], wspace=0.30, figure=fig)
a = fig.add_subplot(gs[0]); ad = fig.add_subplot(gs[1])
a.set_facecolor(FONDO_PANEL)
ic = 1.96 * mod_sens.bse[orden]
for y, o in enumerate(orden):
    v = b[o]
    a.barh(y, v, color=colores_factor[o], height=0.62, zorder=3, alpha=0.95)
    a.barh(y, v, color="none", edgecolor=TINTA, linewidth=0.5, height=0.62, zorder=4)
    a.errorbar(v, y, xerr=ic[o], fmt="none", ecolor=TINTA, capsize=2.5, linewidth=0.8, zorder=5)
    extremo = v + (ic[o] if v >= 0 else -ic[o])
    a.text(extremo + (0.02 if v >= 0 else -0.02) * abs(b).max(), y, num(v, signo=True), va="center",
           ha="left" if v >= 0 else "right", fontsize=8.5, fontweight="bold", color=TINTA)
a.set_yticks(range(len(orden)), [nombres_factor[o] for o in orden])
a.axvline(0, color=TINTA, linewidth=0.8)
a.grid(axis="y", visible=False)
a.grid(axis="x", color="white", linewidth=0.9)
a.set_xlim(min(b.min() - ic.max(), 0) * 1.9 - 0.10 * abs(b).max(), (abs(b).max() + ic.max()) * 1.22)
a.xaxis.set_major_formatter(miles)
a.set_xlabel("Cambio del VAN (S/ millones) si el factor sube 1 desviación estándar")
a.text(0.99, 0.04, f"R² = {mod_sens.rsquared:.3f} · F = {num(mod_sens.fvalue)} · N = {num(mod_sens.nobs)}",
       transform=a.transAxes, ha="right", fontsize=7.6, color=TINTA2)
letra(a, "a", "Efecto de cada factor (barras = IC 95 %)")
# Dona: participación aproximada de cada factor en la variación explicada (coeficientes estandarizados al cuadrado)
part = (b ** 2) / (b ** 2).sum() * 100
orden_d = part.sort_values(ascending=False).index
ad.pie(part[orden_d], colors=[colores_factor[o] for o in orden_d], startangle=90, counterclock=False,
       wedgeprops=dict(width=0.38, edgecolor="white", linewidth=1.5))
ad.text(0, 0.08, f"{part['Precio del oro']:.0f} %", ha="center", va="center", fontsize=14, fontweight="bold", color="#9a7410")
ad.text(0, -0.22, "precio del oro", ha="center", va="center", fontsize=7.8, color=TINTA2)
for k_, o in enumerate(orden_d):
    ad.text(-1.05, -1.25 - k_ * 0.27, f"■ {nombres_factor[o]}: {part[o]:.1f} %", fontsize=7.4, color=colores_factor[o],
            fontweight="bold", va="center", transform=ad.transData)
ad.set_xlim(-1.1, 1.1); ad.set_ylim(-2.25, 1.3)
ad.text(-1.0, 1.32, "b", fontsize=10, fontweight="bold", color=TINTA, va="bottom")
ad.text(-0.72, 1.32, "Participación aproximada", fontsize=8, color=TINTA, va="bottom")
ad.set_aspect("equal")
guardar_figura(fig, "figura4_tornado_sensibilidad")
pd.DataFrame({"Participacion_aprox_pct": part}).to_csv(SALIDAS / "participacion_factores_van.csv")

# ---- Figura 5: cono de probabilidad del precio del oro (escenario B) + densidad del precio final ----
from matplotlib.gridspec import GridSpec
ORO_MAPA = LinearSegmentedColormap.from_list("oro", ["#fff6d8", "#f7d77a", "#e7a924", "#b9770e", "#7a4a05"])
fig = plt.figure(figsize=(7.4, 4.3))
gs = GridSpec(1, 2, width_ratios=[4.3, 1], wspace=0.03, figure=fig)
a = fig.add_subplot(gs[0]); am = fig.add_subplot(gs[1], sharey=a)
for ax_ in (a, am):
    ax_.set_facecolor(FONDO_PANEL)
hist = base.set_index("fecha")["precio_oro"].loc["2014-01-01":].resample("ME").mean()
t0 = base["fecha"].iloc[-1]
fechas_fut = pd.DatetimeIndex([t0 + pd.DateOffset(years=k) for k in range(0, N_ANIOS + 2)])
pr = np.hstack([np.full((N_SIM, 1), P_MERCADO), esc_B["precios"]])
final = pr[:, -1]
# dos bandas fáciles de leer: 90 % de los futuros (clara) y 50 % central (oscura)
a.fill_between(fechas_fut, np.percentile(pr, 5, axis=0), np.percentile(pr, 95, axis=0),
               color="#f7d77a", linewidth=0, alpha=0.55, zorder=2, label="90 % de los futuros")
a.fill_between(fechas_fut, np.percentile(pr, 25, axis=0), np.percentile(pr, 75, axis=0),
               color="#d99a1c", linewidth=0, alpha=0.55, zorder=2, label="50 % central de los futuros")
# 60 futuros simulados con los datos reales (bootstrap), coloreados según su precio final
FUT_MAPA = LinearSegmentedColormap.from_list("fut", ["#b3302d", "#e8833a", "#e9c46a", "#5aa0d8", "#1f4e8c"])
idx_lineas = np.random.default_rng(SEMILLA).choice(N_SIM, 60, replace=False)   # solo para dibujar
lf = np.log(final); lf_lo, lf_hi = np.percentile(lf, [3, 97])
for i in idx_lineas[np.argsort(final[idx_lineas])]:
    a.plot(fechas_fut, pr[i], color=FUT_MAPA(np.clip((lf[i] - lf_lo) / (lf_hi - lf_lo), 0, 1)),
           linewidth=0.6, alpha=0.45, zorder=3)
# cinco futuros concretos: el mejor, el peor y tres intermedios (percentiles del precio final)
orden = np.argsort(final)
ejemplos = {"Un futuro muy bueno": orden[int(0.97 * N_SIM)], "Un futuro típico": orden[int(0.50 * N_SIM)],
            "Un futuro muy malo": orden[int(0.03 * N_SIM)]}
for (nom, i), colr in zip(ejemplos.items(), ["#1f4e8c", "#3b3a36", "#b3302d"]):
    a.plot(fechas_fut, pr[i], color=colr, linewidth=1.0, marker="o", markersize=2.2, zorder=5)
    a.annotate(nom, (fechas_fut[-1], pr[i, -1]), xytext=(-2, 7 if "malo" not in nom else -7), textcoords="offset points",
               ha="right", va="bottom" if "malo" not in nom else "top", fontsize=7.3, color=colr,
               fontweight="bold", path_effects=CONTORNO, zorder=9)
a.plot(fechas_fut, np.median(pr, axis=0), color="white", linewidth=3.2, zorder=6)
a.plot(fechas_fut, np.median(pr, axis=0), color=TINTA, linewidth=1.4, zorder=7, label="Mediana simulada")
a.plot(fechas_fut, pr.mean(axis=0), color=AZUL, linewidth=1.3, linestyle=(0, (2, 1.5)), zorder=7, label="Media simulada")
a.fill_between(hist.index, hist.min() * 0.5, hist, color="#d9d6cc", alpha=0.5, linewidth=0, zorder=1)
a.plot(hist.index, hist, color=TINTA, linewidth=1.6, zorder=7, label="Observado (promedio mensual, BCRP)")
a.axvline(t0, color=TINTA2, linewidth=0.9, linestyle=(0, (3, 2)), zorder=4)
a.text(t0 - pd.DateOffset(months=3), 0.975, "HISTORIA REAL  ", transform=a.get_xaxis_transform(), ha="right",
       fontsize=8, color=TINTA2, fontweight="bold", va="top")
a.text(t0 + pd.DateOffset(months=3), 0.975, "  SIMULACIÓN 2026–2041: 60 de 10\u2009000 futuros", transform=a.get_xaxis_transform(),
       fontsize=8, color=TINTA2, fontweight="bold", va="top")
for nivel, col, txt, va_ in [(P_TRS, NARANJA, f"Precio del informe técnico: US$ {num(P_TRS)}", "bottom"),
                             (P_EQUILIBRIO, ROJO, f"Precio de equilibrio (VAN = 0): US$ {num(P_EQUILIBRIO)}", "top")]:
    for ax_ in (a, am):
        ax_.axhline(nivel, color=col, linewidth=1.1, linestyle=(0, (4, 2)), zorder=8)
    a.text(hist.index[0] + pd.DateOffset(months=3), nivel * (1.04 if va_ == "bottom" else 0.96), txt, fontsize=7.8,
           color=col, va=va_, fontweight="bold", zorder=9, path_effects=CONTORNO)
a.legend(loc="upper center", bbox_to_anchor=(0.6, -0.09), ncol=3, fontsize=7.8, frameon=False)
a.set_yscale("log")
a.yaxis.set_major_formatter(miles)
a.yaxis.set_minor_formatter(FuncFormatter(lambda x, _: ""))
a.set_ylabel("US$ por onza (escala logarítmica)")
a.set_xlim(hist.index[0], fechas_fut[-1] + pd.DateOffset(months=5))
a.set_ylim(min(hist.min(), np.percentile(final, 1)) * 0.72, np.percentile(final, 99.3) * 1.15)
a.grid(axis="y", color="white", linewidth=0.9)
letra(a, "a", "Cono de probabilidad del precio del oro, 2014–2041")
# Panel derecho: densidad del precio final (2041) con el mismo degradado
yl = np.exp(np.linspace(np.log(a.get_ylim()[0]), np.log(a.get_ylim()[1]), 500))
dens = stats.gaussian_kde(np.log(final))(np.log(yl))
dens = dens / dens.max()
for k_ in range(len(yl) - 1):
    q = (final < yl[k_]).mean()
    intens = 1 - abs(q - 0.5) * 2
    am.fill_betweenx(yl[k_:k_ + 2], 0, dens[k_:k_ + 2], color=ORO_MAPA(0.12 + 0.85 * intens), linewidth=0)
am.plot(dens, yl, color=TINTA, linewidth=0.9)
for q in (95, 50, 5):
    yq = np.percentile(final, q)
    am.scatter([0.02], [yq], s=14, color=TINTA, zorder=5)
    am.text(0.08, yq, f"P{q}: {num(yq)}", fontsize=7.4, va="center", color=TINTA, fontweight="bold", path_effects=CONTORNO)
debajo = (final < P_EQUILIBRIO).mean() * 100
am.text(0.97, 0.03, f"{debajo:.1f} % termina\nbajo el equilibrio", transform=am.transAxes, ha="right",
        fontsize=7.4, color=ROJO, fontweight="bold")
am.set_xlim(0, 1.15)
am.set_xticks([])
am.tick_params(axis="y", labelleft=False)
am.spines["left"].set_visible(False)
am.grid(False)
am.text(0, 1.04, "b", transform=am.transAxes, fontsize=10, fontweight="bold", color=TINTA, va="bottom")
am.text(0.16, 1.04, f"Precio en {fechas_fut[-1].year}", transform=am.transAxes, fontsize=8, color=TINTA, va="bottom")
guardar_figura(fig, "figura5_abanico_precio_oro")

# ---- Figura 15: futuros simulados de las cuatro variables del estudio (escenario B) ----
FUT_MAPA = LinearSegmentedColormap.from_list("fut", ["#b3302d", "#e8833a", "#e9c46a", "#5aa0d8", "#1f4e8c"])
fig, ejes = plt.subplots(2, 2, figsize=(7.4, 5.3))
anios_fut = [t0.year + k for k in range(0, N_ANIOS + 2)]
sel = np.random.default_rng(SEMILLA + 1).choice(N_SIM, 50, replace=False)   # solo para dibujar
paneles4 = [
    (ejes[0, 0], "a", "Y · Precio del oro (US$/oz, escala log.)", pr, True),
    (ejes[0, 1], "b", "X1 · Demanda: choque acumulado del monto GLD (log.)",
     np.hstack([np.zeros((N_SIM, 1)), esc_B["demanda"]]), False),
    (ejes[1, 0], "c", "X2 · Tipo de cambio (S/ por US$)", esc_B["tc"], False),
]
for a, l, tit, M_, logy in paneles4:
    a.set_facecolor(FONDO_PANEL)
    fin_ = M_[:, -1]
    rk = stats.rankdata(fin_) / len(fin_)
    for i in sel[np.argsort(fin_[sel])]:
        a.plot(anios_fut, M_[i], color=FUT_MAPA(rk[i]), linewidth=0.7, alpha=0.6, zorder=2)
    a.fill_between(anios_fut, np.percentile(M_, 5, axis=0), np.percentile(M_, 95, axis=0), color="#e9e4d4", alpha=0.6,
                   linewidth=0, zorder=1)
    for q_ in (5, 95):
        a.plot(anios_fut, np.percentile(M_, q_, axis=0), color=TINTA, linewidth=0.9, linestyle=(0, (3, 2)), zorder=3)
    a.plot(anios_fut, np.median(M_, axis=0), color="white", linewidth=3, zorder=4)
    a.plot(anios_fut, np.median(M_, axis=0), color=TINTA, linewidth=1.3, zorder=5)
    if logy:
        a.set_yscale("log"); a.yaxis.set_minor_formatter(FuncFormatter(lambda x, _: ""))
    a.yaxis.set_major_formatter(miles if np.nanmax(np.abs(M_)) > 100 and not l == "b" else FuncFormatter(lambda x, _: f"{x:,.1f}".replace("-", "−")))
    lo_, hi_ = np.percentile(M_, 1), np.percentile(M_, 99)
    a.set_ylim(lo_ if not logy else lo_ * 0.9, hi_ if not logy else hi_ * 1.1)
    a.grid(axis="y", color="white", linewidth=0.9)
    letra(a, l, tit)
a = ejes[1, 1]
a.set_facecolor(FONDO_PANEL)
k_pct = esc_B["k"] * 100
cuentas, bordes, parches = a.hist(k_pct, bins=45, edgecolor="white", linewidth=0.3)
centros = (bordes[:-1] + bordes[1:]) / 2
for c_, pa_ in zip(centros, parches):
    pa_.set_facecolor(FUT_MAPA(1 - np.clip((c_ - np.percentile(k_pct, 1)) / (np.percentile(k_pct, 99) - np.percentile(k_pct, 1)), 0, 1)))
a.axvline(K0 * 100, color=TINTA, linewidth=1.1, linestyle=(0, (3, 2)))
a.text(K0 * 100, cuentas.max() * 1.02, f" WACC del informe: {K0*100:.2f} %", fontsize=7.6, color=TINTA, va="bottom")
for q in (5, 95):
    a.axvline(np.percentile(k_pct, q), color=TINTA2, linewidth=0.8, linestyle=(0, (1, 1.5)))
a.text(0.98, 0.70, f"P5 = {np.percentile(k_pct, 5):.2f} %\nP95 = {np.percentile(k_pct, 95):.2f} %", transform=a.transAxes,
       ha="right", fontsize=7.6, color=TINTA2)
a.set_ylim(0, cuentas.max() * 1.15)
a.set_yticks([])
a.set_xlabel("Tasa de descuento simulada (%)")
a.grid(False)
letra(a, "d", "X3 · Riesgo país: tasa de descuento de cada futuro")
for a in (ejes[0, 0], ejes[0, 1], ejes[1, 0]):
    a.axvline(t0.year, color=TINTA2, linewidth=0.7)
    a.set_xlim(anios_fut[0], anios_fut[-1])
    a.set_xticks(range(anios_fut[0], anios_fut[-1] + 1, 3))
    a.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))
fig.text(0.5, -0.01, "Líneas: 50 de los 10\u2009000 futuros simulados (color según el valor final: rojo bajo, azul alto) · línea negra: mediana · "
         "líneas discontinuas: percentiles 5 y 95", ha="center", fontsize=7.4, color=TINTA2)
fig.tight_layout(h_pad=2.2, w_pad=1.8)
guardar_figura(fig, "figura15_futuros_cuatro_variables")

# ---- Figura 6: VAN de cada simulación frente al precio medio del oro, con zonas de resultado ----
fig, a = plt.subplots(figsize=(7.4, 4.0))
x_min, x_max = 700, np.percentile(esc_B["precios"][:, :N_ANIOS].mean(axis=1), 99.7)
y_min = min(esc_A["van_usd"].min(), esc_B["van_usd"].min()) * 1.15
y_max = np.percentile(esc_B["van_usd"], 99.7)
a.axhspan(y_min, 0, color="#d64541", alpha=0.10, zorder=0)
a.axhspan(0, van_trs, color="#f0a830", alpha=0.12, zorder=0)
a.axhspan(van_trs, y_max, color="#1f9e6e", alpha=0.07, zorder=0)
for e, color, etiqueta in [(esc_A, NARANJA, "Escenario A · precio del informe técnico"),
                           (esc_B, AZUL, "Escenario B · precio de mercado")]:
    pm = e["precios"][:, :N_ANIOS].mean(axis=1)
    a.scatter(pm, e["van_usd"], s=4, color=color, alpha=0.30, linewidths=0, rasterized=True, label=etiqueta, zorder=3)
    b1, b0 = np.polyfit(pm, e["van_usd"], 1)
    xs = np.linspace(pm.min(), min(pm.max(), x_max), 50)
    a.plot(xs, b0 + b1 * xs, color=color, linewidth=1.3, zorder=4)
precios_lin = np.linspace(x_min, x_max, 200)
van_lin = np.array([calcular_van(np.full((1, N_ANIOS + 1), p), np.array([K0]))[0][0] for p in precios_lin]) / 1e6
a.plot(precios_lin, van_lin, color=TINTA, linewidth=1.2, linestyle=(0, (4, 2)), zorder=5,
       label="Modelo con precio constante y tasa 8.26 %")
for xv, col, txt, y_ in [(P_EQUILIBRIO, ROJO, f"Equilibrio\nUS$ {num(P_EQUILIBRIO)}", 0.97),
                         (P_TRS, NARANJA, f"Informe técnico\nUS$ {num(P_TRS)}", 0.84),
                         (P_MERCADO, AZUL, f"Mercado\nUS$ {num(P_MERCADO)}", 0.97)]:
    a.axvline(xv, color=col, linewidth=1, linestyle=(0, (1, 2)), zorder=5)
    a.text(xv, y_, txt, transform=a.get_xaxis_transform(), fontsize=7.8, color=col, fontweight="bold",
           ha="center", va="top", bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1), zorder=6)
for y_txt, txt, col in [(y_min * 0.5, "PÉRDIDA", "#b3302d"), (van_trs / 2, "GANA, PERO MENOS QUE EL VAN OFICIAL", "#b07400"),
                        (y_max * 0.85, "GANA MÁS QUE EL VAN OFICIAL", "#167a54")]:
    a.text(x_max * 0.985, y_txt, txt, ha="right", va="center", fontsize=7.8, color=col, fontweight="bold", zorder=6)
a.set_xlim(x_min, x_max); a.set_ylim(y_min, y_max)
a.xaxis.set_major_formatter(miles); a.yaxis.set_major_formatter(miles)
a.set_xlabel("Precio medio simulado del oro durante la vida de la mina (US$ por onza)")
a.set_ylabel("VAN (US$ millones)")
leg = a.legend(loc="center left", markerscale=4, fontsize=8, frameon=True, facecolor="white", edgecolor="none",
               framealpha=0.9, bbox_to_anchor=(0.0, 0.62))
for h in leg.legend_handles:
    h.set_alpha(1)
guardar_figura(fig, "figura6_van_vs_precio")

# ---- Figura 7: matriz de correlaciones en burbujas (tamaño = fuerza, color = signo) ----
etiquetas = ["Oro", "Demanda", "Tipo de cambio", "Riesgo país"]
C = R[["r_oro", "r_demanda", "r_tc", "d_riesgo_pais"]].corr().to_numpy()
mapa = LinearSegmentedColormap.from_list("divergente", ["#b42f2e", ROJO, "#f3f2ee", AZUL, "#164a8a"])
n = len(R)
fig, a = plt.subplots(figsize=(4.6, 3.9))
a.set_facecolor(FONDO_PANEL)
for i in range(4):
    for j in range(4):
        if j > i:
            continue
        r = C[i, j]
        if i == j:
            a.text(j, i, etiquetas[i].replace(" ", "\n"), ha="center", va="center", fontsize=8, color=TINTA2, fontweight="bold")
            continue
        p = 2 * stats.t.sf(abs(r) * np.sqrt((n - 2) / (1 - r ** 2)), n - 2)
        estrellas = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
        a.scatter(j, i, s=300 + 4200 * abs(r), color=mapa((r + 0.4) / 0.8), edgecolor="white", linewidth=1.2, zorder=3)
        a.text(j, i, num(r, 3, signo=True) + "\n" + (estrellas or "n.s."), ha="center", va="center", fontsize=8,
               fontweight="bold", color="white" if abs(r) > 0.15 else TINTA, zorder=4)
a.set_xlim(-0.6, 3.6); a.set_ylim(3.6, -0.6)
a.set_xticks([]); a.set_yticks([])
for sp in a.spines.values():
    sp.set_visible(False)
a.grid(False)
sm_ = plt.cm.ScalarMappable(cmap=mapa, norm=Normalize(-0.4, 0.4))
cb = fig.colorbar(sm_, ax=a, fraction=0.04, pad=0.02)
cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6.5, length=0)
cb.set_label("Correlación de Pearson", fontsize=8)
fig.text(0.02, 0.01, f"Rendimientos diarios 2004–2026 · N = {num(n)} días · *** p < 0.01  ** p < 0.05  * p < 0.10  n.s. = no significativa",
         fontsize=7, color=TINTA2)
guardar_figura(fig, "figura7_correlaciones")

# ---- Figura 13: mapa de calor de la probabilidad de pérdida según el precio inicial y la tasa de descuento ----
# Reutiliza las 10 000 trayectorias del escenario B (sin nuevos números aleatorios): el precio escala con P0
rel = esc_B["precios"] / P_MERCADO
precios_ini = np.arange(1_400, 5_001, 100)
cambios_k = np.arange(-3.0, 5.01, 0.5)
P_PERD = np.zeros((len(cambios_k), len(precios_ini)))
for i, dk in enumerate(cambios_k):
    k_i = np.maximum(esc_B["k"] + dk / 100, 0.01)
    for j, p0 in enumerate(precios_ini):
        P_PERD[i, j] = (calcular_van(p0 * rel, k_i)[0] < 0).mean() * 100
pd.DataFrame(P_PERD, index=cambios_k, columns=precios_ini).to_csv(SALIDAS / "mapa_probabilidad_perdida.csv")
MAPA_RIESGO = LinearSegmentedColormap.from_list("riesgo", ["#1f9e6e", "#bfe3cf", "#fff3c4", "#f0a830", "#d64541", "#8c1d1a"])
fig, a = plt.subplots(figsize=(7.4, 3.9))
im = a.pcolormesh(precios_ini, K0 * 100 + cambios_k, P_PERD, cmap=MAPA_RIESGO, vmin=0, vmax=100, shading="nearest")
cs = a.contour(precios_ini, K0 * 100 + cambios_k, P_PERD, levels=[5, 25, 50], colors=TINTA, linewidths=[1.4, 0.9, 0.9],
               linestyles=["-", (0, (4, 2)), (0, (1, 1))])
a.clabel(cs, fmt=lambda v: f"{v:.0f} %", fontsize=8, inline=True)
for x_, col, txt in [(P_TRS, NARANJA, f"Informe técnico\n{(esc_A['van_usd'] < 0).mean()*100:.1f} % de pérdida"),
                     (P_MERCADO, AZUL, f"Mercado 31/08/2026\n{(esc_B['van_usd'] < 0).mean()*100:.1f} % de pérdida")]:
    a.scatter([x_], [K0 * 100], s=70, color=col, edgecolor="white", linewidth=1.5, zorder=6)
    a.annotate(txt, (x_, K0 * 100), xytext=(0, 22), textcoords="offset points", ha="center", fontsize=8,
               fontweight="bold", color=TINTA, zorder=7,
               bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=col, linewidth=0.8),
               arrowprops=dict(arrowstyle="-", color=col, linewidth=0.8))
a.axhline(K0 * 100, color="white", linewidth=0.8, linestyle=(0, (2, 2)))
a.xaxis.set_major_formatter(miles)
a.set_xlabel("Precio inicial del oro (US$ por onza)")
a.set_ylabel("Tasa de descuento media (%)")
a.grid(False)
cb = fig.colorbar(im, ax=a, pad=0.02)
cb.set_label("Probabilidad de VAN < 0 (%)"); cb.outline.set_visible(False)
guardar_figura(fig, "figura13_mapa_probabilidad_perdida")

# ---- Figura 14: diagnóstico gráfico del modelo econométrico (residuos de la regresión de la tabla 5) ----
fig, ejes = plt.subplots(2, 2, figsize=(7.4, 5.0))
fechas_R = base.loc[R.index, "fecha"]
res_pct = residuos * 100
a = ejes[0, 0]
a.scatter(fechas_R, res_pct, s=1.2, c=np.abs(res_pct), cmap=LinearSegmentedColormap.from_list("r", ["#9fc5e8", AZUL, ROJO]),
          linewidths=0, rasterized=True)
sd = res_pct.std()
for k_ in (-3, 3):
    a.axhline(k_ * sd, color=ROJO, linewidth=0.8, linestyle=(0, (3, 2)))
a.text(fechas_R.iloc[0], 3 * sd, " ±3 desviaciones", fontsize=7.5, color=ROJO, va="bottom")
a.set_ylabel("Residuo (%)")
letra(a, "a", "Residuos en el tiempo: rachas de volatilidad")
a = ejes[0, 1]
a.hist(res_pct, bins=120, density=True, color=AZUL_CLARO, edgecolor="white", linewidth=0.2)
xs = np.linspace(res_pct.min(), res_pct.max(), 300)
a.plot(xs, stats.norm.pdf(xs, res_pct.mean(), sd), color=ROJO, linewidth=1.3, label="Normal teórica")
a.plot(xs, stats.gaussian_kde(res_pct)(xs), color=AZUL, linewidth=1.3, label="Residuos reales")
a.set_xlim(-5 * sd, 5 * sd)
a.legend(fontsize=7.5)
a.set_yticks([])
a.text(0.98, 0.55, f"Jarque-Bera = {num(jb)}\np < 0.001\ncurtosis = {curt_res:.2f}", transform=a.transAxes, ha="right",
       fontsize=7.5, color=TINTA)
letra(a, "b", "Distribución: colas más pesadas que la normal")
a = ejes[1, 0]
(osm, osr), (pend, inter, _) = stats.probplot(res_pct, dist="norm")
a.scatter(osm, osr, s=2, color=AZUL, alpha=0.6, linewidths=0, rasterized=True)
a.plot(osm, pend * osm + inter, color=ROJO, linewidth=1.2)
a.set_xlabel("Cuantiles teóricos (normal)"); a.set_ylabel("Cuantiles de los residuos (%)")
letra(a, "c", "Gráfico Q-Q: los extremos se alejan de la recta")
a = ejes[1, 1]
from statsmodels.tsa.stattools import acf
rez = np.arange(1, 31)
acf_r = acf(residuos, nlags=30)[1:]
acf_r2 = acf(residuos ** 2, nlags=30)[1:]
banda = 1.96 / np.sqrt(len(residuos))
a.bar(rez - 0.2, acf_r, width=0.4, color=AZUL, label="Residuos")
a.bar(rez + 0.2, acf_r2, width=0.4, color=NARANJA, label="Residuos al cuadrado")
a.axhspan(-banda, banda, color="#e6e5e0", zorder=0)
a.axhline(0, color=TINTA, linewidth=0.6)
a.set_xlabel("Rezago (días)"); a.set_ylabel("Autocorrelación")
a.legend(fontsize=7.5)
letra(a, "d", "Autocorrelación: el riesgo se agrupa (ARCH)")
fig.tight_layout(h_pad=2.0, w_pad=1.5)
guardar_figura(fig, "figura14_diagnostico_modelo")

# ------------------------------------------------------------------
# BLOQUE FINAL. Excel de presentación (generado por código, no a mano) y resumen en pantalla
# ------------------------------------------------------------------
with pd.ExcelWriter(SALIDAS / "resultados_tema55.xlsx") as xl:
    for nombre, t in TABLAS.items():
        t.to_excel(xl, sheet_name=nombre[:31], index=False)
registrar(f"Tablas: {len(TABLAS)} | Figuras: 11 (PNG 300 dpi + PDF) | Cointegración oro-demanda: {COINTEGRADAS}")
print("\n=== CONTRASTE DE HIPÓTESIS ===")
print(contraste[["Hipótesis", "Estadístico", "Valor p", "Decisión"]].to_string(index=False))
print("\n=== DISTRIBUCIÓN DEL VAN ===")
print(TABLAS["tabla8_distribucion_van"].round(2).to_string(index=False))
