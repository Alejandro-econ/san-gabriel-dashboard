# Dashboard San Gabriel — estructura, artículos y pósters

## 1. Estructura del dashboard
Un solo archivo `index.html` (sitio estático, sin servidor) con estas secciones en el menú:

| # | Sección | Qué muestra |
|---|---|---|
| 0 | Portada | Foto de la mina (`mina.jpg`) y acceso a las secciones |
| 1 | Ubicación | Mapa satelital con 3 vistas: general, planta y yacimiento (`sat/`) |
| 2 | Artículos | Biblioteca/estante de libros + catálogo bilingüe "Los 20 artículos" (filtro Ambos / Español / English); cada artículo con botón Leer y PDF en ES y EN, visor de PDF integrado |
| 3 | Pósters | Carrusel tipo exposición con los 20 pósters; descarga en PDF y código LaTeX (.zip) |
| 4 | Resultados | Tablero: 5 tarjetas KPI, distribución con deslizador, gráfico de factores, medidor de margen de precio e hipótesis; selector de escenario y moneda (US$ / Soles) |
| 5 | Journal | Revista para hojear página por página  |
| 6 | Beamer | Vista de presentación  |
| 7 | Mi póster | Sala tipo museo  |

### Carpetas
```
index.html · mina.jpg · LEEME.txt · RESUMEN_PARA_OTRO_CLAUDE.md
sat/        sg_general.jpg · sg_planta.jpg · sg_yacimiento.jpg
lib/        pdf.js 6.2 (visor de PDF)
Producto_Alejandro Soto Antezana/
  Artículos en Ingles_Alejandro Soto Antezana/      Articulo 1.pdf … Articulo 20.pdf
  Artículos traducidos_Alejandro Soto Antezana/     Articulo N Traducido al español.pdf
  Posters de artículos_Alejandro Soto Antezana/     Poster 1.pdf … Poster 20.pdf
  Journal_Alejandro Soto Antezana/                  journal.pdf
  Beamer_Alejandro Soto Antezana/                   beamer.pdf
  Poster del Journal_ Alejandro Soto Antezana/      poster.pdf
  info.json                                         título/autores opcionales
Desarrollo_Alejandro Soto Antezana/
  Template Posters_Alejandro Soto Antezana/         Poster 1.zip … Poster 20.zip (LaTeX)
  Template Journal_Alejandro Soto Antezana/         journal.zip
  Template Beamer_Alejandro Soto Antezana/          beamer.zip
  Template Poster Journal_Alejandro Soto Antezana/  poster.zip
```
Journal, Beamer y Mi póster aparecen solos cuando existe el PDF con ese nombre exacto; el .zip agrega el botón de descarga del LaTeX. Las rutas de artículos y pósters están escritas dentro de `index.html` (objetos `STATIC_DOCS` y `FILEMAP`): si se renombra un archivo o carpeta, hay que actualizar esas rutas.

## 2. Artículos (20, en español e inglés)
- Traducción completa al español en formato de artículo (no de póster), con tablas, ecuaciones y referencias.
- El artículo 11 en español es la traducción entregada por la autora.
- Los originales en inglés se muestran con su título en inglés y su propio botón de lectura.

