"""
SICONE - Módulo de Conciliación Financiera
==========================================

PROPÓSITO:
----------
Verificar la precisión del modelo SICONE comparando proyecciones vs realidad bancaria.
Permite documentar ajustes y calcular diferencias residuales para validación pre-go-live
y conciliaciones mensuales posteriores.

FUNCIONALIDADES:
----------------
1. Extracción de datos proyectados desde JSON consolidado
2. Comparación con saldos reales de Fiducuenta y Cuenta Bancaria
3. Registro estructurado de ajustes (proyectos anteriores, préstamos, etc.)
4. Cálculo de diferencias residuales y métricas de precisión
5. Validaciones automáticas de coherencia

DISEÑO PARA MIGRACIÓN A ODOO:
------------------------------
Este módulo está diseñado con Python puro (sin dependencias de Streamlit)
para facilitar migración futura a Odoo.

AUTOR: Andrés
FECHA: Enero 2025
VERSIÓN: 1.0 MVP
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class SaldosCuenta:
    """
    Representa saldos de una cuenta bancaria.
    
    ODOO MIGRATION:
    ---------------
    Se convertirá en models.Model con campos Many2one a conciliacion_id
    """
    nombre: str
    saldo_inicial: float
    saldo_final: float
    fuente: str = "Manual"
    
    def movimiento_neto(self) -> float:
        """Calcula movimiento neto del período"""
        return self.saldo_final - self.saldo_inicial
    
    def to_dict(self) -> dict:
        """Para serialización JSON"""
        return asdict(self)


@dataclass
class Ajuste:
    """
    Representa un ajuste de conciliación.
    
    Estos son movimientos que existieron en la realidad pero no están
    modelados en SICONE (o viceversa), que explican diferencias entre
    proyección y realidad.
    """
    fecha: str
    cuenta: str  # 'Fiducuenta', 'Cuenta Bancaria', 'Ambas'
    categoria: str
    concepto: str
    monto: float
    tipo: str  # 'Ingreso' o 'Egreso'
    evidencia: str = ""
    observaciones: str = ""
    
    # Categorías disponibles (para validación)
    CATEGORIAS_VALIDAS = [
        "Proyectos anteriores (pre-SICONE)",
        "Préstamos empleados - Desembolso",
        "Préstamos empleados - Recuperación",
        "Movimientos internos entre cuentas",
        "Gastos no modelados",
        "Ingresos no modelados",
        "Ajuste de timing",
        "Otro"
    ]
    
    def to_dict(self) -> dict:
        """Para serialización JSON"""
        return asdict(self)
    
    def validar(self) -> Tuple[bool, str]:
        """
        Valida que el ajuste sea coherente.
        
        En Odoo, esto se implementaría como @api.constrains
        """
        if self.categoria not in self.CATEGORIAS_VALIDAS:
            return False, f"Categoría inválida: {self.categoria}"
        
        if self.tipo not in ["Ingreso", "Egreso"]:
            return False, f"Tipo inválido: {self.tipo}"
        
        if self.monto <= 0:
            return False, "El monto debe ser positivo"
        
        return True, "Ajuste válido"


@dataclass
class ResultadoConciliacion:
    """
    Resultado de conciliación por cuenta.
    
    ODOO MIGRATION:
    ---------------
    En Odoo, estos serían campos computados (@api.depends) en el modelo
    principal de conciliación.
    """
    cuenta: str
    periodo_inicio: str
    periodo_fin: str
    
    # Datos SICONE (proyectados)
    saldo_inicial_sicone: float
    ingresos_sicone: float
    egresos_sicone: float
    saldo_final_sicone: float
    
    # Ajustes documentados
    ajustes_ingresos: float
    ajustes_egresos: float
    
    # Datos reales (bancarios)
    saldo_inicial_real: float
    saldo_final_real: float
    
    # Resultados calculados
    saldo_conciliado: float
    diferencia_residual: float
    precision_porcentaje: float
    
    def get_status(self) -> str:
        """
        Determina status según precisión.
        
        En Odoo: @api.depends('precision_porcentaje')
        """
        if self.precision_porcentaje >= 98.0:
            return "✅ APROBADO"
        elif self.precision_porcentaje >= 95.0:
            return "⚠️ REVISAR"
        else:
            return "🚨 CRÍTICO"
    
    def diferencia_porcentual(self) -> float:
        """Diferencia como % del saldo final"""
        if self.saldo_final_real == 0:
            return 0.0
        return abs(self.diferencia_residual / self.saldo_final_real) * 100
    
    def to_dict(self) -> dict:
        """Para serialización"""
        return asdict(self)


# ============================================================================
# MOTOR DE CONCILIACIÓN
# ============================================================================

class ConciliadorSICONE:
    """
    Motor de conciliación financiera.
    
    DISEÑO SIN ESTADO DE UI:
    -------------------------
    Esta clase NO tiene dependencias de Streamlit. Toda la lógica es Python
    puro, facilitando la migración a Odoo.
    """
    
    def __init__(self, fecha_inicio: str, fecha_fin: str):
        """
        Inicializa el conciliador para un período específico.
        
        Args:
            fecha_inicio: Fecha de inicio en formato 'YYYY-MM-DD'
            fecha_fin: Fecha de fin en formato 'YYYY-MM-DD'
        """
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.datos_sicone = None
        self.datos_sicone_procesados = None
        self.saldos_reales: Dict[str, SaldosCuenta] = {}
        self.ajustes: List[Ajuste] = []
    
    # ------------------------------------------------------------------------
    # CARGA DE DATOS
    # ------------------------------------------------------------------------
    
    def cargar_datos_sicone(self, ruta_json: str = None, datos_dict: dict = None) -> bool:
        """
        Carga datos proyectados del JSON consolidado.
        
        Args:
            ruta_json: Ruta al archivo JSON (para uso desde filesystem)
            datos_dict: Diccionario con datos (para uso desde Odoo/API)
        
        Returns:
            True si carga exitosa
        """
        try:
            if ruta_json:
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    self.datos_sicone = json.load(f)
            elif datos_dict:
                self.datos_sicone = datos_dict
            else:
                return False
            
            # Extraer y procesar datos del período
            self.datos_sicone_procesados = self._extraer_datos_periodo()
            
            return self.datos_sicone_procesados is not None
            
        except Exception as e:
            print(f"❌ Error al cargar datos SICONE: {str(e)}")
            return False
    
    def _extraer_datos_periodo(self) -> Optional[Dict]:
        """
        Extrae datos del período específico desde el JSON consolidado.
        
        ESTRUCTURA DEL JSON CONSOLIDADO:
        --------------------------------
        {
          "df_consolidado": {
            "fechas": ["2025-12-08", "2025-12-15", ...],
            "saldo_consolidado": [2351677236.77, ...],
            "ingresos_proy_total": [0.0, 0.0, ...],
            "egresos_proy_total": [30804103.67, ...],
            "es_historica": [true, true, false, ...]
          }
        }
        
        LÓGICA DE EXTRACCIÓN:
        ---------------------
        1. Busca índice de semana donde fecha >= fecha_inicio
        2. Busca índice de semana donde fecha <= fecha_fin
        3. Extrae saldo inicial (primera semana del período)
        4. Suma ingresos y egresos del período
        5. Calcula saldo final
        
        NOTA: El JSON solo tiene datos consolidados, sin distribución
        por cuenta. Por ahora, retorna datos totales que luego se
        distribuirán según proporciones del usuario.
        """
        if not self.datos_sicone:
            return None
        
        try:
            # Obtener datos consolidados
            df_consolidado = self.datos_sicone.get("df_consolidado", {})
            
            if not df_consolidado:
                print("⚠️ No se encontró 'df_consolidado' en el JSON")
                return None
            
            fechas = df_consolidado.get("fechas", [])
            saldos = df_consolidado.get("saldo_consolidado", [])
            ingresos = df_consolidado.get("ingresos_proy_total", [])
            egresos = df_consolidado.get("egresos_proy_total", [])
            es_historica = df_consolidado.get("es_historica", [])
            
            if not fechas:
                print("⚠️ No hay fechas en df_consolidado")
                return None
            
            # Convertir fecha_inicio y fecha_fin a strings para comparación
            fecha_inicio_str = self.fecha_inicio
            fecha_fin_str = self.fecha_fin
            
            # Encontrar índices del período
            idx_inicio = None
            idx_fin = None
            
            for i, fecha in enumerate(fechas):
                if fecha >= fecha_inicio_str and idx_inicio is None:
                    idx_inicio = i
                if fecha <= fecha_fin_str:
                    idx_fin = i
            
            # Validar que encontramos el período
            if idx_inicio is None or idx_fin is None:
                print(f"⚠️ Período {fecha_inicio_str} a {fecha_fin_str} no encontrado en datos")
                print(f"   Fechas disponibles: {fechas[0]} a {fechas[-1]}")
                return None
            
            if idx_fin < idx_inicio:
                print(f"⚠️ Fecha fin anterior a fecha inicio")
                return None
            
            # Extraer datos del período
            # Saldo inicial: el saldo de la primera semana del período
            saldo_inicial_consolidado = saldos[idx_inicio]
            
            # Sumar ingresos y egresos del período
            ingresos_periodo = sum(ingresos[idx_inicio:idx_fin+1])
            egresos_periodo = sum(egresos[idx_inicio:idx_fin+1])
            
            # Saldo final: el saldo de la última semana del período
            saldo_final_consolidado = saldos[idx_fin]
            
            # Verificar si hay datos históricos en el período
            tiene_historico = any(es_historica[idx_inicio:idx_fin+1])
            
            # Metadatos del período extraído
            metadata_periodo = {
                "idx_inicio": idx_inicio,
                "idx_fin": idx_fin,
                "fecha_inicio_real": fechas[idx_inicio],
                "fecha_fin_real": fechas[idx_fin],
                "semanas_analizadas": idx_fin - idx_inicio + 1,
                "tiene_datos_historicos": tiene_historico
            }
            
            # IMPORTANTE: Como el JSON solo tiene datos consolidados,
            # retornamos los datos totales sin distribución por cuenta.
            # La distribución se hará más adelante según input del usuario.
            datos = {
                "Consolidado": {
                    "saldo_inicial": saldo_inicial_consolidado,
                    "ingresos": ingresos_periodo,
                    "egresos": egresos_periodo,
                    "saldo_final": saldo_final_consolidado
                },
                "Fiducuenta": {
                    "saldo_inicial": 0,
                    "ingresos": 0,
                    "egresos": 0,
                    "saldo_final": 0
                },
                "Cuenta Bancaria": {
                    "saldo_inicial": 0,
                    "ingresos": 0,
                    "egresos": 0,
                    "saldo_final": 0
                },
                "metadata": metadata_periodo
            }
            
            print(f"✅ Datos extraídos del período {metadata_periodo['fecha_inicio_real']} a {metadata_periodo['fecha_fin_real']}")
            print(f"   Semanas: {metadata_periodo['semanas_analizadas']}")
            print(f"   Saldo Inicial: ${saldo_inicial_consolidado:,.0f}")
            print(f"   Saldo Final: ${saldo_final_consolidado:,.0f}")
            
            return datos
            
        except Exception as e:
            print(f"❌ Error al extraer datos del período: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def set_saldos_reales(self, fiducuenta: SaldosCuenta, 
                          cuenta_bancaria: SaldosCuenta) -> None:
        """Establece saldos reales de ambas cuentas"""
        self.saldos_reales["Fiducuenta"] = fiducuenta
        self.saldos_reales["Cuenta Bancaria"] = cuenta_bancaria
    
    # ------------------------------------------------------------------------
    # GESTIÓN DE AJUSTES
    # ------------------------------------------------------------------------
    
    def agregar_ajuste(self, ajuste: Ajuste) -> Tuple[bool, str]:
        """
        Agrega un ajuste validándolo primero.
        
        Returns:
            (bool, str): (éxito, mensaje)
        """
        valido, mensaje = ajuste.validar()
        if not valido:
            return False, mensaje
        
        self.ajustes.append(ajuste)
        return True, "Ajuste agregado correctamente"
    
    def obtener_ajustes_por_cuenta(self, cuenta: str) -> List[Ajuste]:
        """Filtra ajustes aplicables a una cuenta"""
        return [
            aj for aj in self.ajustes 
            if aj.cuenta == cuenta or aj.cuenta == "Ambas"
        ]
    
    # ------------------------------------------------------------------------
    # VALIDACIONES
    # ------------------------------------------------------------------------
    
    def validar_movimientos_internos(self) -> Tuple[bool, str]:
        """
        Valida que movimientos internos estén balanceados.
        
        REGLA: Transferencias entre cuentas deben sumar cero.
        """
        mov_internos = [
            aj for aj in self.ajustes 
            if aj.categoria == "Movimientos internos entre cuentas"
        ]
        
        if not mov_internos:
            return True, "Sin movimientos internos"
        
        ingresos = sum(aj.monto for aj in mov_internos if aj.tipo == "Ingreso")
        egresos = sum(aj.monto for aj in mov_internos if aj.tipo == "Egreso")
        
        diferencia = abs(ingresos - egresos)
        tolerancia = 1000
        
        if diferencia <= tolerancia:
            return True, f"✅ Movimientos balanceados (dif: ${diferencia:,.0f})"
        else:
            return False, (f"❌ Desbalanceados: Ing ${ingresos:,.0f} vs "
                          f"Egr ${egresos:,.0f} (Dif: ${diferencia:,.0f})")
    
    def validar_ajustes_grandes(self, umbral: float = 50_000_000) -> List[Ajuste]:
        """Identifica ajustes que superan el umbral"""
        return [aj for aj in self.ajustes if aj.monto > umbral]
    
    def generar_resumen_ajustes(self):
        """
        Genera un resumen de ajustes por categoría.
        
        Returns:
            dict con resumen estructurado
        """
        if not self.ajustes:
            return {}
        
        resumen = {}
        for ajuste in self.ajustes:
            cat = ajuste.categoria
            if cat not in resumen:
                resumen[cat] = {
                    'ingresos': 0,
                    'egresos': 0,
                    'neto': 0,
                    'cantidad': 0
                }
            
            if ajuste.tipo == "Ingreso":
                resumen[cat]['ingresos'] += ajuste.monto
                resumen[cat]['neto'] += ajuste.monto
            else:
                resumen[cat]['egresos'] += ajuste.monto
                resumen[cat]['neto'] -= ajuste.monto
            
            resumen[cat]['cantidad'] += 1
        
        return resumen
    
    # ------------------------------------------------------------------------
    # CÁLCULO DE CONCILIACIÓN
    # ------------------------------------------------------------------------
    
    def calcular_conciliacion(self) -> Dict[str, ResultadoConciliacion]:
        """
        Ejecuta el cálculo completo de conciliación.
        
        ALGORITMO:
        ----------
        Por cada cuenta:
        1. Saldo inicial SICONE
        2. + Ingresos SICONE
        3. - Egresos SICONE
        4. = Saldo final SICONE
        5. + Ajustes ingresos
        6. - Ajustes egresos
        7. = Saldo conciliado
        8. Comparar vs Saldo final real
        9. Calcular diferencia y precisión
        """
        resultados = {}
        
        for cuenta in ["Fiducuenta", "Cuenta Bancaria"]:
            # Datos SICONE proyectados
            datos_sicone = self.datos_sicone_procesados.get(cuenta, {})
            saldo_ini_sicone = datos_sicone.get("saldo_inicial", 0)
            ingresos_sicone = datos_sicone.get("ingresos", 0)
            egresos_sicone = datos_sicone.get("egresos", 0)
            saldo_fin_sicone = saldo_ini_sicone + ingresos_sicone - egresos_sicone
            
            # Ajustes documentados
            ajustes_cuenta = self.obtener_ajustes_por_cuenta(cuenta)
            ajustes_ing = sum(aj.monto for aj in ajustes_cuenta if aj.tipo == "Ingreso")
            ajustes_egr = sum(aj.monto for aj in ajustes_cuenta if aj.tipo == "Egreso")
            
            # Saldo conciliado
            saldo_conciliado = saldo_fin_sicone + ajustes_ing - ajustes_egr
            
            # Datos reales
            saldos_reales_cuenta = self.saldos_reales.get(cuenta)
            if not saldos_reales_cuenta:
                continue
            
            saldo_ini_real = saldos_reales_cuenta.saldo_inicial
            saldo_fin_real = saldos_reales_cuenta.saldo_final
            
            # Diferencia y precisión
            diferencia = saldo_fin_real - saldo_conciliado
            
            if saldo_fin_real != 0:
                precision = 100 * (1 - abs(diferencia) / abs(saldo_fin_real))
            else:
                precision = 0.0
            
            # Construir resultado
            resultado = ResultadoConciliacion(
                cuenta=cuenta,
                periodo_inicio=self.fecha_inicio,
                periodo_fin=self.fecha_fin,
                saldo_inicial_sicone=saldo_ini_sicone,
                ingresos_sicone=ingresos_sicone,
                egresos_sicone=egresos_sicone,
                saldo_final_sicone=saldo_fin_sicone,
                ajustes_ingresos=ajustes_ing,
                ajustes_egresos=ajustes_egr,
                saldo_inicial_real=saldo_ini_real,
                saldo_final_real=saldo_fin_real,
                saldo_conciliado=saldo_conciliado,
                diferencia_residual=diferencia,
                precision_porcentaje=precision
            )
            
            resultados[cuenta] = resultado
        
        return resultados
    
    # ------------------------------------------------------------------------
    # EXPORTACIÓN
    # ------------------------------------------------------------------------
    
    def exportar_conciliacion(self, ruta_salida: str) -> bool:
        """
        Exporta conciliación a JSON.
        """
        try:
            resultados = self.calcular_conciliacion()
            validacion = self.validar_movimientos_internos()
            
            datos_export = {
                "metadata": {
                    "fecha_conciliacion": datetime.now().isoformat(),
                    "periodo_inicio": self.fecha_inicio,
                    "periodo_fin": self.fecha_fin,
                },
                "resultados": {
                    cuenta: res.to_dict()
                    for cuenta, res in resultados.items()
                },
                "ajustes": [aj.to_dict() for aj in self.ajustes],
                "validaciones": {
                    "movimientos_internos_ok": validacion[0],
                    "mensaje_validacion": validacion[1]
                }
            }
            
            with open(ruta_salida, 'w', encoding='utf-8') as f:
                json.dump(datos_export, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"❌ Error al exportar: {str(e)}")
            return False


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def formatear_moneda(valor: float) -> str:
    """Formatea valor como moneda colombiana"""
    return f"${valor:,.0f}".replace(",", ".")
