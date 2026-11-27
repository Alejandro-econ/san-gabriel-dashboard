# Autor: Alejandro Soto Antezana | Código: 2024200531K
# Tema 55: Riesgo del proyecto: simulación de Monte Carlo sobre precio, demanda y tipo de cambio
# Script 05: figuras en tres dimensiones (3D) para el artículo
# Fecha de extracción de los datos: 2026-10-17 (ver log_ejecucion.txt)
#
# Este script NO descarga ni modifica datos. Solo lee:
#   - datos_procesados/parametros_proyecto_2024200531K.csv  (parámetros leídos del informe de la SEC)
#   - datos_procesados/datos_procesados_2024200531K.csv     (base diaria, para la nube 3D)
#   - salidas/simulaciones_van.csv y salidas/tabla7_parametros_y_validacion.csv (resultados del script 04)
# y guarda 5 figuras 3D en salidas/ (PNG 300 dpi + PDF). Ejecutar DESPUÉS de 04_analisis.py.

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
from scipy.stats import gaussian_kde

# ------------------------------------------------------------------
# BLOQUE 1. Rutas y lectura de insumos (rutas relativas a la carpeta del proyecto)
# ------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
CODIGO = "2024200531K"
PROCESADOS, SALIDAS = RAIZ / "datos_procesados", RAIZ / "salidas"

par = pd.read_csv(PROCESADOS / f"parametros_proyecto_{CODIGO}.csv").set_index("parametro")["valor"]
sims = pd.read_csv(SALIDAS / "simulaciones_van.csv")
t7 = pd.read_csv(SALIDAS / "tabla7_parametros_y_validacion.csv").set_index("Concepto")["Valor"]
P_MERCADO = float(t7[[c for c in t7.index if c.startswith("Precio de mercado")][0]])
P_EQUILIBRIO = float(t7[[c for c in t7.index if c.startswith("Precio del oro de equilibrio")][0]])

# ------------------------------------------------------------------
# BLOQUE 2. El mismo modelo del VAN del script 04 (precio constante), para dibujar superficies
# ------------------------------------------------------------------
Q_TOTAL = par["oro_pagable_koz"] * 1_000
N_ANIOS = int(round(par["vida_mina_anios"]))
Q_ANIO = Q_TOTAL / N_ANIOS
I0, CIERRE = par["inversion_inicial_musd"] * 1e6, par["costo_cierre_musd"] * 1e6
K0, P_TRS, AISC = par["tasa_descuento_pct"] / 100, par["precio_oro_trs_usd_oz"], par["aisc_usd_oz"]
FC_ANTES, FC_DESP = par["flujo_antes_impuestos_musd"] * 1e6, par["flujo_despues_impuestos_musd"] * 1e6
C_UNIT = P_TRS - (FC_ANTES + I0 + CIERRE) / Q_TOTAL
TAU = 1 - (FC_DESP + I0 + CIERRE) / (FC_ANTES + I0 + CIERRE)


def van_constante(precio, k, costo=C_UNIT):
    """VAN en millones de US$ con precio, tasa y costo constantes (acepta matrices de igual forma)."""
    t = np.arange(1, N_ANIOS + 1).reshape((-1,) + (1,) * np.ndim(precio))
    margen = Q_ANIO * (precio - costo)
    flujo = margen - TAU * np.maximum(margen, 0)
    van = -I0 + (flujo / (1 + k) ** t).sum(axis=0) - CIERRE / (1 + k) ** (N_ANIOS + 1)
    return van / 1e6


# ------------------------------------------------------------------
# BLOQUE 3. Estilo común (mismos colores que las figuras 1 a 7; aptos para daltonismo)
# ------------------------------------------------------------------
TINTA, TINTA2 = "#1f1f1d", "#5f5e5a"
AZUL, NARANJA, AQUA, AMARILLO, ROJO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948"
DIVERGENTE = LinearSegmentedColormap.from_list("van", ["#b42f2e", ROJO, "#f6c6c5", "#f3f2ee",
                                                       "#bcd6f5", AZUL, "#164a8a"])
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Lato", "Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "text.color": TINTA, "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.12, "pdf.fonttype": 42,
})


