defaults = {
    "autenticado": False, "username": None, "nombre_completo": None,
    "debe_cambiar_password": False, "es_admin": False, "vista": None,
    "hechos": [], "perfiles": [], "antecedentes": [], "perfiles_actuales": [],
    "verificaciones": [], "desplazamientos": []
}

TAB_NOMBRES = {
    "individual": {
        "casos":              "Individual",
        "hechos":             "Hechos_Individual",
        "perfiles":           "Perfiles_Individual",
        "antecedentes":       "Antecedentes_Individual",
        "perfiles_actuales":  "Perfiles_Actuales_Individual",
        "desplazamientos":    "Desplazamientos_Individual",
        "verificaciones":     "Verificaciones_Individual",
        "instancias_comunes": "Instancias_Comunes_Individual",
        "otras_orgs":         "Otras_Orgs_Individual",
    },
    "colectivo": {
        "casos":              "Colectivo",
        "hechos":             "Hechos_Colectivo",
        "perfiles":           "Perfiles_Colectivo",
        "antecedentes":       "Antecedentes_Colectivo",
        "perfiles_actuales":  "Perfiles_Actuales_Colectivo",
        "desplazamientos":    "Desplazamientos_Colectivo",
        "verificaciones":     "Verificaciones_Colectivo",
        "instancias_comunes": "Instancias_Comunes_Colectivo",
        "otras_orgs":         "Otras_Orgs_Colectivo",
    },
}
