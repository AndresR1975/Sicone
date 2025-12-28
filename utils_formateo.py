"""
SICONE - Utilidades de Formateo
Versión: 1.0.0
Fecha: Diciembre 2024
Autor: Andrés Restrepo & Claude

Módulo compartido con funciones de formateo y utilidades comunes
para todos los módulos de SICONE.

FUNCIONALIDADES:
- Formateo de cifras monetarias (estándar colombiano)
- Formateo de porcentajes
- Formateo de fechas
- Validación de datos
- Constantes compartidas
"""

import pandas as pd
from datetime import datetime, date
from typing import Union, Optional

# ============================================================================
# CONSTANTES
# ============================================================================

# Configuración regional
FORMATO_REGIONAL = "CO"  # "CO" para Colombia, "US" para USA

# Símbolos de moneda
SIMBOLO_MONEDA = "$"

# Separadores decimales
SEPARADOR_DECIMAL_CO = ","  # Colombia usa coma
SEPARADOR_MILES_CO = "."    # Colombia usa punto

SEPARADOR_DECIMAL_US = "."  # USA usa punto
SEPARADOR_MILES_US = ","    # USA usa coma

# Estados de proyectos
ESTADOS_PROYECTO = {
    'ACTIVO': {'color': '#10b981', 'emoji': '🟢'},
    'EN_EJECUCION': {'color': '#3b82f6', 'emoji': '🔵'},
    'PAUSADO': {'color': '#f59e0b', 'emoji': '🟡'},
    'FINALIZADO': {'color': '#6b7280', 'emoji': '⚫'},
    'CANCELADO': {'color': '#ef4444', 'emoji': '🔴'},
}

# Estados financieros
ESTADOS_FINANCIEROS = {
    'EXCEDENTE': {'color': '#10b981', 'emoji': '🟢', 'descripcion': 'Saldo saludable'},
    'ESTABLE': {'color': '#3b82f6', 'emoji': '🔵', 'descripcion': 'Saldo adecuado'},
    'AJUSTADO': {'color': '#f59e0b', 'emoji': '🟡', 'descripcion': 'Requiere atención'},
    'CRÍTICO': {'color': '#ef4444', 'emoji': '🔴', 'descripcion': 'Acción inmediata'},
}


# ============================================================================
# FUNCIONES DE FORMATEO MONETARIO
# ============================================================================

def formatear_moneda(
    valor: Union[float, int, None], 
    formato: str = "CO",
    mostrar_simbolo: bool = True,
    decimales: Optional[int] = None
) -> str:
    """
    Formatea valores monetarios según convenciones colombianas o americanas
    
    Convenciones Colombia (CO):
    - K = Miles (1.000)
    - M = Millones (1.000.000)
    - MM = Miles de millones (1.000.000.000)
    - B = Billones (1.000.000.000.000) [Millón de millones]
    
    Convenciones USA (US):
    - K = Thousands (1,000)
    - M = Millions (1,000,000)
    - B = Billions (1,000,000,000)
    - T = Trillions (1,000,000,000,000)
    
    Args:
        valor: Número a formatear
        formato: "CO" para Colombia, "US" para USA
        mostrar_simbolo: Si se muestra el símbolo de moneda
        decimales: Número de decimales (None = automático según magnitud)
        
    Returns:
        str: Valor formateado
        
    Examples:
        >>> formatear_moneda(1_090_000_000, "CO")
        "$1.09MM"
        >>> formatear_moneda(1_090_000_000, "US")
        "$1.09B"
        >>> formatear_moneda(72_300_000, "CO")
        "$72.3M"
    """
    # Manejar valores nulos o cero
    if valor is None or pd.isna(valor) or valor == 0:
        return f"{SIMBOLO_MONEDA}0" if mostrar_simbolo else "0"
    
    # Determinar signo
    abs_valor = abs(valor)
    signo = "-" if valor < 0 else ""
    simbolo = SIMBOLO_MONEDA if mostrar_simbolo else ""
    
    # Formateo según región
    if formato == "CO":
        # Billones colombianos (millón de millones)
        if abs_valor >= 1_000_000_000_000:
            num_decimales = decimales if decimales is not None else 2
            cifra = abs_valor / 1_000_000_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}B".replace(".", ",")
        
        # Miles de millones (mil millones)
        elif abs_valor >= 1_000_000_000:
            num_decimales = decimales if decimales is not None else 2
            cifra = abs_valor / 1_000_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}MM".replace(".", ",")
        
        # Millones
        elif abs_valor >= 1_000_000:
            num_decimales = decimales if decimales is not None else 1
            cifra = abs_valor / 1_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}M".replace(".", ",")
        
        # Miles
        elif abs_valor >= 1_000:
            num_decimales = decimales if decimales is not None else 0
            cifra = abs_valor / 1_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}K".replace(".", ",")
        
        # Unidades (con separador de miles colombiano)
        else:
            valor_formateado = f"{abs_valor:,.0f}".replace(",", ".")
            return f"{signo}{simbolo}{valor_formateado}"
    
    else:  # formato == "US"
        # Trillions
        if abs_valor >= 1_000_000_000_000:
            num_decimales = decimales if decimales is not None else 2
            cifra = abs_valor / 1_000_000_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}T"
        
        # Billions
        elif abs_valor >= 1_000_000_000:
            num_decimales = decimales if decimales is not None else 2
            cifra = abs_valor / 1_000_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}B"
        
        # Millions
        elif abs_valor >= 1_000_000:
            num_decimales = decimales if decimales is not None else 1
            cifra = abs_valor / 1_000_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}M"
        
        # Thousands
        elif abs_valor >= 1_000:
            num_decimales = decimales if decimales is not None else 0
            cifra = abs_valor / 1_000
            return f"{signo}{simbolo}{cifra:.{num_decimales}f}K"
        
        # Units
        else:
            valor_formateado = f"{abs_valor:,.0f}"
            return f"{signo}{simbolo}{valor_formateado}"


