# INSTRUCCIONES — Kit de pruebas HIDRA/ISMR (para dummies)

Este manual asume que **no** sabes nada de testing automatizado. Sigue los
pasos en orden. No te saltes el paso 0: es el más importante de todos.

Archivos de este kit (todos deben quedar en la carpeta raíz del proyecto,
al lado de `new_app_ismr_sheets.py`):

- `generador_datos.py` — crea los "casos" de prueba (los datos falsos).
- `carga_directa_mongo.py` — mete esos casos directo a la base de datos, sin usar la web. Prueba capacidad.
- `test_apptest_formulario.py` — llena el formulario web de verdad (sin abrir navegador) y detecta errores/caídas.
- `carga_playwright.py` — abre varios navegadores a la vez contra la app publicada, para ver si aguanta usuarios simultáneos.
- `requirements-testing.txt` — lo que hay que instalar.
- `plantilla_reporte.md` — para que armes tu informe final ya con la estructura lista.

---

## PASO 0 — NUNCA pruebes contra la base de datos real (léelo dos veces)

Estos scripts van a crear cientos o miles de "casos" con datos inventados
(nombres falsos, OT-TE falsos, etc.). Si los corres contra la base de datos
de producción, vas a **ensuciar los datos reales** que usan los analistas.

Antes de tocar cualquier script:

1. Entra a MongoDB Atlas (o donde esté alojada la base).
2. Crea una base de datos **nueva**, por ejemplo `ismr_pruebas` (distinta a
   la que usa la app en producción, que probablemente se llama `ismr`).
3. En tu copia local del proyecto, crea el archivo `.streamlit/secrets.toml`
   (si no existe, créalo) con algo así:

   ```toml
   [mongodb]
   uri = "mongodb+srv://usuario:clave@tu-cluster.mongodb.net/"
   db_name = "ismr_pruebas"
   ```

4. Verifica que `db_name` diga `ismr_pruebas` (o el nombre que hayas
   elegido para pruebas), **no** el nombre de producción.

Si no tienes credenciales para crear una base de pruebas, pídeselas a quien
administre el proyecto — no continúes sin esto.

---

## PASO 1 — Instalar lo necesario

Abre una terminal en la carpeta del proyecto (donde está
`new_app_ismr_sheets.py`) y ejecuta, uno por uno:

```bash
pip install -r requirements.txt
pip install -r requirements-testing.txt
playwright install chromium
```

Si algo falla con "pip no reconocido", primero instala Python desde
python.org y marca la casilla "Add to PATH" durante la instalación.

---

## PASO 2 — Crear un usuario analista de prueba

El formulario pide iniciar sesión. Necesitas un usuario real (en tu base
de pruebas) para que los scripts puedan loguearse. Dos formas:

**Opción fácil:** corre la app normalmente contra tu base de pruebas
(`streamlit run new_app_ismr_sheets.py`), entra como administrador y usa la
pantalla "Gestionar Usuarios" para crear un usuario, por ejemplo
`tester.qa` con una contraseña que tú definas. Si te pide cambiar la
contraseña en el primer login, cámbiala tú mismo una vez a mano (los
scripts no saben pasar por esa pantalla).

**Opción rápida (para quien sepa un poco de Python):** usa directamente
`crear_usuario()` de `data/mongo/usuarios_repo.py` en una consola de Python.

Anota el usuario y la contraseña finales: los vas a necesitar en el Paso 4.

---

## PASO 3 — Generar los datos de prueba

Esto NO toca la base de datos ni el formulario todavía, solo crea un
archivo con los casos falsos.

```bash
python generador_datos.py --n-validos 30 --n-borde 10 --n-negativos 25 --n-inyeccion 8
```

Esto crea `casos_generados.json` con 5 grupos de casos:

- `validos` — deberían guardarse sin problema.
- `borde` — valores en el límite (años, edades) para ver si el formulario los maneja bien.
- `negativos` — a cada uno le falta un campo obligatorio distinto; el formulario DEBE rechazarlos.
- `inyeccion` — textos raros/maliciosos en campos libres, para ver si algo se rompe o se guarda sin filtrar.
- `duplicados_ot_te` — dos casos con el mismo OT-TE; el segundo debe ser rechazado.

Ábrelo con cualquier editor de texto si quieres ver cómo lucen los datos.

Los departamentos/municipios usados por defecto (`DEP_MUN_VALIDOS` en
`generador_datos.py`) ya se verificaron contra `data/diccionarios.py`. Si
en el futuro cambian ese diccionario, revisa esa lista de nuevo antes de
confiar en los resultados.

---

## PASO 4 — Probar el formulario de verdad (sin abrir navegador)

Este es el script principal: llena el formulario Individual con cada caso
generado y anota si se guardó, si fue rechazado (y por qué), o si la app
se cayó.

```bash
python test_apptest_formulario.py --usuario tester.qa --password "TU_CLAVE" --archivo casos_generados.json --categoria validos
```

Corre esto **una categoría a la vez**, cambiando `--categoria` por
`validos`, `borde`, `negativos`, `inyeccion`, `duplicados_ot_te`. Cada
corrida genera un archivo `reporte_apptest_<categoria>.csv` — ábrelo en
Excel/Sheets al terminar.

Qué significa cada resultado en la columna `resultado` del CSV:

