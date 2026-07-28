# Cómo montar una copia del proyecto (GitHub + MongoDB) para testing

Objetivo: tener una copia 100% independiente de HIDRA — su propio repo de
GitHub y su propia base de datos — para que puedas hacer pruebas de
saturación sin tocar nunca lo que usan los analistas de verdad.

Nota importante de arranque: revisé la carpeta que tienes en tu computador
y **no está conectada a ningún repositorio de GitHub** (no tiene historial
de git). Así que te doy el camino completo desde cero.

---

## PASO 1 — Crear el repositorio nuevo en GitHub

1. Entra a github.com con tu cuenta y da clic en **New repository** (botón verde).
2. Nombre sugerido: `hidra-testing` (o el que prefieras).
3. Márcalo como **Private** — el proyecto maneja datos sensibles de riesgo, no lo dejes público.
4. NO marques "Add a README" ni ".gitignore" (ya los tienes en tu carpeta local). Deja el repo vacío.
5. Da clic en **Create repository**. GitHub te va a mostrar una URL parecida a:
   `https://github.com/TU_USUARIO/hidra-testing.git`
   Cópiala, la vas a necesitar en el paso 2.

---

## PASO 2 — Subir tu carpeta local a ese repositorio

Abre una terminal **en la carpeta del proyecto** (`HIDRA`, donde está
`new_app_ismr_sheets.py`) y ejecuta, una línea a la vez:

```bash
git init
git add .
git status
```

El comando `git status` te muestra qué se va a subir. **Revisa que NO
aparezca** `secrets.toml` en la lista (ya corregí el `.gitignore` para que
lo excluya automáticamente, pero vale la pena verificarlo con tus propios
ojos antes de subir nada — ahí van las credenciales de la base de datos).

Si todo se ve bien, continúa:

```bash
git commit -m "Copia inicial para entorno de testing"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/hidra-testing.git
git push -u origin main
```

Te va a pedir tu usuario y contraseña de GitHub. Si falla el login por
contraseña (GitHub ya no acepta contraseña normal por HTTPS), necesitas un
"Personal Access Token": en GitHub ve a Settings → Developer settings →
Personal access tokens → Generate new token, dale permiso `repo`, cópialo,
y úsalo como si fuera la contraseña cuando `git push` te lo pida.

Al terminar, recarga la página de tu repo en GitHub: deberías ver todos
los archivos del proyecto ahí.

---

## PASO 3 — Crear la base de datos de pruebas en MongoDB

**Opción A — Nuevo cluster gratuito completo (más aislado, recomendado):**

1. Ve a https://www.mongodb.com/cloud/atlas/register y crea una cuenta (o
   inicia sesión si ya tienes una para el proyecto original).
2. Crea un nuevo proyecto, por ejemplo "HIDRA-Testing".
3. Dentro de ese proyecto, crea un cluster gratuito (M0).
4. En "Database Access", crea un usuario nuevo (usuario/contraseña) solo
   para este cluster de pruebas.
5. En "Network Access", agrega `0.0.0.0/0` (permitir desde cualquier IP) —
   solo para pruebas; en producción no se hace así.
6. En "Database" → "Connect" → "Drivers", copia la cadena de conexión, algo
   como:
   `mongodb+srv://usuario:clave@tu-cluster.mongodb.net/?retryWrites=true&w=majority`

**Opción B — Mismo cluster que producción, pero base de datos separada
(más simple, pero comparte el mismo cluster físico):**

Usa la misma URI del cluster de producción, pero cambia el nombre de la
base (`db_name`) a algo como `ismr_pruebas` en el paso 4. Así los datos
quedan separados aunque compartan servidor.

---

## PASO 4 — Conectar tu copia del proyecto a esa base de pruebas

En tu carpeta local del proyecto (la misma que subiste a GitHub), crea el
archivo `.streamlit/secrets.toml` (no existe todavía) con este contenido,
reemplazando por tus datos reales:

```toml
[mongodb]
uri = "mongodb+srv://usuario:clave@tu-cluster.mongodb.net/?retryWrites=true&w=majority"
db_name = "ismr_pruebas"
```

Este archivo **nunca se sube a GitHub** (ya está en `.gitignore`) — cada
persona que trabaje con el proyecto crea el suyo localmente, o lo configura
directamente en Streamlit Cloud (ver Paso 6).

Prueba que conecta corriendo la app localmente:

```bash
pip install -r requirements.txt
streamlit run new_app_ismr_sheets.py
```

Si abre sin errores de conexión, ya está apuntando a tu base de pruebas.

---

## PASO 5 — (Opcional) Copiar datos reales a la base de pruebas

Si quieres que la copia de pruebas tenga datos parecidos a los reales (en
vez de empezar vacía), usa el script `clonar_datos_mongo.py` que te dejé
junto a este manual — **una sola vez**, antes de generar casos falsos:

```bash
pip install pymongo
python clonar_datos_mongo.py --uri-origen "URI_DE_PRODUCCION" --uri-destino "URI_DE_PRUEBAS" --confirmar
```

El script te pide confirmación escrita ("SI") antes de copiar nada, y se
detiene solo si detecta que origen y destino son la misma URI (para que no
puedas arruinar producción por accidente). Si no tienes o no quieres usar
datos reales, sáltate este paso — la base vacía funciona perfectamente
para las pruebas del kit de testing.

---

## PASO 6 — (Opcional) Publicar la copia en Streamlit Cloud

Solo necesario si quieres correr `carga_playwright.py` contra una URL
pública, en vez de tu máquina local:

1. Ve a https://share.streamlit.io e inicia sesión con GitHub.
2. Clic en **New app**.
3. Elige el repositorio `hidra-testing` que creaste en el Paso 1, rama `main`,
   archivo principal `new_app_ismr_sheets.py`.
4. Antes de darle "Deploy", ve a "Advanced settings" → "Secrets" y pega ahí
   el mismo contenido que pusiste en tu `secrets.toml` local (Paso 4).
5. Dale Deploy. En unos minutos te da una URL pública — esa es la que usas
   en `carga_playwright.py --url ...`.

---

## Checklist final

- [ ] Repo nuevo en GitHub, privado, con todo el código subido.
- [ ] `secrets.toml` NO aparece en el repo de GitHub (verificado a simple vista).
- [ ] Cluster/base de Mongo de pruebas creado, separado de producción.
- [ ] `.streamlit/secrets.toml` local apunta a la base de pruebas (`db_name` distinto al de producción).
- [ ] La app abre localmente sin errores de conexión.
- [ ] (Opcional) Datos clonados de producción a pruebas, una sola vez.
- [ ] (Opcional) App publicada en Streamlit Cloud con los secrets de pruebas cargados ahí.

Con esto ya tienes el entorno espejo listo para usar el kit de testing
(`testing/INSTRUCCIONES.md`) sin ningún riesgo para los datos reales.