def formatear_moneda_completa(
    valor: Union[float, int, None],
    formato: str = "CO"
) -> str:
    """
    Formatea valores monetarios con separadores de miles pero SIN abreviar
    
    Args:
        valor: Número a formatear
        formato: "CO" para Colombia, "US" para USA
        
    Returns:
        str: Valor formateado completo
        
    Examples:
        >>> formatear_moneda_completa(1_090_000_000, "CO")
        "$1.090.000.000"
        >>> formatear_moneda_completa(1_090_000_000, "US")
        "$1,090,000,000"
    """
    if valor is None or pd.isna(valor) or valor == 0:
        return f"{SIMBOLO_MONEDA}0"
    
    signo = "-" if valor < 0 else ""
    abs_valor = abs(valor)
    
    if formato == "CO":
        # Usar punto como separador de miles
        valor_formateado = f"{abs_valor:,.0f}".replace(",", ".")
        return f"{signo}{SIMBOLO_MONEDA}{valor_formateado}"
    else:
        # Usar coma como separador de miles
        valor_formateado = f"{abs_valor:,.0f}"
        return f"{signo}{SIMBOLO_MONEDA}{valor_formateado}"


# ============================================================================
# FUNCIONES DE FORMATEO DE PORCENTAJES
# ============================================================================

def formatear_porcentaje(
    valor: Union[float, int, None],
    decimales: int = 1,
    mostrar_signo: bool = True
) -> str:
    """
    Formatea valores como porcentajes
    
    Args:
        valor: Número a formatear (0.15 = 15%, 15 = 15% según contexto)
        decimales: Número de decimales a mostrar
        mostrar_signo: Si se muestra el símbolo %
        
    Returns:
        str: Porcentaje formateado
        
    Examples:
        >>> formatear_porcentaje(0.157)
        "15.7%"
        >>> formatear_porcentaje(15.7)
        "15.7%"
        >>> formatear_porcentaje(15.7, decimales=0)
        "16%"
    """
    if valor is None or pd.isna(valor):
        return "0%" if mostrar_signo else "0"
    
    # Si el valor es menor a 1, asumimos que está en formato decimal (0.15 = 15%)
    if abs(valor) < 1:
        valor = valor * 100
    
    valor_formateado = f"{valor:.{decimales}f}"
    
    return f"{valor_formateado}%" if mostrar_signo else valor_formateado


# ============================================================================
# FUNCIONES DE FORMATEO DE FECHAS
# ============================================================================

