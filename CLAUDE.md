# ISMR Formulario - Guía para Claude

## Descripción del Proyecto

Aplicación web para el **Sistema de Investigación de Múltiples Riesgos (ISMR)**. Permite a analistas registrar, gestionar y visualizar casos de riesgo individuales y colectivos, almacenando los datos en Google Sheets.

## Stack Tecnológico

- **Python 3.11**
- **Streamlit 1.31.0** — framework de UI web
- **gspread 5.12.0** — cliente de Google Sheets
- **google-auth 2.23.4** — autenticación con Service Account de Google
- **pandas 2.1.4** — manipulación de datos

## Estructura del Proyecto

```
ismr-formulario/
├── app_ismr_sheets.py      # Aplicación principal (monolítica)
├── requirements.txt        # Dependencias Python
├── .devcontainer/
│   └── devcontainer.json   # Config para GitHub Codespaces (Python 3.11, puerto 8501)
├── configuration/          # Reservado para configuraciones futuras
├── data/                   # Reservado para datos locales
├── front/                  # Reservado para assets frontend
├── service/                # Reservado para módulos de servicio
└── .gitignore
```

## Cómo Ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app_ismr_sheets.py
```

La app corre en `http://localhost:8501`.

## Configuración de Secretos

Las credenciales de Google se gestionan vía **Streamlit Secrets**. No hay archivos `.env`.

Para desarrollo local, crear `.streamlit/secrets.toml`:

```toml
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
# ... resto de campos del service account
```

Para producción (Streamlit Cloud), configurar los secretos desde el dashboard.

## Arquitectura de la Aplicación

### Flujo Principal

```
main()
  ├── No autenticado → login_page()
  ├── Primer login  → pantalla_cambiar_password()
  ├── Admin         → menú completo (formularios + visualización + gestión de usuarios)
  └── Analista      → formularios de casos únicamente
```

### Módulos Funcionales (dentro de `app_ismr_sheets.py`)

| Función | Responsabilidad |
|---------|----------------|
| `conectar_sheet_usuarios()` | Conexión a hoja de usuarios `ISMR_Usuarios` |
| `verificar_credenciales()` | Login con hash SHA256 |
| `crear_usuario()` / `actualizar_password()` | CRUD de usuarios |
| `conectar_sheet_casos(tipo)` | Conexión a hoja de casos (individual/colectivo) |
| `formulario_casos(tipo)` | Formulario de ingreso de casos y hechos de riesgo |
| `panel_visualizacion()` | Dashboard de análisis y filtrado (solo admin) |
| `panel_gestion_usuarios()` | Gestión de analistas (solo admin) |

### Google Sheets Utilizados

| Spreadsheet | Hojas |
|-------------|-------|
| `ISMR_Usuarios` | Usuarios y credenciales |
| `ISMR_Casos` | `Individual`, `Hechos_Individual`, `Colectivo`, `Hechos_Colectivo` |

### Session State Keys

```python
st.session_state["autenticado"]           # bool
st.session_state["username"]              # str
st.session_state["nombre_completo"]       # str
st.session_state["debe_cambiar_password"] # bool
st.session_state["es_admin"]              # bool
st.session_state["vista"]                 # None | "individual" | "colectivo"
st.session_state["hechos"]               # list[dict] — hechos de riesgo del caso actual
```

## Convenciones y Patrones

- **Idioma del código**: español (nombres de funciones, variables, mensajes UI)
- **Contraseñas**: almacenadas como hash SHA256
- **IDs de caso**: formato `OT-TE` único por caso, validado contra existentes
- **Hojas dinámicas**: si una hoja no existe, se crea automáticamente con cabeceras
- **Exportación**: CSV con timestamp disponible en panel de visualización
- **Estilo**: tema oscuro con fuentes Bebas Neue y DM Sans, CSS inyectado via `st.markdown`

## Roles de Usuario

| Rol | Permisos |
|-----|---------|
| Analista | Ingresar casos (individual/colectivo) |
| Administrador | Todo lo anterior + visualización completa + gestión de usuarios |

## Comandos Útiles

```bash
# Ver dependencias instaladas
pip list

# Actualizar requirements.txt tras instalar nueva dependencia
pip freeze > requirements.txt

# Ejecutar con recarga automática (modo desarrollo)
streamlit run app_ismr_sheets.py --server.runOnSave true
```

## Notas para Desarrollo

- El archivo `app_ismr_sheets.py` es **monolítico**. Si crece, considerar refactorizar en módulos bajo `service/`.
- Los directorios `configuration/`, `data/`, `front/` y `service/` están vacíos y reservados para expansión futura.
- No agregar lógica de negocio en el archivo principal sin considerar moverla a `service/`.
- Evitar hardcodear credenciales; siempre usar `st.secrets`.
