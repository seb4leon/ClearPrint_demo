"""
Módulo de cálculos para la calculadora de huella de carbono - FASE 1
Sistema con unidades, transporte individual y nueva estructura
"""

import pandas as pd
import numpy as np
from utils.units import convertir_unidad, formatear_numero

def obtener_factor(factores_df, categoria, item=None, subcategoria=None):
    """
    Obtiene el factor de emisión para una categoría específica
    """
    try:
        filtro = factores_df['category'] == categoria
        
        if item:
            filtro &= factores_df['item'] == item
        if subcategoria:
            filtro &= factores_df['subcategory'] == subcategoria
        
        factor = factores_df.loc[filtro, 'factor_kgCO2e_per_unit'].iloc[0]
        return float(factor)
    except (IndexError, ValueError):
        # Valor por defecto si no se encuentra el factor
        factores_por_defecto = {
            'materia_prima': 1.0,
            'material_empaque': 2.0,
            'transporte': 0.1,
            'energia': 0.5,
            'agua': 0.5,
            'residuo': 0.3
        }
        return factores_por_defecto.get(categoria, 1.0)

def calcular_emisiones_materias_primas(materias_primas, factores_df):
    """
    Calcula emisiones de materias primas - NUEVA VERSIÓN con unidades
    Considera cantidad REAL comprada (con merma)
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, materia in enumerate(materias_primas):
        if not materia or 'producto' not in materia:
            continue
            
        # Emisiones del PRODUCTO (usando cantidad REAL comprada)
        factor_producto = obtener_factor(factores_df, 'materia_prima', materia['producto'])
        emisiones_producto = materia.get('cantidad_real_kg', 0) * factor_producto
        total_emisiones += emisiones_producto
        
        # Emisiones del empaque de la materia prima (si existe)
        emisiones_empaque_mp = 0.0
        if materia.get('empaque'):
            factor_empaque = obtener_factor(factores_df, 'material_empaque', materia['empaque']['material'])
            emisiones_empaque_mp = materia['empaque']['peso_kg'] * factor_empaque
            total_emisiones += emisiones_empaque_mp
        
        emisiones_detalle.append({
            'id': i+1,
            'producto': materia['producto'],
            'tipo': 'materia_prima',
            'cantidad_kg': materia.get('cantidad_real_kg', 0),
            'emisiones_producto': emisiones_producto,
            'emisiones_empaque': emisiones_empaque_mp,
            'total': emisiones_producto + emisiones_empaque_mp
        })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_empaques(empaques, factores_df):
    """
    Calcula emisiones de los empaques del producto final
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, empaque in enumerate(empaques):
        if not empaque or 'material' not in empaque:
            continue
            
        factor = obtener_factor(factores_df, 'material_empaque', empaque['material'])
        peso_total = empaque.get('peso_kg', 0) * empaque.get('cantidad', 1)
        emisiones = peso_total * factor
        total_emisiones += emisiones
        
        emisiones_detalle.append({
            'id': i+1,
            'nombre': empaque.get('nombre', f'Empaque {i+1}'),
            'material': empaque['material'],
            'tipo': 'empaque_producto',
            'peso_total_kg': peso_total,
            'emisiones': emisiones
        })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_transporte_materias_primas(materias_primas, factores_df):
    """
    Calcula emisiones de transporte para materias primas - NUEVA VERSIÓN individual
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, materia in enumerate(materias_primas):
        if not materia or 'transportes' not in materia:
            continue
            
        emisiones_materia = 0.0
        rutas_detalle = []
        
        for j, transporte in enumerate(materia.get('transportes', [])):
            if transporte and transporte.get('tipo_transporte'):
                factor = obtener_factor(factores_df, 'transporte', transporte['tipo_transporte'])
                emisiones_ruta = transporte['distancia_km'] * transporte['carga_ton'] * factor
                emisiones_materia += emisiones_ruta
                
                rutas_detalle.append({
                    'ruta': j+1,
                    'origen': transporte.get('origen', ''),
                    'destino': transporte.get('destino', ''),
                    'distancia_km': transporte['distancia_km'],
                    'emisiones': emisiones_ruta
                })
        
        total_emisiones += emisiones_materia
        
        emisiones_detalle.append({
            'id': i+1,
            'producto': materia.get('producto', ''),
            'tipo': 'transporte_materia_prima',
            'total_emisiones': emisiones_materia,
            'rutas': rutas_detalle
        })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_transporte_empaques(empaques, factores_df):
    """
    Calcula emisiones de transporte para empaques - NUEVA VERSIÓN individual
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, empaque in enumerate(empaques):
        if not empaque or 'transportes' not in empaque:
            continue
            
        emisiones_empaque = 0.0
        rutas_detalle = []
        
        for j, transporte in enumerate(empaque.get('transportes', [])):
            if transporte and transporte.get('tipo_transporte'):
                factor = obtener_factor(factores_df, 'transporte', transporte['tipo_transporte'])
                emisiones_ruta = transporte['distancia_km'] * transporte['carga_ton'] * factor
                emisiones_empaque += emisiones_ruta
                
                rutas_detalle.append({
                    'ruta': j+1,
                    'origen': transporte.get('origen', ''),
                    'destino': transporte.get('destino', ''),
                    'distancia_km': transporte['distancia_km'],
                    'emisiones': emisiones_ruta
                })
        
        total_emisiones += emisiones_empaque
        
        emisiones_detalle.append({
            'id': i+1,
            'nombre': empaque.get('nombre', ''),
            'material': empaque.get('material', ''),
            'tipo': 'transporte_empaque',
            'total_emisiones': emisiones_empaque,
            'rutas': rutas_detalle
        })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_energia(consumo_kwh, tipo_energia, factores_df):
    """
    Calcula emisiones por consumo energético
    """
    factor = obtener_factor(factores_df, 'energia', tipo_energia)
    return consumo_kwh * factor

