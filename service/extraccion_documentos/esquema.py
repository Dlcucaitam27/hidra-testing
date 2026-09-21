"""
Esquema objetivo del JSON extraído del formato GESP-FT-14 (V3)
"Evaluación de Riesgo – Ruta individual para la MTSP".

Es la ÚNICA definición de la estructura de salida: el mapeo parte siempre de
`documento_vacio()`, así que todo JSON producido tiene exactamente estas
claves aunque el documento venga incompleto.

Tipos de hoja:
    "texto"   -> str ("" si no se encontró o está vacío)
    "fecha"   -> str ISO "AAAA-MM-DD" o None
    "si_no"   -> "SI" | "NO" | None (None = no marcado / no encontrado)
    "lista"   -> list[str] (opciones marcadas con X)
    [ {...} ] -> lista de registros con la estructura indicada

Cambie VERSION_ESQUEMA cada vez que se agregue, quite o renombre un campo.
"""
import copy

FORMATO = "GESP-FT-14"
VERSION_FORMATO = "V3"
VERSION_ESQUEMA = "1.0"

_IMPACTO_ESFERA = {"items": {}, "otro_cual": "texto", "sinopsis": "texto"}

ESQUEMA = {
    "informacion_general": {
        "fecha_asignacion_ot": "fecha",
        "fecha_remision_calidad": "fecha",
        "numero_ot": "texto",
        "tipo_evaluacion": "texto",
    },
    "datos_personales": {
        "tipo_documento": "texto",            # "CÉDULA DE CIUDADANÍA" | "OTRO" | ""
        "tipo_documento_cual": "texto",
        "numero_identificacion": "texto",
        "primer_nombre": "texto",
        "segundo_nombre": "texto",
        "primer_apellido": "texto",
        "segundo_apellido": "texto",
        "enfoque_diferencial": "texto",
    },
    "solicitante": {
        "fecha_solicitud": "fecha",
        "solicitante": "texto",
        "tipo_evaluacion": "texto",
        "sinopsis": "texto",
    },
    "antecedentes": {
        "registros": [{
            "ot": "texto", "tramite_emergencia": "texto", "tipo_estudio": "texto",
            "nivel_riesgo": "texto", "recomendacion_medidas": "texto",
            "resumen": "texto", "resolucion": "texto",
        }],
        "sinopsis": "texto",
    },
    "perfil_antiguo": {
        "familiar_ppr": {"nombre": "texto", "tipo_vinculo": "texto", "sinopsis": "texto"},
        "persona_reincorporacion": {
            "fecha_ingreso_farc": "texto", "zona_operacion": "texto",
            "columna_frente_movil": "texto", "bloque": "texto", "nombre_mando": "texto",
            "seudonimo": "texto", "rol": "texto", "actividad": "texto",
        },
        "privacion_libertad": [{
            "establecimiento": "texto", "ubicacion": "texto",
            "anio_captura": "texto", "anio_libertad": "texto",
        }],
        "delitos_y_actividades": [{"delito": "texto", "actividad": "texto"}],
        "sinopsis": "texto",
    },
    "perfil_actual": {
        "demografia": {
            "edad_actual": "texto", "departamento_residencia": "texto",
            "municipio_residencia": "texto", "zona_rural_urbana": "texto",
            "zona_reserva_campesina": "texto", "resguardo_indigena": "texto",
            "nivel_escolaridad": "texto",
        },
        "enfoque_diferencial": [{"enfoque": "texto", "descripcion": "texto"}],
        "grupo_familiar": [{
            "nombres": "texto", "edad": "texto", "vinculo": "texto", "lugar_residencia": "texto",
        }],
        "actividades_economicas": {
            "fuente_ingresos": "texto", "empleado": "texto", "persona_proteccion": "texto",
            "proyecto_productivo_arn": "texto", "proyecto_activo": "texto",
            "motivo_no_activo": "texto", "actividad_economica_proyecto": "texto",
            "proyecto_colectivo_individual": "texto", "vinculado_org_gremial": "texto",
            "nombre_org_gremial": "texto", "reside_lugar_proyecto": "texto",
        },
        "actividades_politicas_sociales": {
            "participa_toar_ubpd_desminado_pnis": "texto", "cual": "texto",
            "comparece_jep": "texto", "tipo_comparecencia": "lista",
            "victima_jep": "texto", "macrocaso_jep": "texto",
            "pertenece_organizacion": "texto", "nombre_colectividad": "texto",
            "naturaleza_colectividad": "texto", "rol_colectividad": "texto",
            "actividades_colectividad": "texto", "escala_actividades": "texto",
            "cargo_eleccion_popular": "texto", "cargo_eleccion_cual": "texto",
        },
        "desplazamientos": [{
            "origen": "texto", "destino": "texto", "tipo_estado_via": "texto",
            "medio_transporte": "texto", "horarios": "texto", "frecuencia": "texto",
            "motivo": "texto",
        }],
    },
    "hechos_riesgo": {
        "registros": [{
            "numero": "texto", "dia": "texto", "mes": "texto", "anio": "texto",
            "departamento": "texto", "municipio": "texto",
            "tipo_actor": "lista", "nombre_actor": "texto", "victima": "texto",
            "medio": "texto", "tipo_hecho": "lista", "motivacion": "texto",
            "relato": "texto", "nexo_causal": "si_no",
        }],
        "observaciones": "texto",
    },
    "verificaciones": [{
        "numero": "texto", "fuentes": "lista", "nombre_fuente": "texto", "sinopsis": "texto",
    }],
    "vulnerabilidades_capacidades": "texto",
    "impacto_consecuencial": {
        "economica": copy.deepcopy(_IMPACTO_ESFERA),
        "social": copy.deepcopy(_IMPACTO_ESFERA),
        "politico_institucional": copy.deepcopy(_IMPACTO_ESFERA),
        "salud_bienestar": copy.deepcopy(_IMPACTO_ESFERA),
    },
    "contexto_orden_publico": "texto",
    "alertas_tempranas": "texto",
    "medidas_emergencia": "texto",
    "medidas_proteccion_vigentes": "texto",
    "nivel_riesgo": "texto",
    "conclusion": "texto",
    "modificaciones_premesa": "texto",
    "analista": {
        "nombres_apellidos": "texto", "documento": "texto", "cargo": "texto", "correo": "texto",
    },
}

