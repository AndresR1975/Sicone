# ============================================================================
# MODIFICACIÓN PARA multiproy_fcl.py v1.2.1
# ============================================================================
# 
# INSTRUCCIONES:
# 1. Abrir multiproy_fcl.py en tu editor
# 2. Ir a la línea ~207 (justo ANTES de "# Determinar estado del proyecto")
# 3. INSERTAR el siguiente código:
# ============================================================================

            # ================================================================
            # NUEVO v1.2.1: Calcular % de avance desde hitos
            # ================================================================
            if 'configuracion' in data and 'hitos' in data['configuracion']:
                hitos_config = data['configuracion']['hitos']
                total_hitos = len(hitos_config)
                
                # Contar hitos completados desde cartera (si existe)
                hitos_completados = 0
                
                if 'cartera' in data and data['cartera'] and 'contratos' in data['cartera']:
                    # Iterar contratos y sus hitos
                    for contrato in data['cartera']['contratos']:
                        if 'hitos' in contrato:
                            for hito_cartera in contrato['hitos']:
                                monto_esperado = hito_cartera.get('monto_esperado', 0)
                                pagos = hito_cartera.get('pagos', [])
                                monto_pagado = sum([p.get('monto', 0) for p in pagos])
                                
                                # Hito completado si está 100% pagado o más
                                if monto_pagado >= monto_esperado and monto_esperado > 0:
                                    hitos_completados += 1
                
                # Calcular porcentaje de avance
                if total_hitos > 0:
                    proyecto_info['avance_hitos_pct'] = (hitos_completados / total_hitos) * 100
                    proyecto_info['hitos_completados'] = hitos_completados
                    proyecto_info['hitos_totales'] = total_hitos
                else:
                    proyecto_info['avance_hitos_pct'] = 0
                    proyecto_info['hitos_completados'] = 0
                    proyecto_info['hitos_totales'] = 0
            else:
                # No hay hitos configurados
                proyecto_info['avance_hitos_pct'] = 0
                proyecto_info['hitos_completados'] = 0
                proyecto_info['hitos_totales'] = 0

# ============================================================================
# FIN DE LA MODIFICACIÓN
# ============================================================================
#
# El código continúa normalmente con:
# "# Determinar estado del proyecto"
# (No cambiar nada más)
# ============================================================================

# ============================================================================
# VERIFICACIÓN VISUAL
# ============================================================================
#
# Después de insertar, tu código debería verse así:
#
# ```python
#     # Capital disponible del proyecto
#     proyecto_info['capital_disponible'] = proyecto_info['excedente'] + proyecto_info['saldo_real_tesoreria']
#     
#     # ================================================================
#     # NUEVO v1.2.1: Calcular % de avance desde hitos
#     # ================================================================
#     if 'configuracion' in data and 'hitos' in data['configuracion']:
#         hitos_config = data['configuracion']['hitos']
#         total_hitos = len(hitos_config)
#         # ... (código insertado)
#         proyecto_info['avance_hitos_pct'] = (hitos_completados / total_hitos) * 100
#         # ...
#     else:
#         proyecto_info['avance_hitos_pct'] = 0
#         # ...
#     
#     # Determinar estado del proyecto
#     if proyecto_info['fecha_inicio'] > self.fecha_actual:
#         proyecto_info['estado'] = 'EN_COTIZACIÓN'
#     # ... (resto del código original)
# ```
# ============================================================================
