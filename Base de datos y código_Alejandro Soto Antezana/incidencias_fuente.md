# Registro de incidencias de las fuentes

Este archivo registra cualquier bloqueo o ajuste de las fuentes (numeral 2.4.3 de la consigna).

| Fecha y hora (Lima) | Fuente y URL | Código HTTP | robots.txt | Qué pasó | Qué se hizo |
|---|---|---|---|---|---|
| 2026-10-17 07:50 | SPDR Gold Shares: `https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv` | 200 | Permitido | La ruta respondió con un PDF de 120 páginas (lista de lingotes del día, «Client Gold Stock Holdings»), no con el historial diario. El script 03 no encontró la columna de toneladas | Se revisó la página oficial `https://www.spdrgoldshares.com/usa/gld/`. El botón «Download» del «Historical Archive» apunta a `https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en` (Excel). Se actualizó el script 02 a esa ruta. Es la misma fuente y el mismo portal, así que no hay sustitución de fuente |
| 2026-10-17 08:07 | SPDR Gold Shares: `https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en` | NO_PERMITIDO (el script no descargó) | `https://api.spdrgoldshares.com/robots.txt` no permite la ruta (registrado a las 08:07:29 y 08:09:55 en `log_ejecucion.txt`) | El archivo `robots.txt` del portal prohíbe el acceso automatizado a la ruta del archivo histórico | Se respetó la prohibición y no se descargó el archivo. La demanda de inversión pasó a medirse con el monto negociado diario del fondo GLD (Yahoo Finance, vía API). Para cumplir la vía 2 se agregó la descarga programática del archivo CSV de la serie DGS10 de FRED (robots.txt permitido, 08:22:38). El docente indicó seguir con este cambio |

## Ajustes conocidos de las fuentes (no son bloqueos)

1. **BCRP:** los días sin dato aparecen como `n.d.` (feriados en Perú o en Londres). No se rellenan: el script 03 solo usa los días en que todas las fuentes tienen dato real.
2. **Yahoo Finance (GLD):** el precio de cierre (`Close`) no se ajusta por dividendos porque el fondo GLD no reparte dividendos ni ha tenido splits. Se descarga con `auto_adjust=False`.
3. **FRED (DGS10):** los días sin dato (feriados en EE. UU.) aparecen vacíos o con un punto. No se imputan: el script 03 solo usa los días con dato real en todas las fuentes.
5. **Dónde están los datos:** el repositorio de código no incluye `datos_crudos/` ni `datos_procesados/` (los excluye `.gitignore`). Esos archivos, sin editar, están publicados en la Carpeta N.º 3 del repositorio `https://github.com/Alejandro-econ/san-gabriel-dashboard`, que el docente revisa en el dashboard `https://alejandro-econ.github.io/san-gabriel-dashboard/`. Cualquiera puede además regenerarlos ejecutando los scripts.
4. **Informe técnico de la SEC:** el informe (fecha efectiva 31/12/2024) presenta pequeñas diferencias internas, por ejemplo una vida de mina de 14.0, 14.2 o 14.6 años según la sección. Se usa el valor que alimenta el análisis económico (14.2 años, sección 1.2.1.1) y se redondea a 14 años de producción.
