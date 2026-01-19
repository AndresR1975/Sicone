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
        Extrae datos del período específico desde los proyectos individuales.
        
        NUEVA IMPLEMENTACIÓN - DATOS HISTÓRICOS COMPLETOS:
        --------------------------------------------------
        Extrae datos de proyectos[].data.tesoreria.metricas_semanales
        que contiene el historial completo de cada proyecto desde su inicio.
        
        ESTRUCTURA DEL JSON:
        -------------------
        {
          "proyectos": [
            {
              "nombre": "AVelez",
              "estado": "ACTIVO",
              "data": {
                "proyecto": {
                  "fecha_inicio": "2024-11-14"
                },
                "tesoreria": {
                  "metricas_semanales": [
                    {
                      "semana": 1,
                      "ingresos_acum": 0,
                      "egresos_acum": 421850,
                      "saldo_final_real": -421850
                    },
                    ...
                  ]
                }
              }
            }
          ]
        }
        
        LÓGICA:
        -------
        1. Itera sobre todos los proyectos activos
        2. Para cada proyecto, calcula fecha_inicio + semanas
        3. Filtra semanas dentro del período solicitado
        4. Calcula flujos del período (delta de acumulados)
        5. Suma flujos de todos los proyectos
        
        CORRECCIÓN IMPORTANTE:
        ----------------------
        NO puedo sumar acumulados directamente porque cada proyecto
        tiene su propia línea de tiempo. Debo:
        1. Calcular flujos de cada proyecto POR SEPARADO
        2. LUEGO sumar los flujos de todos los proyectos
        """
        if not self.datos_sicone:
            return None
        
        try:
            from datetime import datetime, timedelta
            
            # Obtener lista de proyectos
            proyectos = self.datos_sicone.get("proyectos", [])
            
            if not proyectos:
                print("⚠️ No se encontraron proyectos en el JSON")
                return None
            
            # Convertir fechas del período a datetime
            fecha_inicio_dt = datetime.fromisoformat(self.fecha_inicio)
            fecha_fin_dt = datetime.fromisoformat(self.fecha_fin)
            
            print(f"🔍 Buscando datos para período: {self.fecha_inicio} a {self.fecha_fin}")
            print(f"   Proyectos encontrados: {len(proyectos)}")
            
            # Acumuladores consolidados
            ingresos_periodo_total = 0
            egresos_periodo_total = 0
            saldo_inicial_total = 0
            saldo_final_total = 0
            semanas_encontradas = 0
            proyectos_con_datos = []
            
            # Procesar cada proyecto
            for proyecto in proyectos:
                nombre_proyecto = proyecto.get("nombre", "Sin nombre")
                estado = proyecto.get("estado", "DESCONOCIDO")
                
                # Solo proyectos activos
                if estado != "ACTIVO":
                    continue
                
                data = proyecto.get("data", {})
                if not data:
                    continue
                
                # Obtener fecha de inicio del proyecto
                info_proyecto = data.get("proyecto", {})
                fecha_inicio_proyecto_str = info_proyecto.get("fecha_inicio")
                
                if not fecha_inicio_proyecto_str:
                    print(f"   ⚠️ {nombre_proyecto}: Sin fecha de inicio, omitiendo")
                    continue
                
                fecha_inicio_proyecto = datetime.fromisoformat(fecha_inicio_proyecto_str)
                
                # Obtener métricas semanales de tesorería
                tesoreria = data.get("tesoreria", {})
                metricas_semanales = tesoreria.get("metricas_semanales", [])
                
                if not metricas_semanales:
                    print(f"   ⚠️ {nombre_proyecto}: Sin métricas semanales, omitiendo")
                    continue
                
                print(f"   📊 {nombre_proyecto}: {len(metricas_semanales)} semanas disponibles desde {fecha_inicio_proyecto_str}")
                
                # Variables para este proyecto
                semanas_en_periodo = []
                
                # Procesar cada semana del proyecto
                for metrica in metricas_semanales:
                    semana_num = metrica.get("semana", 0)
                    
                    # Calcular fecha de esta semana (inicio_proyecto + (semana-1)*7 días)
                    fecha_semana = fecha_inicio_proyecto + timedelta(weeks=(semana_num - 1))
                    
                    # Verificar si esta semana está dentro del período solicitado
                    if fecha_inicio_dt <= fecha_semana <= fecha_fin_dt:
                        semanas_en_periodo.append({
                            "semana": semana_num,
                            "fecha": fecha_semana,
                            "ingresos_acum": metrica.get("ingresos_acum", 0),
                            "egresos_acum": metrica.get("egresos_acum", 0),
                            "saldo_final": metrica.get("saldo_final_real", 0)
                        })
                
                if semanas_en_periodo:
                    # Ordenar por semana
                    semanas_en_periodo.sort(key=lambda x: x["semana"])
                    
                    # Primera y última semana del período
                    primera_semana = semanas_en_periodo[0]
                    ultima_semana = semanas_en_periodo[-1]
                    
                    # Buscar la semana ANTERIOR a la primera del período para calcular saldo inicial
                    semana_anterior = None
                    for metrica in metricas_semanales:
                        if metrica.get("semana") == primera_semana["semana"] - 1:
                            semana_anterior = metrica
                            break
                    
                    # Saldo inicial del período para este proyecto
                    if semana_anterior:
                        saldo_inicial_proyecto = semana_anterior.get("saldo_final_real", 0)
                        ingresos_acum_anterior = semana_anterior.get("ingresos_acum", 0)
                        egresos_acum_anterior = semana_anterior.get("egresos_acum", 0)
                    else:
                        # Si es la primera semana del proyecto, saldo inicial es 0
                        saldo_inicial_proyecto = 0
                        ingresos_acum_anterior = 0
                        egresos_acum_anterior = 0
                    
                    # Flujos del período (diferencia entre última y acumulado anterior)
                    ingresos_periodo_proyecto = ultima_semana["ingresos_acum"] - ingresos_acum_anterior
                    egresos_periodo_proyecto = ultima_semana["egresos_acum"] - egresos_acum_anterior
                    saldo_final_proyecto = ultima_semana["saldo_final"]
                    
                    # Acumular en totales consolidados
                    saldo_inicial_total += saldo_inicial_proyecto
                    ingresos_periodo_total += ingresos_periodo_proyecto
                    egresos_periodo_total += egresos_periodo_proyecto
                    saldo_final_total += saldo_final_proyecto
                    semanas_encontradas += len(semanas_en_periodo)
                    
                    proyectos_con_datos.append({
                        "nombre": nombre_proyecto,
                        "semanas": len(semanas_en_periodo),
                        "saldo_inicial": saldo_inicial_proyecto,
                        "ingresos": ingresos_periodo_proyecto,
                        "egresos": egresos_periodo_proyecto,
                        "saldo_final": saldo_final_proyecto
                    })
                    
                    print(f"      ✓ {len(semanas_en_periodo)} semanas en período")
                    print(f"      → Saldo inicial: ${saldo_inicial_proyecto:,.0f}")
                    print(f"      → Ingresos: ${ingresos_periodo_proyecto:,.0f}")
                    print(f"      → Egresos: ${egresos_periodo_proyecto:,.0f}")
                    print(f"      → Saldo final: ${saldo_final_proyecto:,.0f}")
            
            # Verificar que encontramos datos
            if not proyectos_con_datos:
                print(f"❌ No se encontraron datos para el período {self.fecha_inicio} a {self.fecha_fin}")
                print(f"   Verifica que las fechas coincidan con los proyectos activos")
                return None
            
            # Calcular saldo final proyectado para verificar coherencia
            saldo_final_calculado = saldo_inicial_total + ingresos_periodo_total - egresos_periodo_total
            
            # Preparar datos consolidados
            datos = {
                "Consolidado": {
                    "saldo_inicial": saldo_inicial_total,
                    "ingresos": ingresos_periodo_total,
                    "egresos": egresos_periodo_total,
                    "saldo_final": saldo_final_total  # Usamos el saldo final real
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
                "metadata": {
                    "fecha_inicio_real": self.fecha_inicio,
                    "fecha_fin_real": self.fecha_fin,
                    "proyectos_analizados": len(proyectos_con_datos),
                    "semanas_totales": semanas_encontradas,
                    "tiene_datos_historicos": True,
                    "proyectos_detalle": proyectos_con_datos
                }
            }
            
            print(f"\n✅ Datos consolidados extraídos:")
            print(f"   Proyectos con datos: {len(proyectos_con_datos)}")
            print(f"   Semanas totales: {semanas_encontradas}")
            print(f"   Saldo Inicial Total: ${saldo_inicial_total:,.0f}")
            print(f"   Ingresos Total: ${ingresos_periodo_total:,.0f}")
            print(f"   Egresos Total: ${egresos_periodo_total:,.0f}")
            print(f"   Saldo Final Total: ${saldo_final_total:,.0f}")
            print(f"   Verificación: Calc=${saldo_final_calculado:,.0f} vs Real=${saldo_final_total:,.0f}")
            
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
