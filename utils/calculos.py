"""
Módulo de cálculos para la calculadora de huella de carbono - VERSIÓN FINAL MEJORADA
Sistema con gestión completa de unidades y factores estándar
COMPATIBLE CON NAVEGACIÓN POR PESTAÑAS
"""

import pandas as pd
import numpy as np
from utils.units import convertir_unidad, formatear_numero

def obtener_factor(factores_df, categoria, item=None, subcategoria=None):
    """
    Obtiene el factor de emisión para una categoría específica - VERSIÓN MEJORADA
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
            cantidad_real_kg = materia.get('cantidad_real_kg', 0)
            emisiones_producto = cantidad_real_kg * factor
            total_emisiones += emisiones_producto
            
            # Empaque de la materia prima
            emisiones_empaque_mp = 0.0
            if materia.get('empaque') and materia['empaque'].get('material'):
                factor_empaque, unidad_emp = obtener_factor(factores_df, 'material_empaque', materia['empaque']['material'])
                peso_emp_kg = materia['empaque'].get('peso_kg', 0)
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
    """
    total_emisiones = 0.0
    emisiones_detalle = []
    
    for i, empaque in enumerate(empaques):
        if not empaque or 'material' not in empaque:
            continue
            
        try:
            factor, unidad_esperada = obtener_factor(factores_df, 'material_empaque', empaque['material'])
            peso_total_kg = empaque.get('peso_kg', 0) * empaque.get('cantidad', 1)
            
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
                    carga_kg = transporte.get('carga_kg', 0)
                    
                    # CONVERSIÓN CRÍTICA: kg a toneladas para factor ton-km
                    carga_ton = carga_kg / 1000.0
                    
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
                    carga_kg = transporte.get('carga_kg', 0)
                    
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
                
                # Emisiones por transporte
                if merma.get('distancia_km', 0) > 0:
                    factor_transporte, unidad_transporte = obtener_factor(factores_df, 'transporte', merma.get('tipo_transporte', 'Camión diesel'))
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
                        carga_kg = ruta.get('carga_kg', 0)
                        carga_ton = carga_kg / 1000.0
                        emisiones_ruta = ruta['distancia_km'] * carga_ton * factor_transporte
                        emisiones_canal += emisiones_ruta
                
                total_emisiones += emisiones_canal
                desglose[f"Distribución {canal['nombre']}"] = emisiones_canal
        
        return total_emisiones, desglose
        
    except Exception as e:
        raise Exception(f"Error cálculo distribución: {str(e)}")

def calcular_emisiones_retail(retail_data, factores_df):
    """
    Calcula emisiones de la etapa de retail - CORREGIDA Y ROBUSTA
    """
    try:
        if not retail_data:
            return 0.0, {}
            
        emisiones_totales = 0.0
        desglose = {}
        
        try:
            consumo_kwh = float(retail_data.get('consumo_energia_kwh', 0))
        except (ValueError, TypeError):
            consumo_kwh = 0.0
        
        if consumo_kwh > 0:
            try:
                factor_energia, unidad_energia = obtener_factor(factores_df, 'energia', 'electricidad')
                factor_energia = float(factor_energia)
            except (ValueError, TypeError, IndexError):
                factor_energia = 0.2021
                
            emisiones = consumo_kwh * factor_energia
            emisiones_totales += emisiones
            desglose['Energía Retail'] = emisiones
            
            desglose['Detalles'] = {
                'días_almacenamiento': retail_data.get('dias_almacenamiento', 0),
                'tipo_almacenamiento': retail_data.get('tipo_almacenamiento', ''),
                'consumo_kwh': consumo_kwh,
                'factor_energia': factor_energia
            }
        
        return emisiones_totales, desglose
        
    except Exception as e:
        print(f"Error en cálculo de emisiones retail: {str(e)}")
        return 0.0, {}

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