def calcular_emisiones_agua(consumo_m3, factores_df):
    """
    Calcula emisiones por consumo de agua
    """
    factor = obtener_factor(factores_df, 'agua')
    return consumo_m3 * factor

def calcular_emisiones_residuos(masa_kg, factores_df, distribucion_fin_vida=None):
    """
    Calcula emisiones por gestión de residuos
    """
    if distribucion_fin_vida:
        # Cálculo para fin de vida con distribución porcentual
        total_emisiones = 0.0
        
        # Vertedero
        factor_vertedero = obtener_factor(factores_df, 'residuo', item='Vertedero')
        emisiones_vertedero = (masa_kg * distribucion_fin_vida['porcentaje_vertedero'] / 100 * 
                             factor_vertedero)
        
        # Incineración
        factor_incineracion = obtener_factor(factores_df, 'residuo', item='Incineración')
        emisiones_incineracion = (masa_kg * distribucion_fin_vida['porcentaje_incineracion'] / 100 * 
                                factor_incineracion)
        
        # Compostaje
        factor_compostaje = obtener_factor(factores_df, 'residuo', item='Compostaje')
        emisiones_compostaje = (masa_kg * distribucion_fin_vida['porcentaje_compostado'] / 100 * 
                              factor_compostaje)
        
        # Reciclaje
        factor_reciclaje = obtener_factor(factores_df, 'residuo', item='Reciclaje')
        emisiones_reciclaje = (masa_kg * distribucion_fin_vida['porcentaje_reciclado'] / 100 * 
                             factor_reciclaje)
        
        total_emisiones = (emisiones_vertedero + emisiones_incineracion + 
                          emisiones_compostaje + emisiones_reciclaje)
        
        return total_emisiones
    else:
        # Cálculo simple para residuos de producción
        factor = obtener_factor(factores_df, 'residuo')
        return masa_kg * factor

def calcular_balance_masa(materias_primas, empaques):
    """
    Calcula el balance de masa del sistema - NUEVA FUNCIÓN
    """
    balance = {
        'entradas': {
            'materias_primas_kg': 0.0,
            'empaques_materias_primas_kg': 0.0,
            'empaques_producto_kg': 0.0,
            'total_entradas_kg': 0.0
        },
        'salidas': {
            'producto_terminado_kg': 0.0,
            'mermas_produccion_kg': 0.0,
            'residuos_produccion_kg': 0.0,
            'total_salidas_kg': 0.0
        },
        'coherencia': 0.0  # Diferencia entre entradas y salidas
    }
    
    # Calcular entradas
    for mp in materias_primas:
        if mp and mp.get('producto'):
            balance['entradas']['materias_primas_kg'] += mp.get('cantidad_real_kg', 0)
            if mp.get('empaque'):
                balance['entradas']['empaques_materias_primas_kg'] += mp['empaque'].get('peso_kg', 0)
    
    for emp in empaques:
        if emp and emp.get('nombre'):
            peso_total = emp.get('peso_kg', 0) * emp.get('cantidad', 1)
            balance['entradas']['empaques_producto_kg'] += peso_total
    
    balance['entradas']['total_entradas_kg'] = (
        balance['entradas']['materias_primas_kg'] + 
        balance['entradas']['empaques_materias_primas_kg'] + 
        balance['entradas']['empaques_producto_kg']
    )
    
    # Calcular salidas (placeholder para FASE 2)
    # En FASE 2 se calcularán basado en los datos de producción
    
    balance['coherencia'] = balance['entradas']['total_entradas_kg'] - balance['salidas']['total_salidas_kg']
    
    return balance