def formatear_fecha(
    fecha: Union[datetime, date, str, None],
    formato: str = "corto"
) -> str:
    """
    Formatea fechas en diferentes formatos
    
    Args:
        fecha: Fecha a formatear
        formato: "corto", "largo", "iso", "relativo"
        
    Returns:
        str: Fecha formateada
        
    Examples:
        >>> formatear_fecha(datetime(2024, 12, 28), "corto")
        "28/12/2024"
        >>> formatear_fecha(datetime(2024, 12, 28), "largo")
        "28 de Diciembre de 2024"
        >>> formatear_fecha(datetime(2024, 12, 28), "iso")
        "2024-12-28"
    """
    if fecha is None or pd.isna(fecha):
        return "N/A"
    
    # Convertir string a datetime si es necesario
    if isinstance(fecha, str):
        try:
            fecha = pd.to_datetime(fecha)
        except:
            return fecha  # Retornar como está si no se puede convertir
    
    # Convertir date a datetime
    if isinstance(fecha, date) and not isinstance(fecha, datetime):
        fecha = datetime.combine(fecha, datetime.min.time())
    
    # Formatear según tipo
    if formato == "corto":
        return fecha.strftime("%d/%m/%Y")
    
    elif formato == "largo":
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        dia = fecha.day
        mes = meses[fecha.month]
        año = fecha.year
        return f"{dia} de {mes} de {año}"
    
    elif formato == "iso":
        return fecha.strftime("%Y-%m-%d")
    
    elif formato == "relativo":
        # Calcular diferencia con hoy
        hoy = datetime.now()
        diff = hoy - fecha
        
        if diff.days == 0:
            return "Hoy"
        elif diff.days == 1:
            return "Ayer"
        elif diff.days == -1:
            return "Mañana"
        elif diff.days > 0 and diff.days < 7:
            return f"Hace {diff.days} días"
        elif diff.days < 0 and diff.days > -7:
            return f"En {abs(diff.days)} días"
        elif diff.days >= 7 and diff.days < 30:
            semanas = diff.days // 7
            return f"Hace {semanas} semana{'s' if semanas > 1 else ''}"
        else:
            return fecha.strftime("%d/%m/%Y")
    
    else:
        return fecha.strftime("%d/%m/%Y %H:%M")


# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validar_numero(valor: any, default: float = 0.0) -> float:
    """
    Valida y convierte un valor a número, retornando default si no es válido
    
    Args:
        valor: Valor a validar
        default: Valor por defecto si no es válido
        
    Returns:
        float: Número validado
    """
    if valor is None or pd.isna(valor):
        return default
    
    try:
        return float(valor)
    except (ValueError, TypeError):
        return default


def obtener_valor_seguro(
    diccionario: dict,
    clave: str,
    default: any = None,
    tipo: type = None
) -> any:
    """
    Obtiene un valor de un diccionario de forma segura
    
    Args:
        diccionario: Diccionario del que obtener el valor
        clave: Clave a buscar
        default: Valor por defecto si no existe o es inválido
        tipo: Tipo esperado para validar/convertir
        
    Returns:
        any: Valor obtenido o default
        
    Examples:
        >>> obtener_valor_seguro({'a': 100}, 'a', 0, int)
        100
        >>> obtener_valor_seguro({'a': '100'}, 'a', 0, int)
        100
        >>> obtener_valor_seguro({'a': 100}, 'b', 0)
        0
    """
    valor = diccionario.get(clave, default)
    
    if valor is None or pd.isna(valor):
        return default
    
    # Convertir al tipo esperado si se especifica
    if tipo is not None:
        try:
            return tipo(valor)
        except (ValueError, TypeError):
            return default
    
    return valor


# ============================================================================
# FUNCIONES DE ESTADO Y COLOR
# ============================================================================

def obtener_info_estado_proyecto(estado: str) -> dict:
    """
    Obtiene información de color y emoji para un estado de proyecto
    
    Args:
        estado: Estado del proyecto
        
    Returns:
        dict: Información del estado con claves 'color' y 'emoji'
    """
    estado_upper = estado.upper()
    return ESTADOS_PROYECTO.get(
        estado_upper,
        {'color': '#6b7280', 'emoji': '⚪'}  # Default gris
    )


def obtener_info_estado_financiero(estado: str) -> dict:
    """
    Obtiene información de color, emoji y descripción para un estado financiero
    
    Args:
        estado: Estado financiero
        
    Returns:
        dict: Información del estado
    """
    estado_upper = estado.upper()
    return ESTADOS_FINANCIEROS.get(
        estado_upper,
        {'color': '#6b7280', 'emoji': '⚪', 'descripcion': 'Estado desconocido'}
    )


def calcular_color_semaforo(porcentaje: float) -> str:
    """
    Calcula color tipo semáforo basado en porcentaje
    
    Args:
        porcentaje: Porcentaje a evaluar (0-100)
        
    Returns:
        str: Color hex para el semáforo
        
    Examples:
        >>> calcular_color_semaforo(90)
        '#10b981'  # Verde
        >>> calcular_color_semaforo(50)
        '#f59e0b'  # Amarillo
        >>> calcular_color_semaforo(20)
        '#ef4444'  # Rojo
    """
    if porcentaje >= 75:
        return '#10b981'  # Verde
    elif porcentaje >= 50:
        return '#3b82f6'  # Azul
    elif porcentaje >= 25:
        return '#f59e0b'  # Amarillo
    else:
        return '#ef4444'  # Rojo


