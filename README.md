# ISMR Formulario – Documentación Técnica (BETA)

## Descripción del Proyecto

Aplicación web para el **Sistema de Investigación de Múltiples Riesgos
(ISMR)**.

Permite a analistas:

-   Registrar casos de riesgo (individuales y colectivos)
-   Gestionar múltiples hechos de riesgo por caso (multiregistros)
-   Autenticarse mediante login con control de roles
-   Exportar datos en `.xlsx`
-   Importar usuarios desde `.xlsx`
-   Trabajar con guardado temporal ante fallos de conexión

> ⚠️ **Estado del proyecto:** Fase **BETA / PRUEBA**  
> Sistema en etapa de validación funcional y detección de errores antes
> de su versión estable.

------------------------------------------------------------------------

# Stack Tecnológico

-   Python 3.11
-   Streamlit
-   MongoDB
-   pandas
-   openpyxl
-   Arquitectura modular por capas

------------------------------------------------------------------------

# Estructura Actual del Proyecto

    ismr-formulario/
    │
    ├── .devcontainer/
    ├── .idea/
    ├── .streamlit/
    │
    ├── configuration/
    │   ├── __init__.py
    │   └── settings.py
    │
    ├── data/
    │   ├── mongo/
    │   │   ├── __init__.py
    │   │   ├── casos_repo.py
    │   │   └── usuarios_repo.py
    │   │
    │   ├── __init__.py
    │   ├── casos_repo.py
    │   ├── usuarios_repo.py
    │   └── diccionarios.py
    │
    ├── service/
    │   ├── __init__.py
    │   ├── auth_service.py
    │   └── recovery_service.py
    │
    ├── front/
    │   ├── __init__.py
    │   ├── pages.py
    │   └── styles.py
    │
    ├── new_app_ismr_sheets.py
    ├── requirements.txt
    ├── .gitignore
    └── README.md

------------------------------------------------------------------------

# Arquitectura

El sistema sigue una arquitectura por capas:

1.  **Front (Presentación)**  
    Renderizado de vistas, formularios y control de sesión.

2.  **Service (Lógica de Negocio)**  
    Autenticación, validaciones, control de roles y procesamiento de
    datos.

3.  **Data (Persistencia)**  
    Repositorios MongoDB y operaciones CRUD.

4.  **Configuration**  
    Parámetros globales y configuración del entorno.

------------------------------------------------------------------------

# Funcionalidades

## Autenticación

-   Login con usuario y contraseña
-   Hash seguro de contraseñas
-   Roles: Usuario (Analista) y Administrador

## Registro de Casos

-   Casos individuales y colectivos
-   Multiregistro de hechos de riesgo
-   Validación de identificadores únicos
-   Persistencia en MongoDB

## Guardado Temporal

-   Conservación en `session_state`
-   Reintento de guardado ante fallos
-   Minimiza pérdida de información

## Exportación e Importación

-   Exportación de datos en `.xlsx` (solo admin)
-   Importación masiva de usuarios desde `.xlsx`
-   Validación y control de duplicados

## Prellenado desde documento (formato GESP-FT-14 V3)

En el **Formulario Individual**, el panel *📄 Prellenar desde evaluación
de riesgo GESP-FT-14* permite cargar el formato diligenciado en Word
(`.docx`) o PDF (`.pdf`, con texto; sin OCR):

1.  Se extrae la información a un JSON con esquema versionado
    (`service/extraccion_documentos/esquema.py`).
2.  Se muestra qué campos se van a llenar (✅ llenado · ⚠️ revisar · —
    sin dato) y el JSON completo.
3.  Al pulsar **Aplicar al formulario** se llenan los campos y las
    listas (hechos, antecedentes, desplazamientos, verificaciones) y el
    JSON se guarda en la colección MongoDB `extracciones_documentos`
    (el archivo original no se guarda, solo su hash SHA-256).
4.  El analista revisa, completa lo que falte y registra el caso como
    siempre.

Estructura:

    service/extraccion_documentos/
    ├── lectores.py          # Word / PDF -> estructura intermedia común
    ├── mapeo_gesp_ft_14.py  # estructura intermedia -> JSON (por etiquetas, no posiciones)
    ├── esquema.py           # esquema del JSON (VERSION_ESQUEMA)
    ├── prellenado.py        # JSON -> valores del formulario
    └── __main__.py          # CLI de pruebas locales
    data/mongo/extracciones_repo.py

Probar un documento en local sin abrir la app (nada sale del equipo):

``` bash
python -m service.extraccion_documentos evaluacion.pdf             # JSON
python -m service.extraccion_documentos evaluacion.docx --bloques  # estructura intermedia
python -m service.extraccion_documentos ev.docx ev.pdf --comparar  # diferencias Word vs PDF
python -m unittest discover -s tests                               # pruebas (documentos ficticios)
```

------------------------------------------------------------------------

# Ejecución Local

``` bash
pip install -r requirements.txt
streamlit run app_ismr_sheets.py
```

Aplicación disponible en:

http://localhost:8501

------------------------------------------------------------------------

# Estado del Proyecto

🟡 BETA

Sistema en fase de pruebas internas, sujeto a mejoras estructurales y
corrección de errores.

https://ismr-formulario-gqzurmnkdwcynb59a8rq3h.streamlit.app/
