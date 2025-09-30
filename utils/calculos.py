"""
Módulo de cálculos para la calculadora de huella de carbono - VERSIÓN FINAL
Sistema con gestión completa de unidades y factores estándar
"""

import pandas as pd
import numpy as np
from utils.units import convertir_unidad, formatear_numero

def obtener_factor(factores_df, categoria, item=None, subcategoria=None):
    """
    Obtiene el factor de emisión para una categoría específica - VERSIÓN FINAL
    """
    try:
        # Búsqueda case-insensitive y flexible
        filtro = factores_df['category'].str.lower() == categoria.lower()
        
        if item:
            items_disponibles = factores_df[filtro]['item'].str.lower().tolist()
            item_lower = item.lower()
            item_match = next((i for i in items_disponibles if item_lower in i), None)
            if item_match:
                item_original = factores_df[filtro & (factores_df['item'].str.lower() == item_match)]['item'].iloc[0]
                filtro &= factores_df['item'] == item_original
                
        if subcategoria:
            filtro &= factores_df['subcategory'] == subcategoria
        
        if not factores_df[filtro].empty:
            factor = float(factores_df.loc[filtro, 'factor_kgCO2e_per_unit'].iloc[0])
            unidad = factores_df.loc[filtro, 'unit'].iloc[0]
            if pd.isna(factor) or factor is None:
                raise ValueError("Factor no válido")
            return factor, unidad
        else:
            raise IndexError("Factor no encontrado")
            
    except (IndexError, ValueError, Exception) as e:
        print(f"Error obteniendo factor para {categoria}/{item}: {str(e)}")
        # Valores por defecto con sus unidades estándar
        factores_por_defecto = {
            'materia_prima': (2.0, 'kg'),
            'material_empaque': (3.0, 'kg'), 
            'transporte': (0.1, 'ton-km'),
            'energia': (0.45, 'kWh'),
            'agua': (0.34, 'm3'),
            'residuo': (0.5, 'kg')
        }
        return factores_por_defecto.get(categoria.lower(), (1.0, 'kg'))