def num(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", " ").replace("-", "−")


miles = FuncFormatter(lambda x, _: num(x))


def ejes_limpios(ax):
    """Paneles 3D sin fondo gris y con rejilla suave (estilo editorial)."""
    for eje in (ax.xaxis, ax.yaxis, ax.zaxis):
        eje.set_pane_color((1, 1, 1, 0))
        eje._axinfo["grid"].update(color="#e6e5e0", linewidth=0.5)
        eje.line.set_color(TINTA2)
        eje.line.set_linewidth(0.6)


def guardar(fig, nombre):
    fig.savefig(SALIDAS / f"{nombre}.png")
    fig.savefig(SALIDAS / f"{nombre}.pdf")
    plt.close(fig)
    print("Guardada:", nombre)


def etiqueta3d(ax, x, y, z, texto, color, dz=0):
    ax.scatter([x], [y], [z], s=38, color=color, edgecolor="white", linewidth=0.9, depthshade=False, zorder=10)
    ax.plot([x, x], [y, y], [z, z + dz], color=color, linewidth=0.8, zorder=10)
    ax.text(x, y, z + dz, texto, color=TINTA, fontsize=6.8, fontweight="bold", zorder=11,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=color, linewidth=0.6))


# ------------------------------------------------------------------
# FIGURA 8. Superficie del VAN según el precio del oro y la tasa de descuento
# ------------------------------------------------------------------
precios = np.linspace(1_200, 5_600, 90)
tasas = np.linspace(0.04, 0.14, 60)
PP, KK = np.meshgrid(precios, tasas)
VV = van_constante(PP, KK)
norma = TwoSlopeNorm(vmin=VV.min(), vcenter=0, vmax=VV.max())

fig = plt.figure(figsize=(4.1, 3.4))
ax = fig.add_subplot(projection="3d")
ax.plot_surface(PP, KK * 100, VV, cmap=DIVERGENTE, norm=norma, rstride=2, cstride=2,
                linewidth=0.15, edgecolor="white", antialiased=True, alpha=0.97)
piso = VV.min() - 400
ax.contourf(PP, KK * 100, VV, zdir="z", offset=piso, levels=18, cmap=DIVERGENTE, norm=norma, alpha=0.55)
ax.contour(PP, KK * 100, VV, zdir="z", offset=piso, levels=[0], colors=TINTA, linewidths=1.4)
v_trs, v_mer = van_constante(P_TRS, K0), van_constante(P_MERCADO, K0)
etiqueta3d(ax, P_TRS, K0 * 100, v_trs, f" Informe técnico (VAN {num(v_trs)})", NARANJA, dz=900)
etiqueta3d(ax, P_MERCADO, K0 * 100, v_mer, f" Mercado (VAN {num(v_mer)})", AZUL, dz=700)
ax.text(P_EQUILIBRIO + 80, 13.5, piso, "VAN = 0", color=TINTA, fontsize=8.5, fontweight="bold")
ax.set_xlabel("Precio del oro (US$/oz)", labelpad=4)
ax.set_ylabel("Tasa de descuento (%)", labelpad=3)
ax.set_zlabel("VAN (millones de US$)", labelpad=4)
ax.xaxis.set_major_formatter(miles); ax.zaxis.set_major_formatter(miles)
ax.set_zlim(piso, VV.max())
ax.view_init(elev=24, azim=-128)
ejes_limpios(ax)
m = plt.cm.ScalarMappable(cmap=DIVERGENTE, norm=norma); m.set_array([])
cb = fig.colorbar(m, ax=ax, shrink=0.5, pad=0.14, format=miles)
cb.outline.set_visible(False)
guardar(fig, "figura8_superficie_van_precio_tasa")