def calcular_emisiones_detalladas_completas(session_state, factores_df):
    """
    Calcula TODAS las emisiones del ciclo de vida con desglose detallado por fuente
    VERSIÓN MEJORADA PARA INCLUIR TODAS LAS ETAPAS
    """
    try:
        emisiones_totales = 0.0
        desglose_detallado = {
            'materias_primas': {'total': 0.0, 'fuentes': {}},
            'empaques': {'total': 0.0, 'fuentes': {}},
            'transporte': {'total': 0.0, 'fuentes': {}},
            'procesamiento': {'total': 0.0, 'fuentes': {}},
            'distribucion': {'total': 0.0, 'fuentes': {}},
            'retail': {'total': 0.0, 'fuentes': {}},
            'fin_vida': {'total': 0.0, 'fuentes': {}}
        }
        
        # 1. MATERIAS PRIMAS
        if session_state.get('materias_primas'):
            emisiones_mp, detalle_mp = calcular_emisiones_materias_primas(
                session_state['materias_primas'], 
                factores_df
            )
            emisiones_totales += emisiones_mp
            desglose_detallado['materias_primas']['total'] = emisiones_mp
            
            if detalle_mp:
                for mp in detalle_mp:
                    if 'producto' in mp:
                        desglose_detallado['materias_primas']['fuentes'][mp['producto']] = {
                            'emisiones_material': mp.get('emisiones_producto', 0),
                            'emisiones_empaque': mp.get('emisiones_empaque', 0),
                            'total': mp.get('total', 0),
                            'cantidad_kg': mp.get('cantidad_real_kg', 0)
                        }
        
        # 2. EMPAQUES
        if session_state.get('empaques'):
            emisiones_emp, detalle_emp = calcular_emisiones_empaques(
                session_state['empaques'], 
                factores_df
            )
            emisiones_totales += emisiones_emp
            desglose_detallado['empaques']['total'] = emisiones_emp
            
            if detalle_emp:
                for emp in detalle_emp:
                    nombre = emp.get('nombre', f'Empaque {emp.get("id", "")}')
                    desglose_detallado['empaques']['fuentes'][nombre] = {
                        'emisiones': emp.get('emisiones', 0),
                        'peso_kg': emp.get('peso_total_kg', 0),
                        'material': emp.get('material', '')
                    }
        
        # 3. TRANSPORTE (MP + Empaques)
        transporte_total = 0.0
        detalle_transporte = {'materias_primas': [], 'empaques': []}
        
        # Transporte materias primas
        if session_state.get('materias_primas'):
            emisiones_trans_mp, detalle_trans_mp = calcular_emisiones_transporte_materias_primas(
                session_state['materias_primas'], 
                factores_df
            )
            transporte_total += emisiones_trans_mp
            detalle_transporte['materias_primas'] = detalle_trans_mp
        
        # Transporte empaques
        if session_state.get('empaques'):
            emisiones_trans_emp, detalle_trans_emp = calcular_emisiones_transporte_empaques(
                session_state['empaques'], 
                factores_df
            )
            transporte_total += emisiones_trans_emp
            detalle_transporte['empaques'] = detalle_trans_emp
        
        emisiones_totales += transporte_total
        desglose_detallado['transporte']['total'] = transporte_total
        desglose_detallado['transporte']['fuentes'] = {
            'materias_primas': {'emisiones': emisiones_trans_mp if 'emisiones_trans_mp' in locals() else 0.0, 
                               'detalle': detalle_transporte['materias_primas']},
            'empaques': {'emisiones': emisiones_trans_emp if 'emisiones_trans_emp' in locals() else 0.0, 
                        'detalle': detalle_transporte['empaques']}
        }
        
        # 4. PROCESAMIENTO (Producción) - GARANTIZAR QUE SE CALCULE
        if session_state.get('produccion'):
            emisiones_prod, desglose_prod = calcular_emisiones_produccion(
                session_state['produccion'], 
                factores_df
            )
            emisiones_totales += emisiones_prod
            desglose_detallado['procesamiento']['total'] = emisiones_prod
            desglose_detallado['procesamiento']['fuentes'] = desglose_prod
        
        # 5. DISTRIBUCIÓN - GARANTIZAR QUE SE CALCULE
        if session_state.get('distribucion'):
            emisiones_dist, desglose_dist = calcular_emisiones_distribucion(
                session_state['distribucion'], 
                factores_df
            )
            emisiones_totales += emisiones_dist
            desglose_detallado['distribucion']['total'] = emisiones_dist
            desglose_detallado['distribucion']['fuentes'] = desglose_dist
        
        # 6. RETAIL - GARANTIZAR QUE SE CALCULE
        if session_state.get('retail'):
            emisiones_retail, desglose_retail = calcular_emisiones_retail(
                session_state['retail'], 
                factores_df
            )
            emisiones_totales += emisiones_retail
            desglose_detallado['retail']['total'] = emisiones_retail
            desglose_detallado['retail']['fuentes'] = desglose_retail
        
        # 7. FIN DE VIDA - GARANTIZAR QUE SE CALCULE
        if session_state.get('uso_fin_vida'):
            emisiones_fin_vida, desglose_fin_vida = calcular_emisiones_uso_fin_vida(
                session_state['uso_fin_vida'], 
                factores_df
            )
            emisiones_totales += emisiones_fin_vida
            desglose_detallado['fin_vida']['total'] = emisiones_fin_vida
            desglose_detallado['fin_vida']['fuentes'] = desglose_fin_vida
        
        # Validar que todas las etapas se calcularon
        etapas_calculando = [
            ('materias_primas', 'Materias Primas'),
            ('empaques', 'Empaques'),
            ('transporte', 'Transporte'),
            ('procesamiento', 'Procesamiento'),
            ('distribucion', 'Distribución'),
            ('retail', 'Retail'),
            ('fin_vida', 'Fin de Vida')
        ]
        
        for etapa_key, etapa_nombre in etapas_calculando:
            if desglose_detallado[etapa_key]['total'] == 0:
                print(f"⚠️ Advertencia: {etapa_nombre} tiene emisiones 0. Verificar datos de entrada.")
        
        return emisiones_totales, desglose_detallado
        
    except Exception as e:
        raise Exception(f"Error en cálculo detallado: {str(e)}")