def exportar_resultados_excel(producto, resultados_detalle, total_emisiones, factores_df, balance_masa=None):
    """
    Exporta resultados a archivo Excel - MEJORADA para FASE 1
    """
    import openpyxl
    from datetime import datetime
    
    archivo = f"temp_huella_{producto['nombre']}.xlsx"
    
    with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
        # Hoja de resumen
        resumen_data = {
            'Producto': [producto['nombre']],
            'Unidad Funcional': [producto['unidad_funcional']],
            'Peso Neto': [f"{formatear_numero(producto['peso_neto'])} {producto['unidad_peso']}"],
            'Peso Empaque': [f"{formatear_numero(producto['peso_empaque'])} {producto['unidad_empaque']}"],
            'Huella Total (kg CO₂e)': [total_emisiones],
            'Fecha Cálculo': [datetime.now().strftime("%Y-%m-%d %H:%M")]
        }
        df_resumen = pd.DataFrame(resumen_data)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        
        # Hoja de desglose
        resultados_detalle.to_excel(writer, sheet_name='Desglose por Etapa', index=False)
        
        # Hoja de factores utilizados
        factores_df.to_excel(writer, sheet_name='Factores de Emisión', index=False)
        
        # Hoja de balance de masa (si existe)
        if balance_masa:
            balance_data = {
                'Concepto': list(balance_masa['entradas'].keys()) + list(balance_masa['salidas'].keys()) + ['Coherencia'],
                'Valor (kg)': list(balance_masa['entradas'].values()) + list(balance_masa['salidas'].values()) + [balance_masa['coherencia']]
            }
            df_balance = pd.DataFrame(balance_data)
            df_balance.to_excel(writer, sheet_name='Balance de Masa', index=False)
    
    return archivo

# Funciones de validación para FASE 1
def validar_datos_completos(materias_primas, empaques):
    """
    Valida que los datos mínimos estén completos para cálculos
    """
    errores = []
    
    # Validar materias primas
    for i, mp in enumerate(materias_primas):
        if mp and mp.get('producto'):
            if mp.get('cantidad_real_kg', 0) <= 0:
                errores.append(f"Materia prima {i+1}: Cantidad real debe ser mayor a 0")
            
            # Validar transportes si existen
            if mp.get('transportes'):
                for j, trans in enumerate(mp['transportes']):
                    if trans and trans.get('distancia_km', 0) > 0 and not trans.get('tipo_transporte'):
                        errores.append(f"Materia prima {i+1}, Ruta {j+1}: Tipo de transporte requerido")
    
    # Validar empaques
    for i, emp in enumerate(empaques):
        if emp and emp.get('nombre'):
            if emp.get('peso_kg', 0) <= 0:
                errores.append(f"Empaque {i+1}: Peso debe ser mayor a 0")
    
    return errores

def calcular_emisiones_totales_fase1(materias_primas, empaques, factores_df):
    """
    Calcula emisiones totales para FASE 1 (páginas 1-5)
    """
    emisiones_totales = 0.0
    desglose = {}
    
    try:
        # 1. Emisiones materias primas
        emisiones_mp, detalle_mp = calcular_emisiones_materias_primas(materias_primas, factores_df)
        emisiones_totales += emisiones_mp
        desglose['Materias Primas'] = emisiones_mp
        
        # 2. Emisiones empaques
        emisiones_emp, detalle_emp = calcular_emisiones_empaques(empaques, factores_df)
        emisiones_totales += emisiones_emp
        desglose['Empaques'] = emisiones_emp
        
        # 3. Transporte materias primas
        emisiones_trans_mp, detalle_trans_mp = calcular_emisiones_transporte_materias_primas(materias_primas, factores_df)
        emisiones_totales += emisiones_trans_mp
        desglose['Transporte MP'] = emisiones_trans_mp
        
        # 4. Transporte empaques
        emisiones_trans_emp, detalle_trans_emp = calcular_emisiones_transporte_empaques(empaques, factores_df)
        emisiones_totales += emisiones_trans_emp
        desglose['Transporte Empaques'] = emisiones_trans_emp
        
        return emisiones_totales, desglose
        
    except Exception as e:
        raise Exception(f"Error en cálculos: {str(e)}")
    
def calcular_emisiones_transporte(transportes, factores_df):
    """
    Función de compatibilidad - mantener para evitar errores de importación
    """
    # Esta función ya no se usa, pero se mantiene por compatibilidad
    return 0.0, []