# ------------------------------------------------------------------
# FIGURA 9. Superficie del VAN según el precio del oro y el costo unitario
# ------------------------------------------------------------------
costos = np.linspace(1_100, 2_600, 70)
PP2, CC = np.meshgrid(precios, costos)
VV2 = van_constante(PP2, K0, CC)
norma2 = TwoSlopeNorm(vmin=VV2.min(), vcenter=0, vmax=VV2.max())
fig = plt.figure(figsize=(4.1, 3.4))
ax = fig.add_subplot(projection="3d")
ax.plot_surface(PP2, CC, VV2, cmap=DIVERGENTE, norm=norma2, rstride=2, cstride=2,
                linewidth=0.15, edgecolor="white", alpha=0.97)
piso2 = VV2.min() - 400
ax.contourf(PP2, CC, VV2, zdir="z", offset=piso2, levels=18, cmap=DIVERGENTE, norm=norma2, alpha=0.55)
ax.contour(PP2, CC, VV2, zdir="z", offset=piso2, levels=[0], colors=TINTA, linewidths=1.4)
etiqueta3d(ax, P_MERCADO, C_UNIT, van_constante(P_MERCADO, K0), f" Costo implícito {num(C_UNIT)}", AZUL, dz=700)
etiqueta3d(ax, P_MERCADO, AISC, van_constante(P_MERCADO, K0, AISC), f" AISC {num(AISC)}", AQUA, dz=-1500)
etiqueta3d(ax, P_TRS, C_UNIT, van_constante(P_TRS, K0), " Informe técnico", NARANJA, dz=1100)
ax.set_xlabel("Precio del oro (US$/oz)", labelpad=4)
ax.set_ylabel("Costo unitario (US$/oz)", labelpad=4)
ax.set_zlabel("VAN (millones de US$)", labelpad=4)
for e in (ax.xaxis, ax.yaxis, ax.zaxis):
    e.set_major_formatter(miles)
ax.set_zlim(piso2, VV2.max())
ax.view_init(elev=24, azim=-128)
ejes_limpios(ax)
m = plt.cm.ScalarMappable(cmap=DIVERGENTE, norm=norma2); m.set_array([])
cb = fig.colorbar(m, ax=ax, shrink=0.5, pad=0.14, format=miles)
cb.outline.set_visible(False)
guardar(fig, "figura9_superficie_van_precio_costo")

# ------------------------------------------------------------------
# FIGURA 10. Histograma 3D conjunto: tasa de descuento simulada y VAN (escenario B)
# ------------------------------------------------------------------
k_sim, van_b = sims["wacc_B"].to_numpy() * 100, sims["van_usd_mm_B"].to_numpy()
lim_v = np.percentile(van_b, [0.5, 99.5])
H, xb, yb = np.histogram2d(k_sim, np.clip(van_b, *lim_v), bins=[8, 10],
                           range=[[np.percentile(k_sim, 0.5), np.percentile(k_sim, 99.5)], lim_v])
xc, yc = np.meshgrid((xb[:-1] + xb[1:]) / 2, (yb[:-1] + yb[1:]) / 2, indexing="ij")
dx, dy = (xb[1] - xb[0]) * 0.85, (yb[1] - yb[0]) * 0.85
alto = H.ravel() / len(van_b) * 100                         # % de las 10 000 simulaciones
color_barra = plt.cm.Blues(0.30 + 0.70 * alto / alto.max())       # más alto = azul más intenso
color_barra[yc.ravel() < 0] = matplotlib.colors.to_rgba(ROJO)     # barras con VAN negativo en rojo
fig = plt.figure(figsize=(4.1, 3.4))
ax = fig.add_subplot(projection="3d")
mask = alto > 0
ax.bar3d(xc.ravel()[mask] - dx / 2, yc.ravel()[mask] - dy / 2, 0, dx, dy, alto[mask],
         color=color_barra[mask], edgecolor="white", linewidth=0.25, shade=True, alpha=0.95)
ax.set_xlabel("Tasa de descuento simulada (%)", labelpad=4)
ax.set_ylabel("VAN (millones de US$)", labelpad=5)
ax.set_zlabel("Simulaciones (%)", labelpad=3)
ax.yaxis.set_major_formatter(miles)
ax.view_init(elev=28, azim=-55)
ejes_limpios(ax)
guardar(fig, "figura10_histograma3d_tasa_van")