- `OK` — el caso se guardó correctamente.
- `RECHAZADO_VALIDACION` — el formulario mostró un mensaje de error (revisa la columna `detalle`). Para la categoría `negativos` esto es LO ESPERADO. Si aparece en `validos`, es un bug o tu dato de prueba no es tan válido como pensabas.
- `CRASH` — la app lanzó una excepción no controlada. **Esto siempre es un hallazgo importante**, repórtalo con el `detalle` completo.
- `ERROR_SCRIPT` — el problema fue del script (por ejemplo, no encontró un campo con esa clave). Revisa la columna `avisos_llenado`: probablemente el formulario cambió y una clave (`key=`) ya no coincide. Ver la sección "Si algo no calza" más abajo.
- `INDETERMINADO` — no hubo error ni mensaje de éxito visible; revisa a mano ese caso.

**La primera vez que corras esto, hazlo con `--limite 2`** (solo 2 casos)
para confirmar que todo funciona antes de lanzar la tanda completa de 30+.

```bash
python test_apptest_formulario.py --usuario tester.qa --password "TU_CLAVE" --categoria validos --limite 2
```

### Si algo no calza (los "avisos_llenado" no están vacíos)

El formulario de HIDRA es enorme y algunas claves de campos pueden diferir
ligeramente de lo que este script asume. Si ves avisos como
`No se pudo fijar selectbox 'caso_xxx_individual'`:

1. Abre `front/pages.py` en tu editor.
2. Busca (Ctrl+F) el texto exacto que aparece en pantalla para ese campo
   (por ejemplo "Nivel de Riesgo").
3. Mira la línea `key=f"..."` justo debajo — esa es la clave real.
4. Corrige el nombre en `test_apptest_formulario.py` (están todos juntos en
   la función `rellenar_caso_individual`).

Este script cubre la sección "núcleo" del formulario individual (datos de
OT/TE, demografía, ubicación, riesgo, factores diferenciales). **No** cubre
las secciones de Perfiles, Antecedentes, Hechos, Desplazamientos ni
Verificaciones, porque cada una tiene su propia lógica condicional y
alargaría mucho este kit. Al final del script hay una función
`rellenar_seccion_extra_EJEMPLO` con el patrón exacto para que agregues
esas secciones tú mismo si tu prueba las necesita — es repetir el mismo
truco (buscar la clave, llamar a `_set_selectbox`/`_set_text`/etc.).

---

## PASO 5 — Probar capacidad de la base de datos (sin usar el formulario)

Este script mide qué tan rápido aguanta Mongo si le metes muchos casos de
una, sin pasar por la interfaz. Es la forma más rápida de generar volumen.

```bash
python carga_directa_mongo.py --archivo casos_generados.json --categoria validos
```

Al final imprime algo como:

```
[RESUMEN] 30 casos en 4.12s (7.28 casos/seg)
   OK: 30   Duplicados rechazados: 0   Errores: 0
```

y guarda el detalle en `resultados_carga_mongo_validos.json`. Corre también
con `--categoria duplicados_ot_te` para confirmar que el segundo caso se
rechaza (debe salir `RECHAZADO_DUPLICADO`, no `ERROR`).

---

## PASO 6 — Probar varios usuarios a la vez (saturación real)

Este es el único de los cuatro scripts que necesita la app YA PUBLICADA
(la URL de Streamlit Cloud o donde la tengan corriendo), porque simula
varias personas usándola al mismo tiempo desde fuera.

```bash
python carga_playwright.py --url https://tu-app.streamlit.app --usuarios tester.qa,tester2,tester3 --password "TU_CLAVE" --concurrencia 5 --repeticiones 3
```

- `--usuarios` — lista de usuarios de prueba ya creados (puedes repetir uno
  solo si no quieres crear varios: `--usuarios tester.qa`).
- `--concurrencia` — cuántas "personas" entran al mismo tiempo. Empieza
  bajo (3-5) y ve subiendo (10, 20...) para encontrar el punto donde
  empieza a fallar o a demorarse mucho.
- `--repeticiones` — cuántas veces repetir la tanda completa.

Resultado en `resultados_playwright.csv`: mira la columna `segundos` (si
va subiendo mucho al aumentar la concurrencia, ahí está el límite de
capacidad) y `resultado` (cualquier `ERROR` es una caída o timeout real).

Para ver qué está pasando en vivo la primera vez, agrega `--con-cabeza`
(abre las ventanas del navegador en lugar de ejecutarlas ocultas):

```bash
python carga_playwright.py --url ... --usuarios tester.qa --password "..." --concurrencia 2 --con-cabeza
```

---

## PASO 7 — Armar el reporte

Abre `plantilla_reporte.md`, y ve llenando cada tabla con los números que
sacaste de:

- `reporte_apptest_*.csv` (una fila por caso, con resultado y detalle)
- `resultados_carga_mongo_*.json` (velocidad de inserción, duplicados)
- `resultados_playwright.csv` (comportamiento bajo concurrencia)

La sección "4. Errores y hallazgos detallados" es la más importante: copia
ahí cada fila con `resultado` distinto de lo esperado (un `OK` en
`negativos`, un `CRASH` en cualquier categoría, un `ERROR` en la carga de
Mongo, etc.) — esos son tus bugs reales.

---

## Resumen del orden recomendado

1. Configurar base de pruebas (Paso 0) — **obligatorio, no te lo saltes**.
2. `pip install` de todo (Paso 1).
3. Crear usuario de prueba (Paso 2).
4. `python generador_datos.py ...` (Paso 3).
5. `python test_apptest_formulario.py ... --limite 2` para probar que
   funciona, luego sin `--limite` para la tanda completa (Paso 4).
6. `python carga_directa_mongo.py ...` (Paso 5).
7. `python carga_playwright.py ...` contra la URL publicada (Paso 6).
8. Llenar `plantilla_reporte.md` con todos los resultados (Paso 7).