def calcular_emisiones_materias_primas(materias_primas, factores_df):
    """
    Calcula emisiones de materias primas - UNIDADES CORRECTAS
    Factor: kg CO₂e/kg (el usuario ingresa en varias unidades, convertimos a kg)
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, materia in enumerate(materias_primas):
        if not materia or 'producto' not in materia:
            continue
            
        try:
            # Obtener factor y unidad esperada
            factor, unidad_esperada = obtener_factor(factores_df, 'materia_prima', materia['producto'])
            
            # Convertir cantidad a la unidad del factor (kg)
            cantidad_real_kg = materia.get('cantidad_real_kg', 0)  # Ya está en kg por la conversión en app.py
            emisiones_producto = cantidad_real_kg * factor
            total_emisiones += emisiones_producto
            
            # Empaque de la materia prima
            emisiones_empaque_mp = 0.0
            if materia.get('empaque') and materia['empaque'].get('material'):
                factor_empaque, unidad_emp = obtener_factor(factores_df, 'material_empaque', materia['empaque']['material'])
                peso_emp_kg = materia['empaque'].get('peso_kg', 0)  # Ya está en kg
                emisiones_empaque_mp = peso_emp_kg * factor_empaque
                total_emisiones += emisiones_empaque_mp
                
        except Exception as e:
            print(f"Error en cálculo de MP {materia.get('producto', 'desconocido')}: {str(e)}")
            emisiones_producto = 0.0
            emisiones_empaque_mp = 0.0
        
        if materia.get('producto'):
            emisiones_detalle.append({
                'id': i+1,
                'producto': materia['producto'],
                'cantidad_real_kg': cantidad_real_kg,
                'emisiones_producto': emisiones_producto,
                'emisiones_empaque': emisiones_empaque_mp,
                'total': emisiones_producto + emisiones_empaque_mp
            })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_empaques(empaques, factores_df):
    """
    Calcula emisiones de empaques del producto - UNIDADES CORRECTAS
    Factor: kg CO₂e/kg (convertimos a kg)
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, empaque in enumerate(empaques):
        if not empaque or 'material' not in empaque:
            continue
            
        try:
            factor, unidad_esperada = obtener_factor(factores_df, 'material_empaque', empaque['material'])
            peso_total_kg = empaque.get('peso_kg', 0) * empaque.get('cantidad', 1)  # Ya está en kg
            
            emisiones = peso_total_kg * factor
            total_emisiones += emisiones
            
            emisiones_detalle.append({
                'id': i+1,
                'nombre': empaque.get('nombre', f'Empaque {i+1}'),
                'material': empaque['material'],
                'peso_total_kg': peso_total_kg,
                'emisiones': emisiones
            })
        except Exception as e:
            print(f"Error en cálculo de empaque {i+1}: {str(e)}")
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_transporte_materias_primas(materias_primas, factores_df):
    """
    Calcula emisiones de transporte para MP - CORRECCIÓN CRÍTICA
    Factor: kg CO₂e/ton-km (convertimos kg a ton y usamos km)
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, materia in enumerate(materias_primas):
        if not materia or 'transportes' not in materia:
            continue
            
        emisiones_materia = 0.0
        rutas_detalle = []
        
        for j, transporte in enumerate(materia.get('transportes', [])):
            if transporte and transporte.get('tipo_transporte') and transporte.get('distancia_km', 0) > 0:
                try:
                    factor, unidad_esperada = obtener_factor(factores_df, 'transporte', transporte['tipo_transporte'])
                    distancia_km = transporte.get('distancia_km', 0)
                    carga_kg = transporte.get('carga_kg', 0)  # En kg por conversión en app.py
                    
                    # CONVERSIÓN CRÍTICA: kg a toneladas para factor ton-km
                    carga_ton = carga_kg / 1000.0
                    
                    # Fórmula correcta: km × ton × (kgCO₂e/ton-km) = kgCO₂e
                    emisiones_ruta = distancia_km * carga_ton * factor
                    emisiones_materia += emisiones_ruta
                    
                    rutas_detalle.append({
                        'ruta': j+1,
                        'origen': transporte.get('origen', ''),
                        'destino': transporte.get('destino', ''),
                        'distancia_km': distancia_km,
                        'carga_kg': carga_kg,
                        'carga_ton': carga_ton,
                        'emisiones': emisiones_ruta
                    })
                    
                except Exception as e:
                    print(f"Error en transporte MP {i+1}, ruta {j+1}: {str(e)}")
        
        total_emisiones += emisiones_materia
        
        if materia.get('producto'):
            emisiones_detalle.append({
                'id': i+1,
                'producto': materia.get('producto', ''),
                'total_emisiones': emisiones_materia,
                'rutas': rutas_detalle
            })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_transporte_empaques(empaques, factores_df):
    """
    Calcula emisiones de transporte para empaques - CORRECCIÓN CRÍTICA
    Factor: kg CO₂e/ton-km (convertimos kg a ton y usamos km)
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, empaque in enumerate(empaques):
        if not empaque or 'transportes' not in empaque:
            continue
            
        emisiones_empaque = 0.0
        rutas_detalle = []
        
        for j, transporte in enumerate(empaque.get('transportes', [])):
            if transporte and transporte.get('tipo_transporte') and transporte.get('distancia_km', 0) > 0:
                try:
                    factor, unidad_esperada = obtener_factor(factores_df, 'transporte', transporte['tipo_transporte'])
                    distancia_km = transporte.get('distancia_km', 0)
                    carga_kg = transporte.get('carga_kg', 0)  # En kg por conversión en app.py
                    
                    # CONVERSIÓN CRÍTICA: kg a toneladas
                    carga_ton = carga_kg / 1000.0
                    
                    emisiones_ruta = distancia_km * carga_ton * factor
                    emisiones_empaque += emisiones_ruta
                    
                    rutas_detalle.append({
                        'ruta': j+1,
                        'origen': transporte.get('origen', ''),
                        'destino': transporte.get('destino', ''),
                        'distancia_km': distancia_km,
                        'carga_kg': carga_kg,
                        'carga_ton': carga_ton,
                        'emisiones': emisiones_ruta
                    })
                    
                except Exception as e:
                    print(f"Error en transporte empaque {i+1}, ruta {j+1}: {str(e)}")
        
        total_emisiones += emisiones_empaque
        
        if empaque.get('nombre'):
            emisiones_detalle.append({
                'id': i+1,
                'nombre': empaque.get('nombre', ''),
                'total_emisiones': emisiones_empaque,
                'rutas': rutas_detalle
            })
    
    return total_emisiones, emisiones_detalle