| N.º | Título en español | Título original (inglés) |
|---|---|---|
| 01 | Nuevos enfoques para evaluar el riesgo de proyectos mediante el método de Monte Carlo | New Approaches to Project Risk Assessment Utilizing the Monte Carlo Method |
| 02 | Marco de decisión basado en riesgo para la minería aurífera a tajo abierto con simulación de Monte Carlo | A Risk-Based Decision Framework for Economic Sustainability in Open-Pit Gold Mining Using Monte Carlo Simulation |
| 03 | Modelo híbrido para la planificación estratégica basada en riesgo en minería a tajo abierto (determinista, estocástico e ISO 31000) | A Hybrid Model for Risk-Based Strategic Planning in Open-Pit Mining: Integrating Deterministic, Stochastic, and ISO 31000 Approaches |
| 04 | Optimización de la ley de corte con incertidumbre geológica en una mina subterránea de oro: un caso real | Cutoff Grade Optimization on Operative Decision Variables with Geological Uncertainty in an Underground Gold Mine: A Real Case Study |
| 05 | Evaluación del riesgo de proyectos de energía renovable en distintas estructuras del mercado eléctrico: revisión sistemática | Project Risk Assessment of Renewable Energy Projects in Electricity Market Structures: A Systematic Literature Review |
| 06 | Cálculo del valor actual neto para la garantía financiera de poscierre minero | Net Present Value Calculations for Mining Post-Closure Financial Assurance |
| 07 | Explotación de recursos minerales con precios volátiles de la energía: análisis técnico-económico de yacimientos de baja calidad | Exploitation of Mineral Resources in Conditions of Volatile Energy Prices: Technical and Economic Analysis of Low-Quality Deposits |
| 08 | Escudos fiscales, costo promedio ponderado del capital y la tasa de descuento para proyectos de vida útil finita | Tax Shields, the Weighted Average Cost of Capital, and the Appropriate Discount Rate for a Project with a Finite Useful Life |
| 09 | La tasa de descuento en la evaluación de la sostenibilidad económico-ambiental de proyectos | The Discount Rate in the Evaluation of Project Economic-Environmental Sustainability |
| 10 | Elasticidad de los retornos del oro al tipo de cambio del dólar en distintas zonas de la tasa de fondos federales | US Dollar Exchange Rate Elasticity of Gold Returns at Different Federal Fund Rate Zones |
| 11 | Análisis de la relación entre los precios del oro, la inflación y el bitcoin en el período posterior a la reducción gradual | Analysis of the relationship of gold prices with inflation and bitcoin in the post-tapering period |
| 12 | ¿Es el oro siempre un activo refugio? | Is gold always a safe haven? |
| 13 | Capacidad de cobertura y refugio del oro y las criptomonedas ante extremos geopolíticos y de mercado | Examining the safe-haven and hedge capabilities of gold and cryptocurrencies: A GARCH and regression quantiles approach in geopolitical and market extremes |
| 14 | ¿Son el bitcoin y el oro activos refugio durante el COVID-19 y la guerra Rusia–Ucrania de 2022? | Are Bitcoin and Gold a Safe Haven during COVID-19 and the 2022 Russia–Ukraine War? |
| 15 | Impacto de la volatilidad del oro, la plata y el bitcoin en el riesgo sistémico bancario: ¿refugio o amplificador? | The Impact of Gold, Silver, and Bitcoin Volatility on Banking Systemic Risk: Safe-Haven or Amplifier? |
| 16 | Volatilidad del tipo de cambio y resiliencia del flujo de caja empresarial: evidencia en mercados emergentes de Oriente Medio y Norte de África | Exchange Rate Volatility and Corporate Cash-Flow Resilience: Firm-Level Evidence from MENA Emerging Markets |
| 17 | Valoración de un bono vinculado a materias primas con rendimiento de conveniencia y volatilidad estocásticos y riesgo de crédito | Valuation of Commodity-Linked Bond with Stochastic Convenience Yield, Stochastic Volatility, and Credit Risk in an Intensity-Based Model |
| 18 | Habilidad de selección y de sincronización en los retornos de los fondos mutuos de bonos: evidencia de simulaciones bootstrap | Selection and Timing Skill in Bond Mutual Fund Returns: Evidence from Bootstrap Simulations |
| 19 | Efectividad del valor en riesgo: un enfoque con datos de alta frecuencia y colas semipesadas | Value-at-Risk Effectiveness: A High-Frequency Data Approach with Semi-Heavy Tails |
| 20 | Análisis y modelación del riesgo sistemático económico y del requerimiento de capital: una simulación de Monte Carlo | Investigation and Modelling of Economic Systematic Risk and Capital Requirement: A Monte Carlo Simulation |

## 3. Pósters (20)
- Un póster por artículo, 1 página, hecho en LaTeX (plantilla `plantilla.tex`).
- Logos en los recuadros: UNCP a la izquierda y Facultad de Economía a la derecha, sin marco blanco.
- Cada póster tiene su PDF y su `.zip` con el código LaTeX y los logos (`logo1.png`, `logo2.png`) para editarlo en Overleaf.