# ============================================================================
# FUNCIONES DE UTILIDAD PARA REPORTES
# ============================================================================

def generar_timestamp() -> str:
    """
    Genera timestamp formateado para reportes
    
    Returns:
        str: Timestamp en formato "YYYYMMDD_HHMM"
        
    Example:
        >>> generar_timestamp()
        "20241228_1558"
    """
    return datetime.now().strftime("%Y%m%d_%H%M")


def calcular_semanas_cobertura(saldo: float, burn_rate: float) -> float:
    """
    Calcula cuántas semanas de cobertura hay con el saldo actual
    
    Args:
        saldo: Saldo disponible
        burn_rate: Tasa de quema semanal
        
    Returns:
        float: Número de semanas de cobertura
        
    Examples:
        >>> calcular_semanas_cobertura(1000000, 100000)
        10.0
        >>> calcular_semanas_cobertura(1000000, 0)
        999.0  # Máximo cuando burn_rate es 0
    """
    if burn_rate <= 0:
        return 999.0  # Cobertura "infinita"
    
    return saldo / burn_rate


def determinar_estado_financiero(
    saldo: float,
    margen_proteccion: float,
    cobertura_semanas: float
) -> str:
    """
    Determina el estado financiero basado en métricas
    
    Args:
        saldo: Saldo actual
        margen_proteccion: Margen de protección definido
        cobertura_semanas: Semanas de cobertura
        
    Returns:
        str: Estado financiero ("EXCEDENTE", "ESTABLE", "AJUSTADO", "CRÍTICO")
    """
    excedente = saldo - margen_proteccion
    
    if excedente > margen_proteccion * 0.5:  # 50% más que el margen
        return "EXCEDENTE"
    elif excedente > 0:
        return "ESTABLE"
    elif cobertura_semanas >= 4:
        return "AJUSTADO"
    else:
        return "CRÍTICO"


# ============================================================================
# FUNCIONES DE CONVERSIÓN DE DATOS
# ============================================================================

def normalizar_nombre_clave(nombre: str) -> str:
    """
    Normaliza nombres de claves para búsqueda flexible
    
    Args:
        nombre: Nombre a normalizar
        
    Returns:
        str: Nombre normalizado (minúsculas, sin espacios)
        
    Examples:
        >>> normalizar_nombre_clave("Presupuesto Total")
        "presupuesto_total"
        >>> normalizar_nombre_clave("saldoRealTesoreria")
        "saldo_real_tesoreria"
    """
    # Convertir a minúsculas
    nombre = nombre.lower()
    
    # Reemplazar espacios por guión bajo
    nombre = nombre.replace(" ", "_")
    
    # Reemplazar camelCase por snake_case
    import re
    nombre = re.sub(r'(?<!^)(?=[A-Z])', '_', nombre).lower()
    
    return nombre


# ============================================================================
# EJEMPLOS DE USO (para testing)
# ============================================================================

if __name__ == "__main__":
    print("=== EJEMPLOS DE USO ===\n")
    
    # Formateo monetario Colombia
    print("Formateo Monetario (Colombia):")
    print(f"  1,090,000,000 → {formatear_moneda(1_090_000_000, 'CO')}")
    print(f"  688,700,000 → {formatear_moneda(688_700_000, 'CO')}")
    print(f"  72,300,000 → {formatear_moneda(72_300_000, 'CO')}")
    print(f"  1,500 → {formatear_moneda(1_500, 'CO')}")
    print()
    
    # Formateo monetario USA
    print("Formateo Monetario (USA):")
    print(f"  1,090,000,000 → {formatear_moneda(1_090_000_000, 'US')}")
    print(f"  688,700,000 → {formatear_moneda(688_700_000, 'US')}")
    print()
    
    # Porcentajes
    print("Formateo Porcentajes:")
    print(f"  0.157 → {formatear_porcentaje(0.157)}")
    print(f"  15.7 → {formatear_porcentaje(15.7)}")
    print()
    
    # Fechas
    print("Formateo Fechas:")
    hoy = datetime.now()
    print(f"  Corto: {formatear_fecha(hoy, 'corto')}")
    print(f"  Largo: {formatear_fecha(hoy, 'largo')}")
    print(f"  ISO: {formatear_fecha(hoy, 'iso')}")
    print()
    
    # Estados
    print("Información de Estados:")
    info = obtener_info_estado_financiero("EXCEDENTE")
    print(f"  EXCEDENTE → {info['emoji']} {info['descripcion']}")
