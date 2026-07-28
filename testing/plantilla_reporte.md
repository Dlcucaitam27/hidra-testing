# Reporte de Pruebas — Formulario HIDRA/ISMR

**Fecha:** [completar]
**Responsable:** [completar]
**Entorno probado:** [local / Streamlit Cloud / URL] — **Mongo:** [nombre de la BD de prueba usada]

## 1. Alcance

- Formulario probado: Individual / Colectivo
- Tipos de prueba realizadas: funcional (casos válidos), límites, negativa (validación), inyección, duplicados OT-TE, concurrencia/carga.
- Herramientas usadas: `generador_datos.py`, `test_apptest_formulario.py`, `carga_directa_mongo.py`, `carga_playwright.py`.

## 2. Resumen ejecutivo

[2-3 párrafos: cuántos casos se probaron en total, tasa de éxito, principales hallazgos, si hubo caídas o errores críticos.]

## 3. Resultados por tipo de prueba

### 3.1 Casos válidos (regresión funcional)
| Total | OK | Rechazados inesperadamente | Crashes |
|---|---|---|---|
| | | | |

### 3.2 Casos límite (bordes)
| Total | Comportamiento esperado | Comportamiento inesperado |
|---|---|---|

### 3.3 Casos negativos (validación de campos obligatorios)
| Total | Rechazados correctamente | Aceptados indebidamente (BUG) |
|---|---|---|

### 3.4 Inyección / payloads maliciosos
| Total | Sanitizados correctamente | Guardados tal cual (revisar) | Crash |
|---|---|---|---|

### 3.5 Duplicados de OT-TE
[¿El índice único de Mongo rechazó correctamente el segundo caso?]

### 3.6 Concurrencia / saturación (Playwright)
| Sesiones simultáneas | Éxitos | Errores | Tiempo promedio de login |
|---|---|---|---|

## 4. Errores y hallazgos detallados

| ID caso | Categoría | Campo/condición | Resultado obtenido | Esperado | Severidad | Evidencia |
|---|---|---|---|---|---|---|
| | | | | | | |

(Severidad sugerida: Crítica = caída de la app / pérdida de datos, Alta = guarda datos inválidos, Media = mensaje de error confuso, Baja = cosmético)

## 5. Capacidad observada

- Casos/segundo insertados directamente en Mongo: [de `resultados_carga_mongo_*.json`]
- Sesiones simultáneas soportadas sin degradación notoria: [de `resultados_playwright.csv`]
- Punto donde empezó a fallar (si aplica): [ ]

## 6. Recomendaciones

[Lista breve de mejoras sugeridas al equipo de desarrollo.]

## 7. Anexos

- `casos_generados.json` — datos de prueba usados
- `reporte_apptest_*.csv` — detalle por caso del formulario
- `resultados_carga_mongo_*.json` — detalle de inserciones directas
- `resultados_playwright.csv` — detalle de sesiones concurrentes