# Campos sin los cuales el resultado casi seguro no corresponde a un formato válido.
# No bloquean la extracción: se reportan como advertencias.
CAMPOS_RECOMENDADOS = [
    ("informacion_general", "numero_ot"),
    ("datos_personales", "numero_identificacion"),
    ("datos_personales", "primer_nombre"),
    ("datos_personales", "primer_apellido"),
]

_DEFECTOS = {"texto": "", "fecha": None, "si_no": None, "lista": []}


def documento_vacio() -> dict:
    """Estructura completa con valores por defecto (listas de registros vacías)."""
    def construir(nodo):
        if isinstance(nodo, dict):
            return {k: construir(v) for k, v in nodo.items()}
        if isinstance(nodo, list):
            return []
        return copy.deepcopy(_DEFECTOS[nodo])
    return construir(ESQUEMA)


def validar(documento: dict) -> list[str]:
    """Devuelve una lista de problemas encontrados (vacía si todo está bien)."""
    problemas = []

    def revisar(nodo, valor, ruta):
        if isinstance(nodo, dict):
            if not isinstance(valor, dict):
                problemas.append(f"{ruta}: se esperaba un objeto")
                return
            # "items" de impacto es un diccionario libre clave -> si_no
            if not nodo:
                return
            for k, sub in nodo.items():
                if k not in valor:
                    problemas.append(f"{ruta}.{k}: falta el campo")
                else:
                    revisar(sub, valor[k], f"{ruta}.{k}")
        elif isinstance(nodo, list):
            if not isinstance(valor, list):
                problemas.append(f"{ruta}: se esperaba una lista")
                return
            for i, reg in enumerate(valor):
                revisar(nodo[0], reg, f"{ruta}[{i}]")
        elif nodo == "texto" and not isinstance(valor, str):
            problemas.append(f"{ruta}: se esperaba texto")
        elif nodo == "fecha" and valor is not None and not (isinstance(valor, str) and len(valor) == 10):
            problemas.append(f"{ruta}: fecha inválida '{valor}'")
        elif nodo == "si_no" and valor not in (None, "SI", "NO"):
            problemas.append(f"{ruta}: valor SI/NO inválido '{valor}'")
        elif nodo == "lista" and not isinstance(valor, list):
            problemas.append(f"{ruta}: se esperaba una lista")

    revisar(ESQUEMA, {k: v for k, v in documento.items() if k != "_meta"}, "$")
    for seccion, campo in CAMPOS_RECOMENDADOS:
        if not documento.get(seccion, {}).get(campo):
            problemas.append(f"{seccion}.{campo}: vacío (campo recomendado)")
    return problemas