def calcular_emisiones_energia(consumo_kwh, tipo_energia, factores_df):
    """
    Calcula emisiones por energía - UNIDADES CORRECTAS
    Factor: kg CO₂e/kWh (el usuario ingresa en kWh)
    """
    try:
        factor, unidad_esperada = obtener_factor(factores_df, 'energia', tipo_energia)
        return consumo_kwh * factor
    except Exception as e:
        print(f"Error cálculo energía: {str(e)}")
        return 0.0

def calcular_emisiones_agua(consumo_m3, factores_df):
    """
    Calcula emisiones por agua - UNIDADES CORRECTAS  
    Factor: kg CO₂e/m³ (el usuario ingresa en m³)
    """
    try:
        factor, unidad_esperada = obtener_factor(factores_df, 'agua')
        return consumo_m3 * factor
    except Exception as e:
        print(f"Error cálculo agua: {str(e)}")
        return 0.0
    


def calcular_emisiones_residuos(masa_kg, factores_df, distribucion_fin_vida=None):
    """
    Calcula emisiones por gestión de residuos - CORREGIDA
    """
    try:
        if distribucion_fin_vida:
            # Cálculo para fin de vida con distribución porcentual
            total_emisiones = 0.0
            
            # Vertedero
            factor_vertedero, unidad_vertedero = obtener_factor(factores_df, 'residuo', 'Vertedero')
            emisiones_vertedero = (masa_kg * distribucion_fin_vida.get('porcentaje_vertedero', 0) / 100 * factor_vertedero)
            
            # Incineración
            factor_incineracion, unidad_incineracion = obtener_factor(factores_df, 'residuo', 'Incineración')
            emisiones_incineracion = (masa_kg * distribucion_fin_vida.get('porcentaje_incineracion', 0) / 100 * factor_incineracion)
            
            # Compostaje
            factor_compostaje, unidad_compostaje = obtener_factor(factores_df, 'residuo', 'Compostaje')
            emisiones_compostaje = (masa_kg * distribucion_fin_vida.get('porcentaje_compostaje', 0) / 100 * factor_compostaje)
            
            # Reciclaje
            factor_reciclaje, unidad_reciclaje = obtener_factor(factores_df, 'residuo', 'Reciclaje')
            emisiones_reciclaje = (masa_kg * distribucion_fin_vida.get('porcentaje_reciclaje', 0) / 100 * factor_reciclaje)
            
            total_emisiones = (emisiones_vertedero + emisiones_incineracion + 
                              emisiones_compostaje + emisiones_reciclaje)
            
            return total_emisiones
        else:
            # Cálculo simple para residuos de producción
            factor, unidad = obtener_factor(factores_df, 'residuo')
            return masa_kg * factor
            
    except Exception as e:
        print(f"Error en cálculo de emisiones de residuos: {str(e)}")
        return 0.0

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
    Calcula emisiones totales para FASE 1 (páginas 1-5) - ACTUALIZADA
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
    Calcula emisiones de la etapa de producción - CORREGIDA
    """
    total_emisiones = 0.0
    desglose = {}
    
    try:
        # 1. Emisiones por energía
        if produccion_data.get('energia_kwh', 0) > 0:
            factor_energia, unidad_energia = obtener_factor(factores_df, 'energia', produccion_data.get('tipo_energia', 'Red eléctrica promedio'))
            emisiones_energia = produccion_data['energia_kwh'] * factor_energia
            total_emisiones += emisiones_energia
            desglose['Energía Producción'] = emisiones_energia
        
        # 2. Emisiones por agua
        if produccion_data.get('agua_m3', 0) > 0:
            factor_agua, unidad_agua = obtener_factor(factores_df, 'agua')
            emisiones_agua = produccion_data['agua_m3'] * factor_agua
            total_emisiones += emisiones_agua
            desglose['Agua Producción'] = emisiones_agua
        
        return total_emisiones, desglose
        
    except Exception as e:
        raise Exception(f"Error cálculo producción: {str(e)}")

def calcular_emisiones_gestion_mermas(mermas_gestionadas, factores_df):
    """
    Calcula emisiones por gestión de mermas y residuos - CORREGIDA
    """
    total_emisiones = 0.0
    desglose = {}
    
    try:
        for merma in mermas_gestionadas:
            if merma and merma.get('cantidad_kg', 0) > 0:
                # Emisiones por gestión
                factor_gestion, unidad_gestion = obtener_factor(factores_df, 'residuo', merma.get('tipo_gestion', 'Vertedero'))
                emisiones_gestion = merma['cantidad_kg'] * factor_gestion
                
                # Emisiones por transporte - CORRECCIÓN CRÍTICA
                if merma.get('distancia_km', 0) > 0:
                    factor_transporte, unidad_transporte = obtener_factor(factores_df, 'transporte', merma.get('tipo_transporte', 'Camión diesel'))
                    # CONVERTIR kg a ton para factor ton-km
                    carga_ton = merma['cantidad_kg'] / 1000.0
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
    Calcula emisiones de la etapa de distribución - CORREGIDA
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
                        factor_transporte, unidad_transporte = obtener_factor(factores_df, 'transporte', ruta.get('tipo_transporte', 'Camión diesel'))
                        # CONVERTIR kg a ton para factor ton-km
                        carga_kg = ruta.get('carga_kg', 0)
                        carga_ton = carga_kg / 1000.0
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
    
def calcular_emisiones_uso_fin_vida(uso_fin_vida_data, factores_df):
    """
    Calcula emisiones de la etapa de uso y fin de vida del producto - CORREGIDA
    """
    emisiones_totales = 0.0
    desglose = {
        'uso': {
            'energia': 0.0,
            'agua': 0.0
        },
        'fin_vida': {}
    }
    
    try:
        # 1. Emisiones durante uso
        if uso_fin_vida_data.get('energia_uso_kwh', 0) > 0:
            factor_energia, unidad_energia = obtener_factor(factores_df, 'energia', 'electricidad')
            emisiones_energia = uso_fin_vida_data['energia_uso_kwh'] * factor_energia
            emisiones_totales += emisiones_energia
            desglose['uso']['energia'] = emisiones_energia
        
        if uso_fin_vida_data.get('agua_uso_m3', 0) > 0:
            factor_agua, unidad_agua = obtener_factor(factores_df, 'agua')
            emisiones_agua = uso_fin_vida_data['agua_uso_m3'] * factor_agua
            emisiones_totales += emisiones_agua
            desglose['uso']['agua'] = emisiones_agua
        
        # 2. Emisiones por gestión de fin de vida
        for empaque in uso_fin_vida_data.get('gestion_empaques', []):
            if not empaque or not empaque.get('peso_kg') or not empaque.get('porcentajes'):
                continue
                
            emisiones_empaque = calcular_emisiones_residuos(
                empaque['peso_kg'],
                factores_df,
                empaque['porcentajes']
            )
            
            emisiones_totales += emisiones_empaque
            desglose['fin_vida'][empaque.get('empaque', 'empaque')] = {
                'peso_kg': empaque['peso_kg'],
                'emisiones': emisiones_empaque,
                'porcentajes': empaque['porcentajes']
            }
        
        return emisiones_totales, desglose
        
    except Exception as e:
        raise Exception(f"Error en cálculo de emisiones de uso y fin de vida: {str(e)}")

def calcular_emisiones_retail(retail_data, factores_df):
    """
    Calcula emisiones de la etapa de retail - CORREGIDA
    """
    try:
        if not retail_data:
            return 0.0, {}
            
        emisiones_totales = 0.0
        desglose = {}
        
        # Obtener consumo energético
        consumo_kwh = retail_data.get('consumo_energia_kwh', 0)
        
        if consumo_kwh > 0:
            # Obtener factor de emisión para electricidad
            factor_energia, unidad_energia = obtener_factor(factores_df, 'energia', 'electricidad')
            
            # Calcular emisiones
            emisiones = consumo_kwh * factor_energia
            emisiones_totales += emisiones
            desglose['Energía Retail'] = emisiones
            
            # Agregar detalles al desglose
            desglose['Detalles'] = {
                'días_almacenamiento': retail_data.get('dias_almacenamiento', 0),
                'tipo_almacenamiento': retail_data.get('tipo_almacenamiento', ''),
                'consumo_kwh': consumo_kwh,
                'factor_energia': factor_energia
            }
        
        return emisiones_totales, desglose
        
    except Exception as e:
        raise Exception(f"Error en cálculo de emisiones retail: {str(e)}")
    
def calcular_emisiones_totales_completas(session_state, factores_df):
    """
    Calcula TODAS las emisiones del ciclo de vida - FUNCIÓN PRINCIPAL
    """
    try:
        emisiones_totales = 0.0
        desglose_completo = {}
        
        # 1. Materias Primas
        emisiones_mp, _ = calcular_emisiones_materias_primas(
            session_state.get('materias_primas', []), 
            factores_df
        )
        emisiones_totales += emisiones_mp
        desglose_completo['Materias Primas'] = emisiones_mp
        
        # 2. Empaques
        emisiones_emp, _ = calcular_emisiones_empaques(
            session_state.get('empaques', []), 
            factores_df
        )
        emisiones_totales += emisiones_emp
        desglose_completo['Empaques'] = emisiones_emp
        
        # 3. Transporte Materias Primas
        emisiones_trans_mp, _ = calcular_emisiones_transporte_materias_primas(
            session_state.get('materias_primas', []), 
            factores_df
        )
        emisiones_totales += emisiones_trans_mp
        desglose_completo['Transporte MP'] = emisiones_trans_mp
        
        # 4. Transporte Empaques
        emisiones_trans_emp, _ = calcular_emisiones_transporte_empaques(
            session_state.get('empaques', []), 
            factores_df
        )
        emisiones_totales += emisiones_trans_emp
        desglose_completo['Transporte Empaques'] = emisiones_trans_emp
        
        # 5. Producción
        emisiones_prod, _ = calcular_emisiones_produccion(
            session_state.get('produccion', {}), 
            factores_df
        )
        emisiones_totales += emisiones_prod
        desglose_completo['Producción'] = emisiones_prod
        
        # 6. Distribución
        emisiones_dist, _ = calcular_emisiones_distribucion(
            session_state.get('distribucion', {}), 
            factores_df
        )
        emisiones_totales += emisiones_dist
        desglose_completo['Distribución'] = emisiones_dist
        
        # 7. Retail
        emisiones_retail, _ = calcular_emisiones_retail(
            session_state.get('retail', {}), 
            factores_df
        )
        emisiones_totales += emisiones_retail
        desglose_completo['Retail'] = emisiones_retail
        
        # 8. Uso y Fin de Vida
        emisiones_uso, _ = calcular_emisiones_uso_fin_vida(
            session_state.get('uso_fin_vida', {}), 
            factores_df
        )
        emisiones_totales += emisiones_uso
        desglose_completo['Uso y Fin de Vida'] = emisiones_uso
        
        return emisiones_totales, desglose_completo
        
    except Exception as e:
        raise Exception(f"Error en cálculo completo: {str(e)}")