# ------------------------------------------------------------------
# FIGURA 11. "Cordillera" 3D: distribución del VAN en los escenarios A, B y C
# ------------------------------------------------------------------
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig = plt.figure(figsize=(4.1, 3.4))
ax = fig.add_subplot(projection="3d")
malla = np.linspace(-2_000, 12_000, 600)
filas = [("A: precio del informe técnico", "van_usd_mm_A", NARANJA),
         ("B: precio de mercado (principal)", "van_usd_mm_B", AZUL),
         ("C: B con tendencia histórica", "van_usd_mm_C", AQUA)]
resumen_c = []
for i, (nombre, col, color) in enumerate(filas):
    v = sims[col].to_numpy()
    dens = gaussian_kde(v)(malla)
    dens = dens / dens.max()
    verts = [(malla[0], i, 0)] + list(zip(malla, np.full_like(malla, i), dens)) + [(malla[-1], i, 0)]
    ax.add_collection3d(Poly3DCollection([verts], facecolor=color, alpha=0.35, edgecolor=color, linewidth=1.1))
    neg = malla < 0
    vneg = [(malla[0], i, 0)] + list(zip(malla[neg], np.full(neg.sum(), i), dens[neg])) + [(0, i, 0)]
    ax.add_collection3d(Poly3DCollection([vneg], facecolor=ROJO, alpha=0.75, edgecolor="none"))
    media = v.mean()
    ax.plot([media, media], [i, i], [0, 1.08], color=TINTA, linewidth=1, linestyle="--")
    resumen_c.append((nombre[0], color, f"{nombre[0]}: media {num(media)} · pérdida {(v < 0).mean() * 100:.1f} %"))
ax.plot([0, 0], [-0.3, 2.3], [0, 0], color=ROJO, linewidth=1.2)
for k_, (_, color, txt) in enumerate(resumen_c):
    ax.text2D(0.02, 0.97 - 0.06 * k_, txt, transform=ax.transAxes, fontsize=6.8, color=color, fontweight="bold")
ax.set_xlim(malla[0], malla[-1]); ax.set_ylim(-0.3, 2.3); ax.set_zlim(0, 1.3)
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["A", "B", "C"], fontsize=9, fontweight="bold")
ax.set_xlabel("VAN (millones de US$)", labelpad=4)
ax.set_zlabel("Densidad relativa", labelpad=4)
ax.set_xticks(range(0, 12_001, 4_000))
ax.xaxis.set_major_formatter(miles)
ax.view_init(elev=22, azim=-70)
ejes_limpios(ax)
guardar(fig, "figura11_cordillera_escenarios")