def calcular_emisiones_produccion(produccion_data, factores_df):
    """
    Calcula emisiones de la etapa de producción
    """
    total_emisiones = 0.0
    desglose = {}
    
    try:
        # 1. Emisiones por energía
        if produccion_data.get('energia_kwh', 0) > 0:
            factor_energia = obtener_factor(factores_df, 'energia', produccion_data.get('tipo_energia', 'Red eléctrica promedio'))
            emisiones_energia = produccion_data['energia_kwh'] * factor_energia
            total_emisiones += emisiones_energia
            desglose['Energía Producción'] = emisiones_energia
        
        # 2. Emisiones por agua
        if produccion_data.get('agua_m3', 0) > 0:
            factor_agua = obtener_factor(factores_df, 'agua')
            emisiones_agua = produccion_data['agua_m3'] * factor_agua
            total_emisiones += emisiones_agua
            desglose['Agua Producción'] = emisiones_agua
        
        return total_emisiones, desglose
        
    except Exception as e:
        raise Exception(f"Error cálculo producción: {str(e)}")

def calcular_emisiones_gestion_mermas(mermas_gestionadas, factores_df):
    """
    Calcula emisiones por gestión de mermas y residuos
    """
    total_emisiones = 0.0
    desglose = {}
    
    try:
        for merma in mermas_gestionadas:
            if merma and merma.get('cantidad_kg', 0) > 0:
                # Emisiones por gestión
                factor_gestion = obtener_factor(factores_df, 'residuo', merma.get('tipo_gestion', 'Vertedero'))
                emisiones_gestion = merma['cantidad_kg'] * factor_gestion
                
                # Emisiones por transporte
                if merma.get('distancia_km', 0) > 0:
                    factor_transporte = obtener_factor(factores_df, 'transporte', merma.get('tipo_transporte', 'Camión diesel'))
                    carga_ton = merma['cantidad_kg'] / 1000
                    emisiones_transporte = merma['distancia_km'] * carga_ton * factor_transporte
                else:
                    emisiones_transporte = 0
                
                emisiones_totales_merma = emisiones_gestion + emisiones_transporte
                total_emisiones += emisiones_totales_merma
                
                desglose[f"Merma {merma.get('nombre_material', '')}"] = emisiones_totales_merma
        
        return total_emisiones, desglose
        
    except Exception as e:
        raise Exception(f"Error cálculo mermas: {str(e)}")

def calcular_eficiencia_produccion(materias_primas, peso_producto_kg):
    """
    Calcula la eficiencia del proceso productivo
    """
    try:
        total_mp_usadas_kg = sum(mp.get('cantidad_teorica_kg', 0) for mp in materias_primas if mp.get('producto'))
        
        if total_mp_usadas_kg > 0 and peso_producto_kg > 0:
            eficiencia = (peso_producto_kg / total_mp_usadas_kg) * 100
            return eficiencia, total_mp_usadas_kg
        else:
            return 0.0, 0.0
            
    except Exception as e:
        return 0.0, 0.0
    
def calcular_emisiones_distribucion(distribucion_data, factores_df):
    """
    Calcula emisiones de la etapa de distribución
    """
    total_emisiones = 0.0
    desglose = {}
    
    try:
        if not distribucion_data.get('canales'):
            return 0.0, {}
        
        for canal in distribucion_data['canales']:
            if canal and canal.get('nombre') and canal.get('rutas'):
                emisiones_canal = 0.0
                
                for ruta in canal['rutas']:
                    if ruta and ruta.get('distancia_km', 0) > 0:
                        factor_transporte = obtener_factor(factores_df, 'transporte', ruta.get('tipo_transporte', 'Camión diesel'))
                        carga_ton = ruta.get('carga_kg', 0) / 1000
                        emisiones_ruta = ruta['distancia_km'] * carga_ton * factor_transporte
                        emisiones_canal += emisiones_ruta
                
                total_emisiones += emisiones_canal
                desglose[f"Distribución {canal['nombre']}"] = emisiones_canal
        
        return total_emisiones, desglose
        
    except Exception as e:
        raise Exception(f"Error cálculo distribución: {str(e)}")

def validar_distribucion(distribucion_data):
    """
    Valida que la configuración de distribución sea coherente
    """
    try:
        if not distribucion_data.get('canales'):
            return True, "No hay canales configurados"
        
        # Validar suma de porcentajes
        porcentaje_total = sum(canal.get('porcentaje', 0) for canal in distribucion_data['canales'] if canal)
        
        if abs(porcentaje_total - 100.0) > 0.1:
            return False, f"Suma de porcentajes incorrecta: {porcentaje_total:.1f}%"
        
        # Validar rutas configuradas
        canales_sin_rutas = [c['nombre'] for c in distribucion_data['canales'] if c and not c.get('rutas')]
        if canales_sin_rutas:
            return False, f"Canales sin rutas: {', '.join(canales_sin_rutas)}"
        
        return True, "Configuración válida"
        
    except Exception as e:
        return False, f"Error en validación: {str(e)}"