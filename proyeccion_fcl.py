# CORRECCIÓN CRÍTICA: Agregar esta función DESPUÉS de configurar_hitos_default()
# Insertar en línea ~757, justo después de la función configurar_hitos_default()

def calcular_semanas_esperadas_hitos(hitos: List[Dict], fases_config: List[Dict]) -> List[Dict]:
    """
    Calcula y agrega 'semana_esperada' a cada hito basándose en:
    - fase_vinculada: nombre de la fase
    - momento: 'inicio' o 'fin'
    
    CORRECCIÓN v2.3.2: Los hitos DEBEN tener semana_esperada calculada
    para que ejecucion_fcl.py pueda generar alertas correctamente.
    
    Args:
        hitos: Lista de hitos sin semana_esperada
        fases_config: Configuración de fases con duraciones
        
    Returns:
        Lista de hitos CON semana_esperada calculada
    """
    
    # 1. Calcular semanas acumuladas de inicio y fin de cada fase
    fases_semanas = {}
    semana_acum = 1
    
    for fase in fases_config:
        nombre_fase = fase['nombre']
        duracion = fase.get('duracion_semanas', 0)
        
        if duracion > 0:
            semana_inicio = semana_acum
            semana_fin = semana_acum + duracion - 1
            
            fases_semanas[nombre_fase] = {
                'inicio': semana_inicio,
                'fin': semana_fin
            }
            
            semana_acum += duracion
    
    # 2. Asignar semana_esperada a cada hito
    hitos_con_semanas = []
    
    for hito in hitos:
        hito_copia = hito.copy()
        
        fase_vinculada = hito.get('fase_vinculada', '')
        momento = hito.get('momento', 'inicio')
        
        if fase_vinculada in fases_semanas:
            if momento == 'inicio':
                hito_copia['semana_esperada'] = fases_semanas[fase_vinculada]['inicio']
            else:  # momento == 'fin'
                hito_copia['semana_esperada'] = fases_semanas[fase_vinculada]['fin']
        else:
            # Fallback: asignar semana 1
            hito_copia['semana_esperada'] = 1
            print(f"⚠️ WARNING: Fase '{fase_vinculada}' no encontrada para hito '{hito.get('nombre')}'")
        
        hitos_con_semanas.append(hito_copia)
    
    return hitos_con_semanas


# ============================================================================
# MODIFICAR la parte donde se genera el JSON (línea ~2449)
# ============================================================================

# ANTES (línea ~2449):
# 'hitos': hitos,

# AHORA debe ser:
# 'hitos': calcular_semanas_esperadas_hitos(hitos, fases),

# ============================================================================
# CAMBIOS EXACTOS A APLICAR EN proyeccion_fcl.py:
# ============================================================================

"""
PASO 1: Agregar la función calcular_semanas_esperadas_hitos() en línea ~757
        (justo después de configurar_hitos_default())

PASO 2: Modificar línea 2449:
        ANTES: 'hitos': hitos,
        AHORA: 'hitos': calcular_semanas_esperadas_hitos(hitos, fases),

Con esto, el JSON generado incluirá 'semana_esperada' para cada hito.
"""