# ------------------------------------------------------------------
# FIGURA 12. Nube 3D de los rendimientos diarios reales: oro, tipo de cambio y riesgo país
# ------------------------------------------------------------------
archivo = PROCESADOS / f"datos_procesados_{CODIGO}.csv"
if archivo.exists():
    base = pd.read_csv(archivo, parse_dates=["fecha"]).dropna(subset=["r_oro", "r_tc", "d_riesgo_pais"])
    x, y, z = base["r_oro"] * 100, base["r_tc"] * 100, base["d_riesgo_pais"] * 100   # % y pbs
    anio = base["fecha"].dt.year
    fig = plt.figure(figsize=(4.1, 3.4))
    ax = fig.add_subplot(projection="3d")
    lx, ly, lz = np.percentile(x, [0.2, 99.8]), np.percentile(y, [0.2, 99.8]), np.percentile(z, [0.2, 99.8])
    dentro = x.between(*lx) & y.between(*ly) & z.between(*lz)
    # dos periodos con colores distintos (los mismos de las submuestras del modelo econométrico)
    for (ini, fin, col, nom) in [(2004, 2015, "#2a78d6", "2004–2015"), (2016, 2026, "#eda100", "2016–2026")]:
        sel_ = dentro & anio.between(ini, fin)
        ax.scatter(x[sel_], y[sel_], z[sel_], color=col, s=3, alpha=0.35, depthshade=False, linewidth=0,
                   rasterized=True, label=nom)
    # sombra de la nube en el piso (proyección 2D)
    ax.scatter(x[dentro], y[dentro], np.full(dentro.sum(), lz[0]), color="#9a9890", s=1.5, alpha=0.30, linewidth=0, rasterized=True)
    # recta de regresión del tipo de cambio sobre el oro, en el plano del piso
    b = np.polyfit(x[dentro], y[dentro], 1)
    xs = np.linspace(*lx, 50)
    ax.plot(xs, np.polyval(b, xs), np.full(50, lz[0]), color=ROJO, linewidth=1.6)
    ax.set_xlim(*lx); ax.set_ylim(*ly); ax.set_zlim(*lz)
    ax.set_xlabel("Rendimiento del oro (%)", labelpad=3)
    ax.set_ylabel("Rendimiento del tipo de cambio (%)", labelpad=3)
    ax.set_zlabel("Cambio del riesgo país (pbs)", labelpad=3)
    ax.view_init(elev=20, azim=-58)
    ejes_limpios(ax)
    ax.legend(loc="upper left", markerscale=4, frameon=False, title="Días de", fontsize=7.5, title_fontsize=7.5)
    guardar(fig, "figura12_nube3d_rendimientos")
    print(f"Pendiente TC sobre oro (piso de la figura 12): {b[0]:.4f}; días graficados: {int(dentro.sum())}")
else:
    print("Falta", archivo.name, "-> no se genera la figura 12")

# ------------------------------------------------------------------
# TABLA 11. Evidencia textual de los parámetros leídos del informe de la SEC (página y frase literal)
# ------------------------------------------------------------------
NOMBRES = {
    "van_despues_impuestos_musd": "VAN después de impuestos (US$ mm)", "tasa_descuento_pct": "Tasa de descuento (%)",
    "flujo_antes_impuestos_musd": "Flujo antes de impuestos (US$ mm)",
    "flujo_despues_impuestos_musd": "Flujo después de impuestos (US$ mm)",
    "inversion_inicial_musd": "Inversión pendiente (US$ mm)", "costo_cierre_musd": "Costo de cierre (US$ mm)",
    "precio_oro_trs_usd_oz": "Precio del oro (US$/oz)", "aisc_usd_oz": "AISC (US$/oz)",
    "oro_pagable_koz": "Oro pagable (koz)", "produccion_media_koz_anio": "Producción media (koz/año)",
    "vida_mina_anios": "Vida de la mina (años)", "impuesto_renta_pct": "Impuesto a la renta (%)",
}


def tex(texto):
    reemplazos = {"\\": r"\textbackslash{}", "%": r"\%", "$": r"\$", "&": r"\&", "_": r"\_", "#": r"\#",
                  "<": r"$<$", ">": r"$>$", "~": r"$\sim$", "•": r"$\bullet$", "{": r"\{", "}": r"\}"}
    return "".join(reemplazos.get(c, c) for c in str(texto))


ev = pd.read_csv(PROCESADOS / f"parametros_proyecto_{CODIGO}.csv")
filas = [r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{3.6cm}rr>{\raggedright\arraybackslash\itshape}X}",
         r"\toprule", r"Parámetro & Valor & Página & Frase literal del informe (en inglés) \\", r"\midrule"]
for _, f in ev.iterrows():
    frase = " ".join(str(f["frase_literal"]).split())[:115]
    valor = f"{f['valor']:,.2f}".rstrip("0").rstrip(".").replace(",", r"\,")
    filas.append(f"{tex(NOMBRES.get(f['parametro'], f['parametro']))} & {valor} & {int(f['pagina_pdf'])} & "
                 f"\\enquote{{{tex(frase)}\\ldots}} \\\\")
filas += [r"\bottomrule", r"\end{tabularx}"]
(SALIDAS / "tabla11_evidencia_sec.tex").write_text("\n".join(filas) + "\n", encoding="utf-8")
print("Guardada: tabla11_evidencia_sec.tex")