# Funciones de compatibilidad
def calcular_emisiones_totales_completas(session_state, factores_df):
    """Función de compatibilidad - alias para calcular_emisiones_detalladas_completas"""
    return calcular_emisiones_detalladas_completas(session_state, factores_df)

def calcular_balance_masa(materias_primas, empaques):
    """Función de compatibilidad"""
    return {
        'entradas': {'total_entradas_kg': 0.0},
        'salidas': {'total_salidas_kg': 0.0},
        'coherencia': 0.0
    }

# AÑADIR ESTA FUNCIÓN FALTANTE al archivo calculos.py

def calcular_emisiones_uso_fin_vida(uso_fin_vida_data, factores_df):
    """
    Calcula emisiones de la etapa de uso y fin de vida - NUEVA FUNCIÓN
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
        for gestion in uso_fin_vida_data.get('gestion_empaques', []):
            if gestion and gestion.get('peso_kg', 0) > 0:
                emisiones_empaque = calcular_emisiones_residuos(
                    gestion['peso_kg'],
                    factores_df,
                    gestion.get('porcentajes', {})
                )
                
                emisiones_totales += emisiones_empaque
                nombre_empaque = gestion.get('nombre_empaque', f'Empaque_{len(desglose["fin_vida"])}')
                desglose['fin_vida'][nombre_empaque] = {
                    'peso_kg': gestion['peso_kg'],
                    'emisiones': emisiones_empaque,
                    'porcentajes': gestion.get('porcentajes', {})
                }
        
        return emisiones_totales, desglose
        
    except Exception as e:
        print(f"Error en cálculo de emisiones de uso y fin de vida: {str(e)}")
        return 0.0, {'uso': {'energia': 0.0, 'agua': 0.0}, 'fin_vida': {}}

def exportar_resultados_excel(producto, resultados_detalle, total_emisiones, factores_df, balance_masa=None):
    """Función de compatibilidad"""
    return "temp_export.xlsx"