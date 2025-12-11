"""
Módulo de Inversiones Temporales para SICONE
Gestiona análisis y proyección de inversiones de excedentes de liquidez
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import date, timedelta

# ============================================================================
# CONSTANTES
# ============================================================================

# Tasas de referencia (actualizar manualmente o por API)
TASAS_REFERENCIA = {
    'DTF': 13.25,  # EA
    'IBR': 12.80,  # EA
}

# Comisiones típicas por instrumento (%)
COMISIONES = {
    'CDT': 0.0,  # Sin comisión
    'Fondo Liquidez': 0.5,  # 0.5% anual
    'Fondo Corto Plazo': 0.8,  # 0.8% anual
    'Cuenta Remunerada': 0.0,  # Sin comisión
}

# Retención en la fuente sobre rendimientos financieros
RETENCION_FUENTE = 0.07  # 7%

# Gravamen a los Movimientos Financieros (4x1000)
GMF = 0.004  # 0.4%

# Rangos de tasa por instrumento y plazo (EA)
TASAS_MERCADO = {
    'CDT': {
        30: (12.0, 13.0),
        60: (12.5, 13.5),
        90: (13.0, 14.0),
        180: (13.5, 14.5),
        360: (14.0, 15.0),
    },
    'Fondo Liquidez': {
        1: (10.0, 11.0),  # Diario
    },
    'Fondo Corto Plazo': {
        1: (11.0, 13.0),  # Diario
    },
    'Cuenta Remunerada': {
        1: (3.0, 6.0),  # Diario
    },
}


# ============================================================================
# CLASES DE DATOS
# ============================================================================

@dataclass
class Inversion:
    """Representa una inversión temporal"""
    nombre: str
    monto: float
    plazo_dias: int
    tasa_ea: float
    instrumento: str
    comision_anual: float = 0.0
    
    def calcular_retorno_bruto(self) -> float:
        """Calcula retorno bruto antes de descuentos"""
        # VF = VP * (1 + i)^(n/365)
        valor_final = self.monto * (1 + self.tasa_ea/100) ** (self.plazo_dias / 365)
        return valor_final - self.monto
    
    def calcular_comision(self) -> float:
        """Calcula comisión del instrumento"""
        if self.comision_anual == 0:
            return 0
        # Comisión proporcional al plazo
        return self.monto * (self.comision_anual / 100) * (self.plazo_dias / 365)
    
    def calcular_retencion(self, retorno_bruto: float) -> float:
        """Calcula retención en la fuente sobre rendimientos"""
        return retorno_bruto * RETENCION_FUENTE
    
    def calcular_gmf_retiro(self) -> float:
        """Calcula GMF (4x1000) al retirar capital + rendimientos"""
        # Se aplica sobre capital + rendimientos al retirar
        retorno_bruto = self.calcular_retorno_bruto()
        monto_retiro = self.monto + retorno_bruto
        return monto_retiro * GMF
    
    def calcular_retorno_neto(self) -> Dict:
        """Calcula retorno neto después de todos los descuentos"""
        retorno_bruto = self.calcular_retorno_bruto()
        comision = self.calcular_comision()
        retencion = self.calcular_retencion(retorno_bruto)
        gmf = self.calcular_gmf_retiro()
        
        # Descuentos totales
        descuentos_totales = comision + retencion + gmf
        retorno_neto = retorno_bruto - descuentos_totales
        
        # Capital final neto (lo que realmente recibes)
        capital_final_neto = self.monto + retorno_neto - self.monto * GMF  # GMF también al invertir
        
        return {
            'retorno_bruto': retorno_bruto,
            'comision': comision,
            'retencion_fuente': retencion,
            'gmf': gmf,
            'descuentos_totales': descuentos_totales,
            'retorno_neto': retorno_neto,
            'capital_final_neto': capital_final_neto,
            'roi_bruto': (retorno_bruto / self.monto) * 100,
            'roi_neto': (retorno_neto / self.monto) * 100,
            'tasa_efectiva_neta': ((1 + retorno_neto/self.monto) ** (365/self.plazo_dias) - 1) * 100
        }
    
    def get_fecha_vencimiento(self, fecha_inicio: date = None) -> date:
        """Calcula fecha de vencimiento"""
        if fecha_inicio is None:
            fecha_inicio = date.today()
        return fecha_inicio + timedelta(days=self.plazo_dias)


# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================

def calcular_excedente_invertible(saldo_total: float, margen_requerido: float, 
                                   margen_seguridad_pct: float = 20.0) -> Dict:
    """
    Calcula el excedente invertible considerando margen de seguridad
    
    Args:
        saldo_total: Saldo total disponible
        margen_requerido: Margen base requerido (8 semanas burn rate)
        margen_seguridad_pct: % adicional de seguridad
    
    Returns:
        Dict con cálculos de excedente
    """
    margen_seguridad_monto = margen_requerido * (margen_seguridad_pct / 100)
    margen_total = margen_requerido + margen_seguridad_monto
    excedente = max(0, saldo_total - margen_total)
    
    return {
        'saldo_total': saldo_total,
        'margen_requerido': margen_requerido,
        'margen_seguridad_pct': margen_seguridad_pct,
        'margen_seguridad_monto': margen_seguridad_monto,
        'margen_total': margen_total,
        'excedente_invertible': excedente,
        'porcentaje_excedente': (excedente / saldo_total * 100) if saldo_total > 0 else 0
    }


def analizar_riesgo_liquidez(saldo_total: float, monto_total_invertido: float, 
                             margen_total: float) -> Dict:
    """
    Analiza el riesgo de liquidez post-inversión
    
    Args:
        saldo_total: Saldo total disponible
        monto_total_invertido: Suma de todas las inversiones
        margen_total: Margen requerido + seguridad
    
    Returns:
        Dict con análisis de riesgo
    """
    liquidez_post = saldo_total - monto_total_invertido
    ratio_cobertura = liquidez_post / margen_total if margen_total > 0 else 0
    
    # Determinar nivel de riesgo
    if ratio_cobertura >= 3.0:
        nivel_riesgo = 'MUY BAJO'
        emoji = '🟢'
        estado = 'SEGURO'
    elif ratio_cobertura >= 2.0:
        nivel_riesgo = 'BAJO'
        emoji = '🟢'
        estado = 'SEGURO'
    elif ratio_cobertura >= 1.5:
        nivel_riesgo = 'MEDIO'
        emoji = '🟡'
        estado = 'ACEPTABLE'
    elif ratio_cobertura >= 1.0:
        nivel_riesgo = 'ALTO'
        emoji = '🟠'
        estado = 'PRECAUCIÓN'
    else:
        nivel_riesgo = 'CRÍTICO'
        emoji = '🔴'
        estado = 'RIESGOSO'
    
    return {
        'liquidez_post_inversion': liquidez_post,
        'monto_total_invertido': monto_total_invertido,
        'margen_total': margen_total,
        'ratio_cobertura': ratio_cobertura,
        'nivel_riesgo': nivel_riesgo,
        'emoji': emoji,
        'estado': estado,
        'porcentaje_invertido': (monto_total_invertido / saldo_total * 100) if saldo_total > 0 else 0
    }


def generar_recomendaciones(excedente: float, margen_total: float) -> List[Dict]:
    """
    Genera recomendaciones de inversión según excedente disponible
    
    Args:
        excedente: Excedente invertible
        margen_total: Margen total requerido
    
    Returns:
        Lista de recomendaciones
    """
    recomendaciones = []
    
    # Solo recomendar si hay excedente significativo
    if excedente < margen_total * 0.5:
        return [{
            'nombre': 'Sin Recomendación',
            'mensaje': 'Excedente insuficiente para inversiones. Enfocarse en liquidez operativa.',
            'prioridad': 0
        }]
    
    # Recomendación 1: Conservadora
    if excedente >= margen_total * 1.5:
        monto_rec = excedente * 0.70
        rec = {
            'nombre': 'Conservadora',
            'descripcion': 'Balance óptimo entre liquidez y rentabilidad',
            'monto': monto_rec,
            'distribucion': [
                {'instrumento': 'CDT', 'plazo': 90, 'porcentaje': 60, 'monto': monto_rec * 0.6},
                {'instrumento': 'Fondo Corto Plazo', 'plazo': 30, 'porcentaje': 30, 'monto': monto_rec * 0.3},
                {'instrumento': 'Fondo Liquidez', 'plazo': 1, 'porcentaje': 10, 'monto': monto_rec * 0.1},
            ],
            'liquidez_post': excedente - monto_rec,
            'riesgo': 'BAJO',
            'recomendada': True,
            'ventajas': [
                'Mantiene liquidez suficiente',
                'Diversificación de plazos',
                'Retorno moderado garantizado'
            ],
            'prioridad': 1
        }
        recomendaciones.append(rec)
    
    # Recomendación 2: Balanceada
    if excedente >= margen_total * 2.0:
        monto_rec = excedente * 0.80
        rec = {
            'nombre': 'Balanceada',
            'descripcion': 'Mayor rentabilidad con liquidez controlada',
            'monto': monto_rec,
            'distribucion': [
                {'instrumento': 'CDT', 'plazo': 180, 'porcentaje': 40, 'monto': monto_rec * 0.4},
                {'instrumento': 'CDT', 'plazo': 90, 'porcentaje': 40, 'monto': monto_rec * 0.4},
                {'instrumento': 'Fondo Liquidez', 'plazo': 1, 'porcentaje': 20, 'monto': monto_rec * 0.2},
            ],
            'liquidez_post': excedente - monto_rec,
            'riesgo': 'MEDIO',
            'recomendada': False,
            'ventajas': [
                'Mayor retorno potencial',
                'Liquidez escalonada',
                'Diversificación de instrumentos'
            ],
            'prioridad': 2
        }
        recomendaciones.append(rec)
    
    # Recomendación 3: Agresiva
    if excedente >= margen_total * 2.5:
        monto_rec = excedente * 0.85
        rec = {
            'nombre': 'Agresiva',
            'descripcion': 'Maximiza rentabilidad con mayor riesgo de liquidez',
            'monto': monto_rec,
            'distribucion': [
                {'instrumento': 'CDT', 'plazo': 180, 'porcentaje': 60, 'monto': monto_rec * 0.6},
                {'instrumento': 'CDT', 'plazo': 90, 'porcentaje': 30, 'monto': monto_rec * 0.3},
                {'instrumento': 'Fondo Liquidez', 'plazo': 1, 'porcentaje': 10, 'monto': monto_rec * 0.1},
            ],
            'liquidez_post': excedente - monto_rec,
            'riesgo': 'MEDIO-ALTO',
            'recomendada': False,
            'ventajas': [
                'Máximo retorno potencial',
                'Aprovechar tasas largas',
                'Menor liquidez inmediata'
            ],
            'desventajas': [
                'Baja liquidez por 6 meses',
                'Penalización por retiro anticipado'
            ],
            'prioridad': 3
        }
        recomendaciones.append(rec)
    
    return recomendaciones


def get_info_instrumento(instrumento: str) -> Dict:
    """
    Retorna información detallada sobre un instrumento financiero
    
    Args:
        instrumento: Nombre del instrumento
    
    Returns:
        Dict con información del instrumento
    """
    info = {
        'CDT': {
            'nombre_completo': 'Certificado de Depósito a Término',
            'descripcion': 'Instrumento de renta fija que paga una tasa conocida al vencimiento',
            'ventajas': [
                '✅ Retorno garantizado y conocido desde el inicio',
                '✅ Muy bajo riesgo (respaldado por Fogafín hasta $50M)',
                '✅ Tasas competitivas según plazo',
                '✅ No tiene comisiones de administración'
            ],
            'desventajas': [
                '❌ Baja liquidez (penalización por retiro anticipado)',
                '❌ Tasa fija (no aprovecha subidas de tasas)',
                '❌ Requiere mantener hasta vencimiento para retorno completo'
            ],
            'mejor_para': 'Excedentes que NO se necesitarán en el corto plazo',
            'plazo_recomendado': '90-180 días para balance liquidez/rentabilidad',
            'comision': '0% (sin comisión)',
            'liquidez': 'BAJA',
            'riesgo': 'MUY BAJO'
        },
        'Fondo Liquidez': {
            'nombre_completo': 'Fondo de Inversión de Liquidez',
            'descripcion': 'Fondo que invierte en títulos de muy corto plazo (< 90 días)',
            'ventajas': [
                '✅ Alta liquidez (retiro en 24-48 horas)',
                '✅ Sin penalización por retiro',
                '✅ Rentabilidad diaria',
                '✅ Flexible para entradas y salidas'
            ],
            'desventajas': [
                '❌ Menor rentabilidad que CDT',
                '❌ Tasa variable (puede bajar)',
                '❌ Comisión de administración',
                '❌ No garantiza retorno fijo'
            ],
            'mejor_para': 'Excedentes que pueden necesitarse en corto plazo',
            'plazo_recomendado': 'Sin plazo mínimo (flexible)',
            'comision': '~0.5% anual',
            'liquidez': 'ALTA',
            'riesgo': 'BAJO'
        },
        'Fondo Corto Plazo': {
            'nombre_completo': 'Fondo de Inversión de Corto Plazo',
            'descripcion': 'Fondo que invierte en títulos de corto plazo (< 1 año)',
            'ventajas': [
                '✅ Buena liquidez (retiro en 48-72 horas)',
                '✅ Mejor rentabilidad que fondos de liquidez',
                '✅ Diversificación automática',
                '✅ Gestión profesional'
            ],
            'desventajas': [
                '❌ Comisión de administración mayor',
                '❌ Tasa variable',
                '❌ No garantiza retorno específico',
                '❌ Puede tener pérdidas (raro pero posible)'
            ],
            'mejor_para': 'Balance entre liquidez y rentabilidad',
            'plazo_recomendado': 'Mínimo 30 días recomendado',
            'comision': '~0.8% anual',
            'liquidez': 'MEDIA-ALTA',
            'riesgo': 'BAJO-MEDIO'
        },
        'Cuenta Remunerada': {
            'nombre_completo': 'Cuenta de Ahorros Remunerada',
            'descripcion': 'Cuenta de ahorros que paga intereses por saldo',
            'ventajas': [
                '✅ Liquidez inmediata',
                '✅ Sin penalización',
                '✅ Sin comisión',
                '✅ Muy fácil de usar'
            ],
            'desventajas': [
                '❌ Baja rentabilidad (3-6% EA)',
                '❌ No aprovecha excedentes',
                '❌ Inflación puede superar retorno'
            ],
            'mejor_para': 'Reserva de liquidez inmediata solamente',
            'plazo_recomendado': 'Sin plazo (uso diario)',
            'comision': '0%',
            'liquidez': 'MUY ALTA',
            'riesgo': 'MUY BAJO'
        }
    }
    
    return info.get(instrumento, {})


def calcular_resumen_portafolio(inversiones: List[Inversion]) -> Dict:
    """
    Calcula resumen consolidado de múltiples inversiones
    
    Args:
        inversiones: Lista de inversiones
    
    Returns:
        Dict con resumen consolidado
    """
    if not inversiones:
        return {
            'monto_total': 0,
            'retorno_bruto_total': 0,
            'retorno_neto_total': 0,
            'descuentos_totales': 0,
            'roi_promedio_ponderado': 0,
            'plazo_promedio_ponderado': 0
        }
    
    monto_total = sum(inv.monto for inv in inversiones)
    retorno_bruto_total = 0
    retorno_neto_total = 0
    descuentos_totales = 0
    plazo_ponderado = 0
    
    for inv in inversiones:
        resultado = inv.calcular_retorno_neto()
        retorno_bruto_total += resultado['retorno_bruto']
        retorno_neto_total += resultado['retorno_neto']
        descuentos_totales += resultado['descuentos_totales']
        plazo_ponderado += inv.plazo_dias * (inv.monto / monto_total)
    
    roi_promedio = (retorno_neto_total / monto_total * 100) if monto_total > 0 else 0
    
    return {
        'monto_total': monto_total,
        'retorno_bruto_total': retorno_bruto_total,
        'retorno_neto_total': retorno_neto_total,
        'descuentos_totales': descuentos_totales,
        'roi_promedio_ponderado': roi_promedio,
        'plazo_promedio_ponderado': plazo_ponderado,
        'numero_inversiones': len(inversiones)
    }
