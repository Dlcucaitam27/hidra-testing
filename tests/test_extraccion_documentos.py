"""
Pruebas de la extracción GESP-FT-14 con documentos FICTICIOS (tests/fixtures).

    python -m unittest discover -s tests -v

Cuando se calibre con documentos reales, NO se agregan aquí: se prueban en
local con `python -m service.extraccion_documentos archivo --comparar`.
"""
import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from service.extraccion_documentos import ErrorLectura, extraer_documento  # noqa: E402
from service.extraccion_documentos.esquema import documento_vacio, validar  # noqa: E402
from service.extraccion_documentos.mapeo_gesp_ft_14 import mapear, parsear_fecha  # noqa: E402
from service.extraccion_documentos.texto import elegir_opcion, norm, separar_marca  # noqa: E402

FIXTURES = RAIZ / "tests" / "fixtures"


def _extraer(nombre):
    ruta = FIXTURES / nombre
    return extraer_documento(ruta.name, ruta.read_bytes())


class TestTexto(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(norm("  Número de\nIdentificación "), "numero de identificacion")

    def test_separar_marca(self):
        self.assertEqual(separar_marca("X GAO-R"), ("gao-r", True))
        self.assertEqual(separar_marca("GAO-R"), ("gao-r", False))

    def test_elegir_opcion(self):
        opciones = ["Seleccione...", "PLANADAS", "CHAPARRAL", "SAN JOSÉ DE CÚCUTA"]
        self.assertEqual(elegir_opcion("planadas", opciones), "PLANADAS")
        self.assertEqual(elegir_opcion("Cúcuta", opciones), "SAN JOSÉ DE CÚCUTA")
        self.assertIsNone(elegir_opcion("Ibagué", opciones))

    def test_parsear_fecha(self):
        self.assertEqual(parsear_fecha("10/01/2026"), "2026-01-10")
        self.assertEqual(parsear_fecha("2026-01-10"), "2026-01-10")
        self.assertEqual(parsear_fecha("10 de enero de 2026"), "2026-01-10")
        self.assertIsNone(parsear_fecha("31/02/2026"))


class TestEsquema(unittest.TestCase):
    def test_documento_vacio_cumple_esquema(self):
        problemas = validar(documento_vacio())
        self.assertTrue(all("recomendado" in p for p in problemas), problemas)

    def test_documento_ajeno(self):
        datos, adv = mapear([{"tipo": "texto", "texto": "Acta de reunión"}])
        self.assertTrue(any("no parece" in a for a in adv))
        self.assertEqual(datos["hechos_riesgo"]["registros"], [])

    def test_extension_no_soportada(self):
        with self.assertRaises(ErrorLectura):
            extraer_documento("archivo.xlsx", b"")


class _CasosComunes:
    """Aserciones que deben cumplirse igual en Word y en PDF."""
    archivo = None

    @classmethod
    def setUpClass(cls):
        cls.d = _extraer(cls.archivo)

    def test_sin_problemas_de_esquema(self):
        self.assertEqual(self.d["_meta"]["advertencias"], [])

    def test_informacion_general(self):
        ig = self.d["informacion_general"]
        self.assertEqual(ig["numero_ot"].replace(" ", ""), "OT-2026-0457")
        self.assertEqual(ig["fecha_asignacion_ot"], "2026-02-05")
        self.assertEqual(ig["fecha_remision_calidad"], "2026-03-20")
        self.assertEqual(ig["tipo_evaluacion"], "REEVALUACIÓN POR HECHOS SOBREVINIENTES")

    def test_datos_personales(self):
        dp = self.d["datos_personales"]
        self.assertEqual(dp["tipo_documento"], "CÉDULA DE CIUDADANÍA")
        self.assertEqual(dp["numero_identificacion"], "1.234.567.890")
        self.assertEqual((dp["primer_nombre"], dp["segundo_nombre"]), ("PEDRO", "ANDRÉS"))
        self.assertEqual((dp["primer_apellido"], dp["segundo_apellido"]), ("PÉREZ", "GÓMEZ"))

    def test_solicitante(self):
        so = self.d["solicitante"]
        self.assertEqual(so["fecha_solicitud"], "2026-01-10")
        self.assertEqual(so["solicitante"], "A nombre propio")
        self.assertIn("llamada telefónica", so["sinopsis"])

    def test_perfiles(self):
        self.assertEqual(self.d["perfil_antiguo"]["persona_reincorporacion"]["seudonimo"], "El Profe")
        demo = self.d["perfil_actual"]["demografia"]
        self.assertEqual((demo["departamento_residencia"], demo["municipio_residencia"]), ("Tolima", "Planadas"))
        self.assertEqual(demo["zona_reserva_campesina"], "Si")
        self.assertEqual(demo["nivel_escolaridad"], "Bachiller")
        familia = self.d["perfil_actual"]["grupo_familiar"]
        self.assertEqual([m["edad"] for m in familia], ["45", "15", "72"])
        self.assertEqual(self.d["perfil_actual"]["actividades_politicas_sociales"]["tipo_comparecencia"],
                         ["MÁXIMO RESPONSABLE"])

    def test_desplazamientos(self):
        (desp,) = self.d["perfil_actual"]["desplazamientos"]
        self.assertEqual(desp["origen"], "Planadas, Tolima")
        self.assertEqual(desp["frecuencia"], "Una vez al mes")
        self.assertEqual(desp["motivo"], "Laboral")

    def test_hechos(self):
        h1, h2 = self.d["hechos_riesgo"]["registros"]
        self.assertEqual((h1["dia"], h1["mes"], h1["anio"]), ("12", "01", "2026"))
        self.assertEqual(h1["tipo_actor"], ["GAO-R"])
        self.assertEqual(h1["tipo_hecho"], ["DIRECTA"])
        self.assertEqual(h1["nexo_causal"], "SI")
        self.assertEqual((h2["dia"], h2["municipio"]), ("", "Chaparral"))
        self.assertEqual(h2["tipo_actor"], ["OTRO"])
        self.assertEqual(h2["motivacion"], "Estigmatización")
        self.assertEqual(h2["nexo_causal"], "NO")
        self.assertIn("Fiscalía", self.d["hechos_riesgo"]["observaciones"])

    def test_verificaciones(self):
        v1, v2 = self.d["verificaciones"]
        self.assertEqual(v1["fuentes"], ["TERCEROS"])
        self.assertEqual(v2["fuentes"], ["INSTITUCIÓN DEL ESTADO COLOMBIANO"])
        self.assertEqual(v2["sinopsis"], "La fuente 2 confirma los hechos narrados por el evaluado.")

    def test_impacto(self):
        imp = self.d["impacto_consecuencial"]
        self.assertEqual(imp["economica"]["items"]["dependencia"], "SI")
        self.assertEqual(imp["economica"]["items"]["iniciativas"], "NO")
        self.assertEqual(imp["politico_institucional"]["items"]["estigmatizacion"], "SI")
        self.assertEqual(imp["salud_bienestar"]["items"]["desescolarizacion"], "NO")
        self.assertIsNone(imp["social"]["items"]["redes"])

    def test_textos_libres(self):
        self.assertEqual(self.d["nivel_riesgo"], "EXTRAORDINARIO")
        self.assertIn("disidencias", self.d["contexto_orden_publico"])
        self.assertEqual(self.d["vulnerabilidades_capacidades"],
                         "Vive en zona rural dispersa con baja presencia institucional.")
        self.assertEqual(self.d["analista"]["correo"], "analista.prueba@ejemplo.gov.co")


class TestWord(_CasosComunes, unittest.TestCase):
    archivo = "gesp_ft_14_ficticio.docx"

    def test_antecedentes_completos(self):
        (a,) = self.d["antecedentes"]["registros"]
        self.assertEqual(a["ot"], "OT-2024-0123")
        self.assertEqual(a["resolucion"], "Res. 0456 de 2024")


class TestPdf(_CasosComunes, unittest.TestCase):
    archivo = "gesp_ft_14_ficticio.pdf"


class TestPlantillaVacia(unittest.TestCase):
    """El formato sin diligenciar no debe producir ningún valor (sin falsos positivos)."""

    def _campos_con_valor(self, nombre):
        from service.extraccion_documentos.__main__ import _aplanar
        d = _extraer(nombre)
        return [(k, v) for k, v in _aplanar({k: v for k, v in d.items() if k != "_meta"})
                if v not in ("", None, [], {})]

    def test_word_vacio(self):
        self.assertEqual(self._campos_con_valor("gesp_ft_14_vacio.docx"), [])

    def test_pdf_vacio(self):
        self.assertEqual(self._campos_con_valor("gesp_ft_14_vacio.pdf"), [])


class TestPrellenado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from service.extraccion_documentos.prellenado import construir_prellenado
        cls.p = construir_prellenado(_extraer("gesp_ft_14_ficticio.docx"), "individual")

    def test_valores_basicos(self):
        v = self.p["valores"]
        self.assertEqual(v["caso_ot_anio_individual"], 2026)
        self.assertEqual(v["caso_ot_numero_individual"], 457)
        self.assertEqual(v["caso_solicitante_individual"], "A NOMBRE PROPIO")
        self.assertEqual((v["p_departamento_individual"], v["p_municipio_individual"]), ("TOLIMA", "PLANADAS"))
        self.assertEqual(v["caso_nivel_riesgo_individual"], "EXTRAORDINARIO")
        self.assertEqual(v["imp_eco_iniciativas_individual"], "NO REPORTA")

    def test_nucleo_familiar(self):
        v = self.p["valores"]
        self.assertEqual(v["caso_num_personas_individual"], 3)
        self.assertEqual(v["caso_hijos_menores_individual"], 1)
        self.assertEqual(v["caso_adultos_mayores_individual"], 1)
        self.assertEqual(v["caso_companero_individual"], "SI")

    def test_valores_son_opciones_validas(self):
        from data.diccionarios import _IMPACTO_SI_NR, _MUNICIPIOS, _SI_NO, _SI_NO_REPORTA
        v = self.p["valores"]
        self.assertIn(v["p_municipio_individual"], _MUNICIPIOS[v["p_departamento_individual"]])
        self.assertIn(v["caso_zona_rural_individual"], _SI_NO_REPORTA)
        self.assertIn(v["caso_companero_individual"], _SI_NO)
        for k, val in v.items():
            if k.startswith("imp_"):
                self.assertIn(val, _IMPACTO_SI_NR, k)

    def test_listas(self):
        l = self.p["listas"]
        self.assertEqual(l["hechos"][0]["fecha"], "2026-01-12")
        self.assertEqual(l["hechos"][1]["fecha"], "2025-11")
        self.assertEqual(l["hechos"][0]["tipo_actor"], "GAO R - GRUPO ARMADO ORGANIZADO RESIDUAL")
        self.assertEqual(l["hechos"][0]["tipo"], "")  # el formato no lo trae: lo elige el analista
        d = l["desplazamientos"][0]
        self.assertEqual((d["motivo"], d["frecuencia"], d["tipo_via"], d["medios_transporte"]),
                         ("LABORAL", "1 vez al mes", "TERCIARIA", "MOTO"))
        self.assertEqual((d["dep_destino"], d["mun_destino"]), ("TOLIMA", "IBAGUÉ"))
        self.assertEqual(l["verificaciones"][1]["fuente"], "INSTITUCION DEL ESTADO COLOMBIANO")
        self.assertEqual(l["antecedentes"][0]["anio_resolucion"], "2024")


if __name__ == "__main__":
    unittest.main()
