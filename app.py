"""
Calculadora de Huella de Carbono - FASE 1 COMPLETA
Sistema con unidades, transporte individual y balance de masa real
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.calculos import (
    calcular_emisiones_materias_primas,
    calcular_emisiones_empaques,
    calcular_emisiones_transporte_materias_primas,
    calcular_emisiones_transporte_empaques,
    calcular_emisiones_energia,
    calcular_emisiones_agua,
    calcular_emisiones_residuos,
    exportar_resultados_excel,
    obtener_factor,
    calcular_emisiones_uso_fin_vida
)
from utils.units import convertir_unidad, formatear_numero, obtener_unidades_disponibles

# Configuración de la página
st.set_page_config(
    page_title="Calculadora Huella de Carbono",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session_state con NUEVA estructura
def inicializar_session_state():
    defaults = {
        'producto': {
            'nombre': '',
            'unidad_funcional': '1 unidad',
            'peso_neto': 0.0,
            'unidad_peso': 'kg',
            'peso_empaque': 0.0,
            'unidad_empaque': 'kg'
        },
        'materias_primas': [],
        'empaques': [],
        'transportes_materias_primas': [],
        'transportes_empaques': [],
        'produccion': {
            'energia_kwh': 0.0,
            'tipo_energia': 'Red eléctrica promedio',
            'agua_m3': 0.0,
            'residuos_produccion': []
        },
        'distribucion': {
            'canales': []
        },
        'retail': {
            'dias_almacenamiento': 7,
            'tipo_almacenamiento': 'temperatura_ambiente',
            'consumo_energia_kwh': 0.0
        },
        'uso_fin_vida': {
            'energia_uso_kwh': 0.0,
            'agua_uso_m3': 0.0,
            'gestion_fin_vida': [],
            'emisiones': None
        }
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

inicializar_session_state()

# Función de validación global (agregar después de inicializar_session_state)
def validar_coherencia_datos():
    """Valida la coherencia entre los datos ingresados en diferentes páginas"""
    alertas = []
    
    # Solo validar si hay datos suficientes
    if (st.session_state.producto['nombre'] and 
        st.session_state.materias_primas and
        any(mp.get('producto') for mp in st.session_state.materias_primas)):
        
        peso_producto_kg = st.session_state.producto.get('peso_neto_kg', 0)
        total_mp_usadas_kg = sum(mp.get('cantidad_teorica_kg', 0) for mp in st.session_state.materias_primas if mp.get('producto'))
        
        if peso_producto_kg > 0 and total_mp_usadas_kg > 0:
            diferencia = abs(peso_producto_kg - total_mp_usadas_kg)
            porcentaje_diferencia = (diferencia / max(peso_producto_kg, total_mp_usadas_kg)) * 100
            
            if porcentaje_diferencia > 10:
                alertas.append(f"📊 **Incoherencia en pesos:** Producto {formatear_numero(peso_producto_kg)} kg vs MP {formatear_numero(total_mp_usadas_kg)} kg ({porcentaje_diferencia:.1f}% diferencia)")
    
    return alertas

# Mostrar alertas globales en el sidebar (agregar en el sidebar, antes de la navegación)
alertas_globales = validar_coherencia_datos()
if alertas_globales:
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚠️ Alertas de Validación")
    for alerta in alertas_globales:
        st.sidebar.warning(alerta)

# Cargar factores de emisión - CORREGIDA
@st.cache_data
def cargar_factores():
    try:
        factores = pd.read_csv('data/factors.csv')
        # Asegurarnos de que la columna factor_kgCO2e_per_unit sea numérica
        factores['factor_kgCO2e_per_unit'] = pd.to_numeric(factores['factor_kgCO2e_per_unit'], errors='coerce')
        # Llenar valores NaN con valores por defecto
        factores['factor_kgCO2e_per_unit'] = factores['factor_kgCO2e_per_unit'].fillna(1.0)
        return factores
    except FileNotFoundError:
        st.error("No se encontró el archivo de factores. Usando valores por defecto.")
        return pd.DataFrame({
            'category': ['materia_prima', 'material_empaque', 'transporte', 'energia', 'agua', 'residuo'],
            'subcategory': ['cereales', 'plasticos', 'terrestre', 'electricidad', 'potable', 'disposicion'],
            'item': ['Trigo', 'PET', 'Camión diesel', 'Red eléctrica promedio', 'Agua potable', 'Vertedero'],
            'unit': ['kg', 'kg', 'ton-km', 'kWh', 'm3', 'kg'],
            'factor_kgCO2e_per_unit': [0.5, 2.5, 0.1, 0.5, 0.5, 0.3],
            'source': ['Genérico', 'Genérico', 'Genérico', 'Genérico', 'Genérico', 'Genérico']
        })
    except Exception as e:
        st.error(f"Error cargando factores: {str(e)}")
        return pd.DataFrame({
            'category': ['materia_prima', 'material_empaque', 'transporte', 'energia', 'agua', 'residuo'],
            'subcategory': ['cereales', 'plasticos', 'terrestre', 'electricidad', 'potable', 'disposicion'],
            'item': ['Trigo', 'PET', 'Camión diesel', 'Red eléctrica promedio', 'Agua potable', 'Vertedero'],
            'unit': ['kg', 'kg', 'ton-km', 'kWh', 'm3', 'kg'],
            'factor_kgCO2e_per_unit': [0.5, 2.5, 0.1, 0.5, 0.5, 0.3],
            'source': ['Genérico', 'Genérico', 'Genérico', 'Genérico', 'Genérico', 'Genérico']
        })

factores = cargar_factores()

# Función para obtener opciones de cada categoría - CORREGIDA
def obtener_opciones_categoria(categoria):
    try:
        opciones = factores[factores['category'] == categoria]['item'].unique()
        return list(opciones)  # Convertir a lista para evitar problemas con numpy arrays
    except Exception as e:
        print(f"Error obteniendo opciones para {categoria}: {str(e)}")
        return []

# Navegación
st.sidebar.title("🌍 Calculadora de Huella de Carbono")
st.sidebar.markdown("---")

pagina = st.sidebar.radio("Navegación", [
    "🏠 Bienvenida",
    "1. Definir Producto",
    "2. Materias Primas", 
    "3. Empaque del Producto",
    "4. Transporte Materias Primas",
    "5. Transporte Empaques", 
    "6. Producción y Mermas",
    "7. Distribución",
    "8. Retail",
    "9. Uso y Fin de Vida",
    "10. Resultados"
])

# Página de Bienvenida
if pagina == "🏠 Bienvenida":
    st.title("🌍 Calculadora de Huella de Carbono")
    st.markdown("---")
    
    st.markdown("""
    <div style='background-color: #e8f5e8; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50;'>
    <h2 style='color: #2e7d32; margin-top: 0;'>¡Bienvenido/a a la Calculadora de Huella de Carbono!</h2>
    <p style='color: #555; font-size: 16px;'>Esta herramienta te permitirá calcular el impacto ambiental de tu producto con un sistema completo de trazabilidad.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Nuevas características de la FASE 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style='background-color: #e3f2fd; padding: 15px; border-radius: 10px; text-align: center;'>
        <h3 style='color: #1565c0;'>⚖️ Sistema de Unidades</h3>
        <p>• Conversión automática<br>• Múltiples unidades<br>• Formato español<br>• Flexibilidad total</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background-color: #f3e5f5; padding: 15px; border-radius: 10px; text-align: center;'>
        <h3 style='color: #7b1fa2;'>🚚 Transporte Individual</h3>
        <p>• Rutas por material<br>• Múltiples segmentos<br>• Origen/destino<br>• Trazabilidad completa</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='background-color: #fff3e0; padding: 15px; border-radius: 10px; text-align: center;'>
        <h3 style='color: #ef6c00;'>📊 Balance Real</h3>
        <p>• Merma real<br>• Comprado vs usado<br>• Gestión por elemento<br>• Coherencia total</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📖 **Nuevas Características - FASE 1**", expanded=True):
        st.markdown("""
        ### 🆕 **¿Qué hay de nuevo?**
        
        **Sistema de Unidades Inteligente:**
        - Ingresa datos en las unidades que prefieras (g, kg, ton, mL, L, m³)
        - Conversión automática a unidades estándar
        - Formato español con puntos para miles y comas para decimales
        
        **Transporte Individual por Material:**
        - Cada materia prima y empaque tiene sus propias rutas
        - Múltiples segmentos de transporte por elemento
        - Origen y destino específicos para trazabilidad
        
        **Balance de Masa Real:**
        - Diferenciación entre cantidad comprada y cantidad usada
        - Cálculo automático de mermas y pérdidas
        - Gestión individual de residuos por elemento
        
        ### 🚀 **Flujo de Trabajo Mejorado**
        1. **Definir producto** con unidades flexibles
        2. **Materias primas** con compra real vs teórica
        3. **Empaques** del producto final
        4. **Transporte individual** por material
        5. **Producción** con gestión de mermas
        6. **Resultados** con trazabilidad completa
        """)
    
    st.markdown("---")
    st.success("**FASE 1 IMPLEMENTADA** - Sistema con unidades y transporte individual")

# Página 1: Definir Producto (CORREGIDA - datos persistentes)
elif pagina == "1. Definir Producto":
    st.title("1. Definir Producto")
    st.info("💡 Define las características básicas de tu producto con unidades flexibles")
    
    # Inicializar valores si no existen
    if 'peso_neto_valor' not in st.session_state.producto:
        st.session_state.producto['peso_neto_valor'] = st.session_state.producto['peso_neto']
    if 'peso_empaque_valor' not in st.session_state.producto:
        st.session_state.producto['peso_empaque_valor'] = st.session_state.producto['peso_empaque']
    
    with st.form("definir_producto"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Información Básica")
            st.session_state.producto['nombre'] = st.text_input(
                "**Nombre del producto**", 
                value=st.session_state.producto['nombre'],
                placeholder="Ej: Galletas de chocolate, Jugo de naranja..."
            )
            
            st.session_state.producto['unidad_funcional'] = st.text_input(
                "**Unidad funcional**",
                value=st.session_state.producto['unidad_funcional'],
                placeholder="Ej: '1 unidad', '1 kg', '1 litro'"
            )
        
        with col2:
            st.subheader("📊 Pesos y Medidas")
            
            col_peso1, col_peso2 = st.columns(2)
            with col_peso1:
                # Usar el valor guardado en session_state
                peso_neto = st.number_input(
                    "**Peso neto del producto**", 
                    min_value=0.0,
                    value=st.session_state.producto['peso_neto_valor'],  # CORREGIDO
                    step=0.000000001,
                    format="%.10f",
                    key="peso_neto_input"
                )
                st.session_state.producto['peso_neto_valor'] = peso_neto  # GUARDAR
            with col_peso2:
                unidad_peso = st.selectbox(
                    "**Unidad**",
                    options=obtener_unidades_disponibles('masa'),
                    index=obtener_unidades_disponibles('masa').index(st.session_state.producto['unidad_peso']) 
                    if st.session_state.producto['unidad_peso'] in obtener_unidades_disponibles('masa') else 1,
                    key="unidad_peso_select"
                )
                st.session_state.producto['unidad_peso'] = unidad_peso  # GUARDAR
            
            col_empaque1, col_empaque2 = st.columns(2)
            with col_empaque1:
                # Usar el valor guardado en session_state
                peso_empaque = st.number_input(
                    "**Peso del empaque**", 
                    min_value=0.0,
                    value=st.session_state.producto['peso_empaque_valor'],  # CORREGIDO
                    step=0.000000001,
                    format="%.10f",
                    key="peso_empaque_input"
                )
                st.session_state.producto['peso_empaque_valor'] = peso_empaque  # GUARDAR
            with col_empaque2:
                unidad_empaque = st.selectbox(
                    "**Unidad empaque**",
                    options=obtener_unidades_disponibles('masa'),
                    index=obtener_unidades_disponibles('masa').index(st.session_state.producto['unidad_empaque']) 
                    if st.session_state.producto['unidad_empaque'] in obtener_unidades_disponibles('masa') else 1,
                    key="unidad_empaque_select"
                )
                st.session_state.producto['unidad_empaque'] = unidad_empaque  # GUARDAR
            
            # Convertir a kg para cálculos internos (SIEMPRE hacerlo)
            st.session_state.producto['peso_neto_kg'] = convertir_unidad(peso_neto, unidad_peso, 'kg')
            st.session_state.producto['peso_empaque_kg'] = convertir_unidad(peso_empaque, unidad_empaque, 'kg')
            st.session_state.producto['peso_neto'] = peso_neto  # Guardar valor original
            st.session_state.producto['peso_empaque'] = peso_empaque  # Guardar valor original
        
        # VALIDACIÓN DE COHERENCIA (NUEVO)
        if st.session_state.materias_primas and any(mp.get('producto') for mp in st.session_state.materias_primas):
            st.subheader("🔍 Validación de Coherencia")
            
            # Calcular total de materias primas usadas (en kg)
            total_mp_usadas_kg = sum(mp.get('cantidad_teorica_kg', 0) for mp in st.session_state.materias_primas if mp.get('producto'))
            total_empaques_kg = sum(emp.get('peso_kg', 0) * emp.get('cantidad', 1) for emp in st.session_state.empaques if emp.get('nombre'))
            
            peso_producto_definido_kg = st.session_state.producto['peso_neto_kg']
            
            # Mostrar comparación
            col_val1, col_val2, col_val3 = st.columns(3)
            with col_val1:
                st.metric("Peso producto definido", f"{formatear_numero(peso_producto_definido_kg)} kg")
            with col_val2:
                st.metric("MP usadas total", f"{formatear_numero(total_mp_usadas_kg)} kg")
            with col_val3:
                st.metric("Empaques total", f"{formatear_numero(total_empaques_kg)} kg")
            
            # Validar coherencia
            if total_mp_usadas_kg > 0:
                diferencia = abs(peso_producto_definido_kg - total_mp_usadas_kg)
                porcentaje_diferencia = (diferencia / max(peso_producto_definido_kg, total_mp_usadas_kg)) * 100
                
                if porcentaje_diferencia > 10:  # Más del 10% de diferencia
                    st.error(f"⚠️ **Posible incoherencia detectada:**")
                    st.write(f"- Diferencia: {formatear_numero(diferencia)} kg ({porcentaje_diferencia:.1f}%)")
                    st.write(f"- El peso del producto definido no coincide con la suma de materias primas usadas")
                    st.info("💡 **Sugerencia:** Verifica que las cantidades sean consistentes")
                else:
                    st.success("✅ **Datos coherentes** - Los pesos son consistentes")
        
        if st.form_submit_button("💾 **Guardar Producto**", type="primary"):
            if st.session_state.producto['nombre']:
                st.success("✅ **Producto guardado correctamente**")
                peso_total = peso_neto + peso_empaque
                st.metric("**Peso total**", f"{formatear_numero(peso_total)} {unidad_peso}")
            else:
                st.warning("⚠️ **Por favor ingresa un nombre para el producto**")
    
    # Información adicional sobre coherencia
    with st.expander("📖 **Información sobre validación de coherencia**"):
        st.markdown("""
        ### ¿Por qué validar la coherencia?
        
        Es importante que los datos sean consistentes entre las diferentes páginas:
        
        - **Peso del producto definido** debe ser similar a la **suma de materias primas usadas**
        - Considera que puede haber **pérdidas por merma** en la producción
        - Las **diferencias menores al 10%** se consideran aceptables
        - Diferencias mayores pueden indicar errores en los datos ingresados
        
        ### Ejemplo:
        - Si defines un producto de **30g** pero usas **200g** de materias primas
        - El sistema te alertará sobre esta posible incoherencia
        - Esto ayuda a detectar errores temprano
        """)

# Página 2: Materias Primas (CON COMPRA REAL VS TEÓRICA)
elif pagina == "2. Materias Primas":
    st.title("2. Materias Primas")
    st.info("🌱 Define las materias primas con cantidad COMPRADA (real) vs USADA (teórica)")
    
    opciones_materias_primas = obtener_opciones_categoria('materia_prima')
    
    if len(opciones_materias_primas) == 0:
        st.warning("⚠️ No hay materias primas definidas en la base de datos")
        opciones_materias_primas = ['Trigo', 'Maíz', 'Arroz', 'Leche entera', 'Carne de vacuno']
    
    # Preguntar número de materias primas
    st.subheader("📋 Configuración Inicial")
    num_materias = st.number_input(
        "**¿Cuántas materias primas diferentes utilizas?**",
        min_value=0,
        max_value=50,
        value=len(st.session_state.materias_primas) if st.session_state.materias_primas else 1
    )
    
    if num_materias > 0:
        st.subheader("📝 Ingreso de Materias Primas")
        
        # Limpiar lista si el número cambió
        if len(st.session_state.materias_primas) != num_materias:
            st.session_state.materias_primas = [{} for _ in range(num_materias)]
        
        # Crear campos para cada materia prima
        for i in range(num_materias):
            with st.expander(f"**Materia Prima {i+1}**", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Información básica
                    producto_seleccionado = st.selectbox(
                        f"**Producto**",
                        options=opciones_materias_primas,
                        key=f"producto_{i}",
                        index=0
                    )
                    
                    # Cantidad TEÓRICA (usada en el producto)
                    st.write("**Cantidad USADA en el producto (teórica):**")
                    col_teo1, col_teo2 = st.columns(2)
                    with col_teo1:
                        cantidad_teorica = st.number_input(
                            f"**Cantidad usada**",
                            min_value=0.0,
                            value=st.session_state.materias_primas[i].get('cantidad_teorica', 0.0) if i < len(st.session_state.materias_primas) else 0.0,
                            key=f"cantidad_teorica_{i}",
                            step=0.000000001,
                            format="%.10f"
                        )
                    with col_teo2:
                        unidad_teorica = st.selectbox(
                            f"**Unidad usada**",
                            options=obtener_unidades_disponibles('masa'),
                            key=f"unidad_teorica_{i}",
                            index=1  # kg por defecto
                        )
                
                with col2:
                    # Cantidad REAL (comprada)
                    st.write("**Cantidad COMPRADA (real con merma):**")
                    col_real1, col_real2 = st.columns(2)
                    with col_real1:
                        cantidad_real = st.number_input(
                            f"**Cantidad comprada**",
                            min_value=0.0,
                            value=st.session_state.materias_primas[i].get('cantidad_real', 0.0) if i < len(st.session_state.materias_primas) else 0.0,
                            key=f"cantidad_real_{i}",
                            step=0.000000001,
                            format="%.10f"
                        )
                    with col_real2:
                        unidad_real = st.selectbox(
                            f"**Unidad comprada**",
                            options=obtener_unidades_disponibles('masa'),
                            key=f"unidad_real_{i}",
                            index=1  # kg por defecto
                        )
                    
                    # Calcular merma automáticamente
                    if cantidad_real > 0 and cantidad_teorica > 0:
                        try:
                            # Convertir a misma unidad para cálculo
                            cantidad_teorica_conv = convertir_unidad(cantidad_teorica, unidad_teorica, unidad_real)
                            merma = cantidad_real - cantidad_teorica_conv
                            porcentaje_merma = (merma / cantidad_real) * 100 if cantidad_real > 0 else 0
                            
                            if merma > 0:
                                st.success(f"**Merma calculada:** {formatear_numero(merma)} {unidad_real} ({porcentaje_merma:.1f}%)")
                            elif merma == 0:
                                st.info("**Sin merma** - Cantidad comprada = cantidad usada")
                            else:
                                st.warning("**Cantidad usada > cantidad comprada** - Revisar datos")
                        except:
                            st.error("Error en conversión de unidades")
                
                # Empaque de la materia prima (opcional) - CORREGIDO
                with st.expander("📦 **Empaque de esta materia prima (opcional)**"):
                    tiene_empaque = st.checkbox(
                        "¿Esta materia prima viene empaquetada?",
                        value=bool(st.session_state.materias_primas[i].get('empaque')) if i < len(st.session_state.materias_primas) else False,
                        key=f"tiene_empaque_{i}"
                    )
                    
                    if tiene_empaque:
                        opciones_empaques = obtener_opciones_categoria('material_empaque')
                        col_emp1, col_emp2, col_emp3 = st.columns(3)
                        
                        with col_emp1:
                            material_empaque = st.selectbox(
                                f"**Material del empaque**",
                                options=opciones_empaques,
                                key=f"material_empaque_{i}"
                            )
                        
                        with col_emp2:
                            # INICIALIZACIÓN SEGURA del diccionario de empaque
                            if i >= len(st.session_state.materias_primas):
                                st.session_state.materias_primas.append({})
                            
                            if 'empaque' not in st.session_state.materias_primas[i]:
                                st.session_state.materias_primas[i]['empaque'] = {}
                                
                            peso_empaque = st.number_input(
                                f"**Peso del empaque**",
                                min_value=0.0,
                                value=float(st.session_state.materias_primas[i].get('empaque', {}).get('peso', 0.0)),
                                key=f"peso_empaque_{i}",
                                step=0.000000001,
                                format="%.10f"
                            )
                        
                        with col_emp3:
                            unidad_empaque = st.selectbox(
                                f"**Unidad empaque**",
                                options=obtener_unidades_disponibles('masa'),
                                key=f"unidad_empaque_{i}",
                                index=1
                            )
                        
                        st.session_state.materias_primas[i]['empaque'] = {
                            'material': material_empaque,
                            'peso': peso_empaque,
                            'unidad': unidad_empaque,
                            'peso_kg': convertir_unidad(peso_empaque, unidad_empaque, 'kg')
                        }
                    else:
                        st.session_state.materias_primas[i]['empaque'] = None
                
                # Guardar datos principales (en kg para cálculos)
                st.session_state.materias_primas[i]['producto'] = producto_seleccionado
                st.session_state.materias_primas[i]['cantidad_teorica'] = cantidad_teorica
                st.session_state.materias_primas[i]['unidad_teorica'] = unidad_teorica
                st.session_state.materias_primas[i]['cantidad_teorica_kg'] = convertir_unidad(cantidad_teorica, unidad_teorica, 'kg')
                
                st.session_state.materias_primas[i]['cantidad_real'] = cantidad_real
                st.session_state.materias_primas[i]['unidad_real'] = unidad_real
                st.session_state.materias_primas[i]['cantidad_real_kg'] = convertir_unidad(cantidad_real, unidad_real, 'kg')
                
                # Inicializar lista de transportes si no existe
                if 'transportes' not in st.session_state.materias_primas[i]:
                    st.session_state.materias_primas[i]['transportes'] = []
        
        # Mostrar resumen
        st.subheader("📊 Resumen de Materias Primas")
        if any(mp for mp in st.session_state.materias_primas if mp.get('producto')):
            datos_tabla = []
            total_comprado_kg = 0
            total_usado_kg = 0
            
            for i, mp in enumerate(st.session_state.materias_primas):
                if mp and mp.get('producto'):
                    # Calcular merma
                    merma_kg = mp.get('cantidad_real_kg', 0) - mp.get('cantidad_teorica_kg', 0)
                    porcentaje_merma = (merma_kg / mp.get('cantidad_real_kg', 1)) * 100 if mp.get('cantidad_real_kg', 0) > 0 else 0
                    
                    fila = {
                        'ID': i+1,
                        'Producto': mp.get('producto', 'No definido'),
                        'Comprado': f"{formatear_numero(mp.get('cantidad_real', 0))} {mp.get('unidad_real', '')}",
                        'Usado': f"{formatear_numero(mp.get('cantidad_teorica', 0))} {mp.get('unidad_teorica', '')}",
                        'Merma': f"{formatear_numero(merma_kg)} kg ({porcentaje_merma:.1f}%)",
                        'Con empaque': 'Sí' if mp.get('empaque') else 'No'
                    }
                    datos_tabla.append(fila)
                    
                    total_comprado_kg += mp.get('cantidad_real_kg', 0)
                    total_usado_kg += mp.get('cantidad_teorica_kg', 0)
            
            if datos_tabla:
                df_resumen = pd.DataFrame(datos_tabla)
                st.dataframe(df_resumen, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("**Total comprado**", f"{formatear_numero(total_comprado_kg)} kg")
                with col2:
                    st.metric("**Total usado**", f"{formatear_numero(total_usado_kg)} kg")
                
                merma_total_kg = total_comprado_kg - total_usado_kg
                if merma_total_kg > 0:
                    st.warning(f"**Merma total:** {formatear_numero(merma_total_kg)} kg")

# Página 3: Empaque del Producto (CON UNIDADES)
elif pagina == "3. Empaque del Producto":
    st.title("3. Empaque del Producto")
    st.info("📦 Caracteriza los empaques y packaging de tu producto final")
    
    opciones_empaques = obtener_opciones_categoria('material_empaque')
    
    st.subheader("📋 Configuración de Empaques")
    num_empaques = st.number_input(
        "**¿Cuántos tipos de empaque diferentes utilizas?**",
        min_value=0,
        max_value=20,
        value=len(st.session_state.empaques) if st.session_state.empaques else 1
    )
    
    if num_empaques > 0:
        st.subheader("📝 Ingreso de Empaques")
        
        if len(st.session_state.empaques) != num_empaques:
            st.session_state.empaques = [{} for _ in range(num_empaques)]
        
        for i in range(num_empaques):
            with st.expander(f"**Empaque {i+1}**", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    nombre_empaque = st.text_input(
                        f"**Nombre/descripción**",
                        value=st.session_state.empaques[i].get('nombre', ''),
                        placeholder="Ej: Caja principal, Bolsa interna, Etiqueta",
                        key=f"empaque_nombre_{i}"
                    )
                    
                    material_empaque = st.selectbox(
                        f"**Material**",
                        options=opciones_empaques,
                        key=f"empaque_material_{i}",
                        index=0
                    )
                
                with col2:
                    col_peso1, col_peso2, col_peso3 = st.columns([2, 2, 1])
                    with col_peso1:
                        peso_empaque = st.number_input(
                            f"**Peso unitario**",
                            min_value=0.0,
                            value=st.session_state.empaques[i].get('peso', 0.0),
                            key=f"empaque_peso_{i}",
                            step=0.001,
                            format="%.3f"
                        )
                    with col_peso2:
                        unidad_empaque = st.selectbox(
                            f"**Unidad**",
                            options=obtener_unidades_disponibles('masa'),
                            key=f"empaque_unidad_{i}",
                            index=1
                        )
                    with col_peso3:
                        cantidad = st.number_input(
                            f"**Cantidad**",
                            min_value=1,
                            value=st.session_state.empaques[i].get('cantidad', 1),
                            key=f"empaque_cantidad_{i}"
                        )
                
                # Inicializar transportes
                if 'transportes' not in st.session_state.empaques[i]:
                    st.session_state.empaques[i]['transportes'] = []
                
                st.session_state.empaques[i] = {
                    'nombre': nombre_empaque,
                    'material': material_empaque,
                    'peso': peso_empaque,
                    'unidad': unidad_empaque,
                    'cantidad': cantidad,
                    'peso_kg': convertir_unidad(peso_empaque, unidad_empaque, 'kg'),
                    'transportes': st.session_state.empaques[i]['transportes']
                }
        
        # Resumen de empaques
        st.subheader("📊 Resumen de Empaques")
        if any(emp for emp in st.session_state.empaques if emp.get('nombre')):
            datos_empaques = []
            peso_total_kg = 0
            
            for i, emp in enumerate(st.session_state.empaques):
                if emp and emp.get('nombre'):
                    peso_total_elemento = emp.get('peso_kg', 0) * emp.get('cantidad', 1)
                    datos_empaques.append({
                        'ID': i+1,
                        'Nombre': emp.get('nombre', 'Sin nombre'),
                        'Material': emp.get('material', 'No definido'),
                        'Peso unit.': f"{formatear_numero(emp.get('peso', 0))} {emp.get('unidad', '')}",
                        'Cantidad': emp.get('cantidad', 1),
                        'Peso total': f"{formatear_numero(peso_total_elemento)} kg"
                    })
                    peso_total_kg += peso_total_elemento
            
            if datos_empaques:
                df_empaques = pd.DataFrame(datos_empaques)
                st.dataframe(df_empaques, use_container_width=True)
                st.metric("**📦 Peso total de empaques**", f"{formatear_numero(peso_total_kg)} kg")

# Página 4: Transporte Materias Primas (CORREGIDA - todas visibles)
elif pagina == "4. Transporte Materias Primas":
    st.title("4. Transporte de Materias Primas")
    st.info("🚚 Define las rutas de transporte para CADA materia prima individualmente")
    
    if not st.session_state.materias_primas or not any(mp.get('producto') for mp in st.session_state.materias_primas):
        st.warning("⚠️ Primero ingresa materias primas en la página 2")
        st.stop()
    
    opciones_transporte = obtener_opciones_categoria('transporte')
    
    # Mostrar TODAS las materias primas en expansores
    st.subheader("📦 Configuración de Transporte por Materia Prima")
    
    for i, materia in enumerate(st.session_state.materias_primas):
        if not materia or not materia.get('producto'):
            continue
            
        with st.expander(f"**{i+1}. {materia['producto']}** - {formatear_numero(materia['cantidad_real'])} {materia['unidad_real']}", expanded=True):
            
            # Información de la materia prima
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Cantidad comprada", f"{formatear_numero(materia['cantidad_real'])} {materia['unidad_real']}")
            with col_info2:
                st.metric("Cantidad usada", f"{formatear_numero(materia['cantidad_teorica'])} {materia['unidad_teorica']}")
            with col_info3:
                merma_kg = materia.get('cantidad_real_kg', 0) - materia.get('cantidad_teorica_kg', 0)
                if merma_kg > 0:
                    st.metric("Merma", f"{formatear_numero(merma_kg)} kg")
                else:
                    st.metric("Merma", "0 kg")
            
            # Configurar número de rutas para esta materia prima
            num_rutas = st.number_input(
                f"**¿Cuántas rutas de transporte tiene {materia['producto']}?**",
                min_value=0,
                max_value=10,
                value=len(materia.get('transportes', [])),
                key=f"num_rutas_{i}"
            )
            
            # Ajustar lista de transportes
            if 'transportes' not in materia:
                materia['transportes'] = []
            
            if len(materia['transportes']) != num_rutas:
                materia['transportes'] = [{} for _ in range(num_rutas)]
            
            # Formulario para cada ruta
            if num_rutas > 0:
                st.write(f"**Rutas de transporte para {materia['producto']}:**")
                
                for j in range(num_rutas):
                    with st.container():
                        st.write(f"**Ruta {j+1}**")
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                        
                        with col1:
                            # Origen (con valor por defecto de ruta anterior si existe)
                            origen_default = ""
                            if j > 0 and materia['transportes'][j-1].get('destino'):
                                origen_default = materia['transportes'][j-1]['destino']
                            
                            origen = st.text_input(
                                f"Origen",
                                value=materia['transportes'][j].get('origen', origen_default),
                                placeholder="Ej: Atacama, Chile",
                                key=f"origen_{i}_{j}"
                            )
                        
                        with col2:
                            destino = st.text_input(
                                f"Destino",
                                value=materia['transportes'][j].get('destino', ''),
                                placeholder="Ej: Fábrica Santiago",
                                key=f"destino_{i}_{j}"
                            )
                        
                        with col3:
                            distancia = st.number_input(
                                f"Distancia (km)",
                                min_value=0.0,
                                value=materia['transportes'][j].get('distancia_km', 0.0),
                                key=f"distancia_{i}_{j}",
                                step=1.0,
                                format="%.1f"
                            )
                        
                        with col4:
                            transporte = st.selectbox(
                                f"Transporte",
                                options=opciones_transporte,
                                key=f"transporte_{i}_{j}",
                                index=0
                            )
                        
                        # Calcular carga en la MISMA unidad que ingresó el usuario
                        # En lugar de toneladas, usamos la unidad original
                        carga_en_unidad_original = materia['cantidad_real']  # Ya está en la unidad correcta
                        unidad_carga = materia['unidad_real']  # Unidad original del usuario
                        
                        # Guardar datos de la ruta
                        materia['transportes'][j] = {
                            'origen': origen,
                            'destino': destino,
                            'distancia_km': distancia,
                            'tipo_transporte': transporte,
                            'carga': carga_en_unidad_original,
                            'unidad_carga': unidad_carga,
                            'carga_kg': materia['cantidad_real_kg']  # Para cálculos internos
                        }
            
            # Mostrar resumen de rutas para esta materia prima
            rutas_validas = [r for r in materia.get('transportes', []) if r.get('origen') and r.get('destino')]
            
            if rutas_validas:
                st.subheader(f"📋 Rutas de {materia['producto']}")
                datos_rutas = []
                emisiones_materia = 0
                
                for k, ruta in enumerate(rutas_validas):
                    # Calcular emisiones para esta ruta
                    if ruta.get('distancia_km', 0) > 0:
                        factor = next((f for f in factores.to_dict('records') 
                                     if f['category'] == 'transporte' and f['item'] == ruta['tipo_transporte']), None)
                        if factor:
                            # Convertir carga a toneladas SOLO para cálculo (internamente)
                            carga_ton = ruta['carga_kg'] / 1000
                            emisiones_ruta = ruta['distancia_km'] * carga_ton * factor['factor_kgCO2e_per_unit']
                            emisiones_materia += emisiones_ruta
                    
                    datos_rutas.append({
                        'Ruta': k+1,
                        'Origen': ruta.get('origen', ''),
                        'Destino': ruta.get('destino', ''),
                        'Distancia': f"{formatear_numero(ruta.get('distancia_km', 0))} km",
                        'Transporte': ruta.get('tipo_transporte', ''),
                        'Carga': f"{formatear_numero(ruta.get('carga', 0))} {ruta.get('unidad_carga', '')}"
                    })
                
                if datos_rutas:
                    df_rutas = pd.DataFrame(datos_rutas)
                    st.dataframe(df_rutas, use_container_width=True)
                    
                    if emisiones_materia > 0:
                        st.metric(f"**Emisiones transporte {materia['producto']}**", 
                                 f"{formatear_numero(emisiones_materia)} kg CO₂e")
            else:
                st.info("💡 Configura las rutas de transporte para esta materia prima")
    
    # Resumen general de todas las materias primas
    st.markdown("---")
    st.subheader("📊 Resumen General de Transporte")
    
    total_rutas = sum(len(mp.get('transportes', [])) for mp in st.session_state.materias_primas if mp.get('producto'))
    rutas_completadas = sum(len([r for r in mp.get('transportes', []) if r.get('origen') and r.get('destino')]) 
                           for mp in st.session_state.materias_primas if mp.get('producto'))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Materias primas", len([mp for mp in st.session_state.materias_primas if mp.get('producto')]))
    with col2:
        st.metric("Rutas configuradas", total_rutas)
    with col3:
        st.metric("Rutas completadas", rutas_completadas)

# Página 5: Transporte Empaques (CORREGIDA - todas visibles)
elif pagina == "5. Transporte Empaques":
    st.title("5. Transporte de Empaques")
    st.info("📦 Define las rutas de transporte para CADA empaque individualmente")
    
    if not st.session_state.empaques or not any(emp.get('nombre') for emp in st.session_state.empaques):
        st.warning("⚠️ Primero ingresa empaques en la página 3")
        st.stop()
    
    opciones_transporte = obtener_opciones_categoria('transporte')
    
    # Mostrar TODOS los empaques en expansores
    st.subheader("📦 Configuración de Transporte por Empaque")
    
    for i, empaque in enumerate(st.session_state.empaques):
        if not empaque or not empaque.get('nombre'):
            continue
            
        # Calcular peso total del empaque
        peso_total = empaque.get('peso_kg', 0) * empaque.get('cantidad', 1)
        peso_total_unidad_original = empaque.get('peso', 0) * empaque.get('cantidad', 1)
        
        with st.expander(f"**{i+1}. {empaque['nombre']}** - {empaque['material']} ({formatear_numero(peso_total_unidad_original)} {empaque['unidad']})", expanded=True):
            
            # Información del empaque
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Material", empaque['material'])
            with col_info2:
                st.metric("Peso unitario", f"{formatear_numero(empaque['peso'])} {empaque['unidad']}")
            with col_info3:
                st.metric("Cantidad", empaque.get('cantidad', 1))
            
            # Configurar número de rutas para este empaque
            num_rutas = st.number_input(
                f"**¿Cuántas rutas de transporte tiene {empaque['nombre']}?**",
                min_value=0,
                max_value=10,
                value=len(empaque.get('transportes', [])),
                key=f"num_rutas_empaque_{i}"
            )
            
            # Ajustar lista de transportes
            if 'transportes' not in empaque:
                empaque['transportes'] = []
            
            if len(empaque['transportes']) != num_rutas:
                empaque['transportes'] = [{} for _ in range(num_rutas)]
            
            # Formulario para cada ruta
            if num_rutas > 0:
                st.write(f"**Rutas de transporte para {empaque['nombre']}:**")
                
                for j in range(num_rutas):
                    with st.container():
                        st.write(f"**Ruta {j+1}**")
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                        
                        with col1:
                            # Origen (con valor por defecto de ruta anterior si existe)
                            origen_default = ""
                            if j > 0 and empaque['transportes'][j-1].get('destino'):
                                origen_default = empaque['transportes'][j-1]['destino']
                            
                            origen = st.text_input(
                                f"Origen",
                                value=empaque['transportes'][j].get('origen', origen_default),
                                placeholder="Ej: Fábrica empaques",
                                key=f"origen_empaque_{i}_{j}"
                            )
                        
                        with col2:
                            destino = st.text_input(
                                f"Destino",
                                value=empaque['transportes'][j].get('destino', ''),
                                placeholder="Ej: Fábrica producto",
                                key=f"destino_empaque_{i}_{j}"
                            )
                        
                        with col3:
                            distancia = st.number_input(
                                f"Distancia (km)",
                                min_value=0.0,
                                value=empaque['transportes'][j].get('distancia_km', 0.0),
                                key=f"distancia_empaque_{i}_{j}",
                                step=1.0,
                                format="%.1f"
                            )
                        
                        with col4:
                            transporte = st.selectbox(
                                f"Transporte",
                                options=opciones_transporte,
                                key=f"transporte_empaque_{i}_{j}",
                                index=0
                            )
                        
                        # Guardar datos de la ruta (usando unidades originales)
                        empaque['transportes'][j] = {
                            'origen': origen,
                            'destino': destino,
                            'distancia_km': distancia,
                            'tipo_transporte': transporte,
                            'carga': peso_total_unidad_original,
                            'unidad_carga': empaque['unidad'],
                            'carga_kg': peso_total  # Para cálculos internos
                        }
            
            # Mostrar resumen de rutas para este empaque
            rutas_validas = [r for r in empaque.get('transportes', []) if r.get('origen') and r.get('destino')]
            
            if rutas_validas:
                st.subheader(f"📋 Rutas de {empaque['nombre']}")
                datos_rutas = []
                emisiones_empaque = 0
                
                for k, ruta in enumerate(rutas_validas):
                    # Calcular emisiones para esta ruta
                    if ruta.get('distancia_km', 0) > 0:
                        factor = next((f for f in factores.to_dict('records') 
                                     if f['category'] == 'transporte' and f['item'] == ruta['tipo_transporte']), None)
                        if factor:
                            # Convertir carga a toneladas SOLO para cálculo (internamente)
                            carga_ton = ruta['carga_kg'] / 1000
                            emisiones_ruta = ruta['distancia_km'] * carga_ton * factor['factor_kgCO2e_per_unit']
                            emisiones_empaque += emisiones_ruta
                    
                    datos_rutas.append({
                        'Ruta': k+1,
                        'Origen': ruta.get('origen', ''),
                        'Destino': ruta.get('destino', ''),
                        'Distancia': f"{formatear_numero(ruta.get('distancia_km', 0))} km",
                        'Transporte': ruta.get('tipo_transporte', ''),
                        'Carga': f"{formatear_numero(ruta.get('carga', 0))} {ruta.get('unidad_carga', '')}"
                    })
                
                if datos_rutas:
                    df_rutas = pd.DataFrame(datos_rutas)
                    st.dataframe(df_rutas, use_container_width=True)
                    
                    if emisiones_empaque > 0:
                        st.metric(f"**Emisiones transporte {empaque['nombre']}**", 
                                 f"{formatear_numero(emisiones_empaque)} kg CO₂e")
            else:
                st.info("💡 Configura las rutas de transporte para este empaque")
    
    # Resumen general de todos los empaques
    st.markdown("---")
    st.subheader("📊 Resumen General de Transporte")
    
    total_rutas = sum(len(emp.get('transportes', [])) for emp in st.session_state.empaques if emp.get('nombre'))
    rutas_completadas = sum(len([r for r in emp.get('transportes', []) if r.get('origen') and r.get('destino')]) 
                           for emp in st.session_state.empaques if emp.get('nombre'))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Empaques", len([emp for emp in st.session_state.empaques if emp.get('nombre')]))
    with col2:
        st.metric("Rutas configuradas", total_rutas)
    with col3:
        st.metric("Rutas completadas", rutas_completadas)

# Página 6: Producción y Mermas (COMPLETA CORREGIDA - FASE 2)
elif pagina == "6. Producción y Mermas":
    st.title("6. Producción y Gestión de Mermas")
    st.info("⚡ Define los consumos de producción y gestiona las mermas de materiales")
    
    # Verificar que hay datos previos necesarios
    if not st.session_state.materias_primas or not any(mp.get('producto') for mp in st.session_state.materias_primas):
        st.warning("⚠️ Primero ingresa materias primas en la página 2")
        st.stop()
    
    if not st.session_state.producto.get('nombre'):
        st.warning("⚠️ Primero define un producto en la página 1")
        st.stop()
    
    # CORRECCIÓN: Convertir arrays de NumPy a listas
    opciones_energia = list(obtener_opciones_categoria('energia'))
    opciones_gestion = ['Vertedero', 'Incineración', 'Compostaje', 'Reciclaje']
    opciones_transporte = list(obtener_opciones_categoria('transporte'))
    
    # Calcular mermas automáticamente desde los datos de página 2
    mermas_calculadas = []
    for i, mp in enumerate(st.session_state.materias_primas):
        if mp and mp.get('producto'):
            merma_kg = mp.get('cantidad_real_kg', 0) - mp.get('cantidad_teorica_kg', 0)
            if merma_kg > 0.0001:  # Solo considerar mermas significativas (> 0.1g)
                mermas_calculadas.append({
                    'id': i,
                    'tipo': 'materia_prima',
                    'nombre': mp['producto'],
                    'merma_kg': merma_kg,
                    'merma_original': mp.get('cantidad_real', 0) - mp.get('cantidad_teorica', 0),
                    'unidad_original': mp.get('unidad_real', 'kg'),
                    'material': mp['producto']
                })
    
    # Inicializar estructura de producción si no existe
    if 'mermas_gestionadas' not in st.session_state.produccion:
        st.session_state.produccion['mermas_gestionadas'] = []
    if 'residuos_empaques' not in st.session_state.produccion:
        st.session_state.produccion['residuos_empaques'] = []
    
    with st.form("produccion_mermas"):
        # SECCIÓN 1: CONSUMOS DE PRODUCCIÓN
        st.subheader("⚡ Consumos de Producción")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.produccion['energia_kwh'] = st.number_input(
                "**Consumo de energía (kWh)**", 
                min_value=0.0,
                value=st.session_state.produccion['energia_kwh'],
                step=1.0,
                format="%.1f",
                help="Energía total consumida en el proceso productivo"
            )
            
            # CORRECCIÓN: Manejar índice de manera segura
            tipo_energia_actual = st.session_state.produccion['tipo_energia']
            indice_actual = 0
            if tipo_energia_actual in opciones_energia:
                indice_actual = opciones_energia.index(tipo_energia_actual)
            
            st.session_state.produccion['tipo_energia'] = st.selectbox(
                "**Tipo de energía**",
                options=opciones_energia,
                index=indice_actual
            )
        
        with col2:
            st.session_state.produccion['agua_m3'] = st.number_input(
                "**Consumo de agua (m³)**", 
                min_value=0.0,
                value=st.session_state.produccion['agua_m3'],
                step=0.1,
                format="%.2f",
                help="Agua utilizada en el proceso productivo"
            )
            
            # Opcional: otros consumos
            st.session_state.produccion['otros_consumos'] = st.number_input(
                "**Otros consumos (opcional)**", 
                min_value=0.0,
                value=st.session_state.produccion.get('otros_consumos', 0.0),
                step=0.1,
                format="%.2f",
                help="Otros consumos (gas, vapor, etc.)"
            )
            st.session_state.produccion['unidad_otros'] = st.text_input(
                "Unidad otros consumos",
                value=st.session_state.produccion.get('unidad_otros', ''),
                placeholder="Ej: m³ gas, kg vapor",
                help="Unidad de los otros consumos"
            )
        
        # SECCIÓN 2: GESTIÓN DE MERMAS (AUTOMÁTICA DESDE PÁGINA 2)
        st.subheader("📊 Gestión de Mermas")
        
        if not mermas_calculadas:
            st.info("💡 No se detectaron mermas significativas en las materias primas ingresadas")
        else:
            st.success(f"✅ Se detectaron {len(mermas_calculadas)} materiales con merma")
            
            for merma in mermas_calculadas:
                with st.expander(f"**{merma['nombre']}** - Merma: {formatear_numero(merma['merma_original'])} {merma['unidad_original']}", expanded=True):
                    
                    # Buscar si ya existe gestión para esta merma
                    gestion_existente = next((g for g in st.session_state.produccion['mermas_gestionadas'] 
                                            if g.get('id_material') == merma['id'] and g.get('tipo') == 'merma'), None)
                    
                    col_m1, col_m2 = st.columns(2)
                    
                    with col_m1:
                        # CORRECCIÓN: Manejar índice de gestión existente
                        gestion_actual = gestion_existente['tipo_gestion'] if gestion_existente else 'Vertedero'
                        indice_gestion = opciones_gestion.index(gestion_actual) if gestion_actual in opciones_gestion else 0
                        
                        gestion = st.selectbox(
                            f"**Gestión para {merma['nombre']}**",
                            options=opciones_gestion,
                            index=indice_gestion,
                            key=f"gestion_{merma['id']}"
                        )
                    
                    with col_m2:
                        # Transporte de la merma
                        distancia = st.number_input(
                            f"**Distancia transporte (km)**",
                            min_value=0.0,
                            value=gestion_existente.get('distancia_km', 0.0) if gestion_existente else 0.0,
                            step=1.0,
                            format="%.1f",
                            key=f"distancia_{merma['id']}"
                        )
                        
                        # CORRECCIÓN: Manejar índice de transporte existente
                        transporte_actual = gestion_existente.get('tipo_transporte', 'Camión diesel') if gestion_existente else 'Camión diesel'
                        indice_transporte = opciones_transporte.index(transporte_actual) if transporte_actual in opciones_transporte else 0
                        
                        transporte = st.selectbox(
                            f"**Transporte**",
                            options=opciones_transporte,
                            index=indice_transporte,
                            key=f"transporte_{merma['id']}"
                        )
                    
                    # Guardar/actualizar gestión
                    gestion_actualizada = {
                        'id_material': merma['id'],
                        'tipo': 'merma',
                        'nombre_material': merma['nombre'],
                        'cantidad_kg': merma['merma_kg'],
                        'tipo_gestion': gestion,
                        'distancia_km': distancia,
                        'tipo_transporte': transporte
                    }
                    
                    # Actualizar lista
                    if gestion_existente:
                        index = st.session_state.produccion['mermas_gestionadas'].index(gestion_existente)
                        st.session_state.produccion['mermas_gestionadas'][index] = gestion_actualizada
                    else:
                        st.session_state.produccion['mermas_gestionadas'].append(gestion_actualizada)
        
        # SECCIÓN 3: RESIDUOS DE EMPAQUES (MANUAL)
        st.subheader("🗑️ Residuos de Empaques en Producción")
        st.info("Empaques que se descartan o dañan durante la producción")
        
        # Listar empaques existentes para selección
        empaques_disponibles = []
        for i, emp in enumerate(st.session_state.empaques):
            if emp and emp.get('nombre'):
                empaques_disponibles.append({
                    'id': i,
                    'nombre': emp['nombre'],
                    'material': emp['material'],
                    'peso_unitario_kg': emp.get('peso_kg', 0)
                })
        
        # Gestión de residuos de empaques
        num_residuos = st.number_input(
            "**¿Cuántos tipos de empaques se descartan en producción?**",
            min_value=0,
            max_value=10,
            value=len(st.session_state.produccion['residuos_empaques']),
            key="num_residuos_empaques"
        )
        
        if num_residuos > 0:
            # Ajustar lista
            if len(st.session_state.produccion['residuos_empaques']) != num_residuos:
                st.session_state.produccion['residuos_empaques'] = [{} for _ in range(num_residuos)]
            
            for i in range(num_residuos):
                with st.expander(f"Residuo de Empaque {i+1}", expanded=True):
                    col_r1, col_r2, col_r3 = st.columns(3)
                    
                    with col_r1:
                        # Seleccionar empaque
                        opciones_empaques_nombres = [f"{e['nombre']} ({e['material']})" for e in empaques_disponibles]
                        if opciones_empaques_nombres:
                            # CORRECCIÓN: Manejar residuo existente
                            residuo_existente = st.session_state.produccion['residuos_empaques'][i]
                            indice_empaque = 0
                            if residuo_existente and residuo_existente.get('nombre_empaque'):
                                nombre_buscado = f"{residuo_existente['nombre_empaque']} ({residuo_existente['material']})"
                                if nombre_buscado in opciones_empaques_nombres:
                                    indice_empaque = opciones_empaques_nombres.index(nombre_buscado)
                            
                            empaque_seleccionado = st.selectbox(
                                f"Empaque",
                                options=opciones_empaques_nombres,
                                index=indice_empaque,
                                key=f"empaque_residuo_{i}"
                            )
                            
                            # Obtener empaque seleccionado
                            empaque_idx = opciones_empaques_nombres.index(empaque_seleccionado)
                            empaque_seleccionado_data = empaques_disponibles[empaque_idx]
                    
                    with col_r2:
                        cantidad = st.number_input(
                            f"Cantidad descartada",
                            min_value=0,
                            value=residuo_existente.get('cantidad', 0) if residuo_existente else 0,
                            key=f"cantidad_residuo_{i}"
                        )
                        
                        # CORRECCIÓN: Manejar gestión existente
                        gestion_actual = residuo_existente.get('tipo_gestion', 'Vertedero') if residuo_existente else 'Vertedero'
                        indice_gestion_residuo = opciones_gestion.index(gestion_actual) if gestion_actual in opciones_gestion else 0
                        
                        gestion = st.selectbox(
                            f"Gestión",
                            options=opciones_gestion,
                            index=indice_gestion_residuo,
                            key=f"gestion_residuo_{i}"
                        )
                    
                    with col_r3:
                        distancia = st.number_input(
                            f"Distancia transporte (km)",
                            min_value=0.0,
                            value=residuo_existente.get('distancia_km', 0.0) if residuo_existente else 0.0,
                            step=1.0,
                            format="%.1f",
                            key=f"distancia_residuo_{i}"
                        )
                        
                        # CORRECCIÓN: Manejar transporte existente
                        transporte_actual = residuo_existente.get('tipo_transporte', 'Camión diesel') if residuo_existente else 'Camión diesel'
                        indice_transporte_residuo = opciones_transporte.index(transporte_actual) if transporte_actual in opciones_transporte else 0
                        
                        transporte = st.selectbox(
                            f"Transporte",
                            options=opciones_transporte,
                            index=indice_transporte_residuo,
                            key=f"transporte_residuo_{i}"
                        )
                    
                    # Guardar residuo
                    if empaques_disponibles:
                        st.session_state.produccion['residuos_empaques'][i] = {
                            'id_empaque': empaque_seleccionado_data['id'],
                            'nombre_empaque': empaque_seleccionado_data['nombre'],
                            'material': empaque_seleccionado_data['material'],
                            'cantidad': cantidad,
                            'peso_unitario_kg': empaque_seleccionado_data['peso_unitario_kg'],
                            'tipo_gestion': gestion,
                            'distancia_km': distancia,
                            'tipo_transporte': transporte
                        }
        
        # SECCIÓN 4: CÁLCULOS Y VALIDACIONES
        st.subheader("📈 Balance y Eficiencia")
        
        # Calcular eficiencia
        total_mp_usadas_kg = sum(mp.get('cantidad_teorica_kg', 0) for mp in st.session_state.materias_primas if mp.get('producto'))
        peso_producto_kg = st.session_state.producto.get('peso_neto_kg', 0)
        
        if total_mp_usadas_kg > 0 and peso_producto_kg > 0:
            eficiencia = (peso_producto_kg / total_mp_usadas_kg) * 100
            
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                st.metric("MP usadas", f"{formatear_numero(total_mp_usadas_kg)} kg")
            with col_e2:
                st.metric("Producto terminado", f"{formatear_numero(peso_producto_kg)} kg")
            with col_e3:
                st.metric("Eficiencia", f"{eficiencia:.1f}%")
            
            # Validar eficiencia
            if eficiencia < 50:
                st.error("⚠️ Eficiencia muy baja (<50%). Revisa los datos.")
            elif eficiencia > 100:
                st.warning("⚠️ Eficiencia >100%. El producto pesa más que las MP usadas.")
            else:
                st.success("✅ Eficiencia dentro de rangos razonables")
        
        # Balance de masa - CORRECCIÓN: variable diferencia_balance
        total_entradas_kg = total_mp_usadas_kg
        total_salidas_kg = peso_producto_kg + sum(m['merma_kg'] for m in mermas_calculadas)
        
        diferencia_balance = total_entradas_kg - total_salidas_kg
        if abs(diferencia_balance) > 0.001:  # Tolerancia de 1g
            st.warning(f"⚠️ Desbalance de masa: {formatear_numero(diferencia_balance)} kg")  # CORREGIDO
        
        if st.form_submit_button("💾 **Guardar Datos de Producción**", type="primary"):
            st.success("✅ **Datos de producción guardados correctamente**")
    
    # RESUMEN FINAL
    st.markdown("---")
    st.subheader("📊 Resumen de Producción")
    
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        mermas_activas = [m for m in st.session_state.produccion['mermas_gestionadas'] if m]
        st.metric("Mermas gestionadas", len(mermas_activas))
    with col_r2:
        residuos_activos = [r for r in st.session_state.produccion['residuos_empaques'] if r]
        st.metric("Residuos empaques", len(residuos_activos))
    with col_r3:
        consumo_total_kwh = st.session_state.produccion['energia_kwh']
        st.metric("Consumo energía", f"{formatear_numero(consumo_total_kwh)} kWh")

# Página 7: Distribución (REDISEÑADA - Robustecida)
elif pagina == "7. Distribución":
    st.title("7. Distribución del Producto")
    st.info("🚚 Define los canales de distribución en 2 pasos simples")
    
    # Verificación básica
    if not st.session_state.producto.get('nombre') or st.session_state.producto.get('peso_neto_kg', 0) <= 0:
        st.warning("⚠️ Primero define un producto con peso en la página 1")
        st.stop()
    
    # CALCULAR PESO TOTAL CORREGIDO: Producto + Empaques
    peso_producto_kg = st.session_state.producto.get('peso_neto_kg', 0)
    
    # Calcular peso total de empaques del producto
    peso_empaques_total_kg = 0
    for emp in st.session_state.empaques:
        if emp and emp.get('nombre'):
            peso_unitario_kg = emp.get('peso_kg', 0)
            cantidad = emp.get('cantidad', 1)
            peso_empaques_total_kg += peso_unitario_kg * cantidad
    
    # Peso total a distribuir: Producto + Empaques
    peso_total_distribuir_kg = peso_producto_kg + peso_empaques_total_kg
    
    st.success(f"📦 **Peso total a distribuir:** {formatear_numero(peso_total_distribuir_kg, 4)} kg "
              f"(Producto: {formatear_numero(peso_producto_kg, 4)} kg + "
              f"Empaques: {formatear_numero(peso_empaques_total_kg, 4)} kg)")
    
    # INICIALIZACIÓN ROBUSTA
    if 'canales' not in st.session_state.distribucion:
        st.session_state.distribucion['canales'] = [{'nombre': 'Canal Principal', 'porcentaje': 100.0, 'rutas': [{}]}]
    
    # Garantizar lista no vacía
    if not st.session_state.distribucion['canales']:
        st.session_state.distribucion['canales'] = [{'nombre': 'Canal Principal', 'porcentaje': 100.0, 'rutas': [{}]}]
    
    opciones_transporte = list(obtener_opciones_categoria('transporte'))
    
    # --- PASO 1: CONFIGURACIÓN BÁSICA (FUERA DEL FORM) ---
    st.subheader("📋 Paso 1: Configuración Básica de Canales")
    
    with st.container():
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            # Control simple de número de canales
            num_canales_actual = len(st.session_state.distribucion['canales'])
            nuevo_num_canales = st.number_input(
                "**Número de canales de distribución**",
                min_value=1,
                max_value=5,  # Reducido para mayor estabilidad
                value=num_canales_actual,
                key="num_canales_control",
                help="Máximo 5 canales para mejor rendimiento"
            )
        
        with col_p2:
            if st.button("🔄 Aplicar número de canales", type="secondary"):
                if nuevo_num_canales != num_canales_actual:
                    # Actualización CONTROLADA y EXPLÍCITA
                    if nuevo_num_canales > num_canales_actual:
                        # Agregar nuevos canales
                        for i in range(num_canales_actual, nuevo_num_canales):
                            st.session_state.distribucion['canales'].append({
                                'nombre': f'Canal {i+1}', 
                                'porcentaje': 0.0, 
                                'rutas': [{}]
                            })
                    else:
                        # Reducir canales (con confirmación para datos importantes)
                        canales_con_rutas = [c for c in st.session_state.distribucion['canales'] 
                                           if any(r.get('origen') for r in c.get('rutas', []))]
                        
                        if nuevo_num_canales < len(canales_con_rutas):
                            st.warning(f"⚠️ Al reducir a {nuevo_num_canales} canales, se perderán datos de {len(canales_con_rutas) - nuevo_num_canales} canales con rutas configuradas.")
                            if st.button("✅ Confirmar reducción (pérdida de datos)", type="primary"):
                                st.session_state.distribucion['canales'] = st.session_state.distribucion['canales'][:nuevo_num_canales]
                                st.rerun()
                        else:
                            st.session_state.distribucion['canales'] = st.session_state.distribucion['canales'][:nuevo_num_canales]
                            st.rerun()
        
        # Configuración simple de porcentajes (FUERA del form principal)
        st.write("**Distribución porcentual por canal:**")
        porcentaje_total = 0.0
        
        for i in range(len(st.session_state.distribucion['canales'])):
            col_perc1, col_perc2 = st.columns([3, 1])
            with col_perc1:
                nombre = st.text_input(
                    f"Nombre canal {i+1}",
                    value=st.session_state.distribucion['canales'][i].get('nombre', f'Canal {i+1}'),
                    key=f"nombre_simple_{i}"
                )
                st.session_state.distribucion['canales'][i]['nombre'] = nombre
            
            with col_perc2:
                porcentaje = st.number_input(
                    f"% Canal {i+1}",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(st.session_state.distribucion['canales'][i].get('porcentaje', 0.0)),
                    step=1.0,
                    format="%.1f",
                    key=f"porcentaje_simple_{i}"
                )
                st.session_state.distribucion['canales'][i]['porcentaje'] = porcentaje
                porcentaje_total += porcentaje
        
        # Validación básica de porcentajes
        col_val1, col_val2 = st.columns(2)
        with col_val1:
            st.metric("Suma porcentajes", f"{porcentaje_total:.1f}%")
        with col_val2:
            if abs(porcentaje_total - 100.0) < 0.1:
                st.success("✅ Suma correcta")
            else:
                st.error("❌ Ajusta los porcentajes")
    
    st.markdown("---")
    
    # --- PASO 2: CONFIGURACIÓN DETALLADA (DENTRO DEL FORM) ---
    st.subheader("🚚 Paso 2: Configuración de Rutas de Transporte")
    
    with st.form("distribucion_detallada"):
        # Solo procesar si los porcentajes son correctos
        if abs(porcentaje_total - 100.0) > 0.1:
            st.error("❌ Primero ajusta los porcentajes en el Paso 1")
            st.form_submit_button("💾 Guardar Configuración", disabled=True)
        else:
            # Configuración detallada por canal
            for i, canal in enumerate(st.session_state.distribucion['canales']):
                with st.expander(f"**{canal['nombre']}** - {canal['porcentaje']:.1f}%", expanded=i==0):
                    # Calcular peso distribuido CORREGIDO: Incluye empaques
                    peso_distribuido = (peso_total_distribuir_kg * canal['porcentaje']) / 100
                    canal['peso_distribuido_kg'] = peso_distribuido
                    
                    st.write(f"**Peso a distribuir:** {formatear_numero(peso_distribuido, 4)} kg")
                    st.write(f"💡 *Incluye: Producto ({formatear_numero((peso_producto_kg * canal['porcentaje']) / 100, 4)} kg) + "
                            f"Empaques ({formatear_numero((peso_empaques_total_kg * canal['porcentaje']) / 100, 4)} kg)*")
                    
                    # Configuración de rutas para este canal
                    if 'rutas' not in canal:
                        canal['rutas'] = [{}]
                    
                    # Control simple de número de rutas
                    num_rutas_actual = len(canal['rutas'])
                    num_rutas = st.number_input(
                        f"Número de rutas para {canal['nombre']}",
                        min_value=1,
                        max_value=3,  # Limitado para rendimiento
                        value=num_rutas_actual,
                        key=f"num_rutas_{i}"
                    )
                    
                    # Ajustar número de rutas (sin auto-actualización)
                    if num_rutas != num_rutas_actual:
                        if st.button(f"🔄 Aplicar {num_rutas} rutas para {canal['nombre']}", key=f"aplicar_rutas_{i}"):
                            if num_rutas > num_rutas_actual:
                                canal['rutas'].extend([{} for _ in range(num_rutas - num_rutas_actual)])
                            else:
                                canal['rutas'] = canal['rutas'][:num_rutas]
                            st.rerun()
                    
                    # Configurar cada ruta (SIN AUTORELLENADO)
                    for j, ruta in enumerate(canal['rutas']):
                        st.write(f"**Ruta {j+1}**")
                        col_r1, col_r2, col_r3, col_r4 = st.columns([2, 2, 1, 1])
                        
                        with col_r1:
                            origen = st.text_input(
                                "Origen",
                                value=ruta.get('origen', ''),
                                placeholder="Ingresa origen manualmente",
                                key=f"origen_{i}_{j}"
                            )
                            ruta['origen'] = origen
                        
                        with col_r2:
                            destino = st.text_input(
                                "Destino", 
                                value=ruta.get('destino', ''),
                                placeholder="Ingresa destino manualmente",
                                key=f"destino_{i}_{j}"
                            )
                            ruta['destino'] = destino
                        
                        with col_r3:
                            distancia = st.number_input(
                                "Distancia (km)",
                                min_value=0.0,
                                value=float(ruta.get('distancia_km', 0.0)),
                                step=0.1,
                                format="%.1f",
                                key=f"distancia_{i}_{j}"
                            )
                            ruta['distancia_km'] = distancia
                        
                        with col_r4:
                            transporte = st.selectbox(
                                "Transporte",
                                options=opciones_transporte,
                                index=0,
                                key=f"transporte_{i}_{j}"
                            )
                            ruta['tipo_transporte'] = transporte
                        
                        # CARGA CORREGIDA: Incluye producto + empaques
                        ruta['carga_kg'] = peso_distribuido
            
            # Botón de guardado final
            if st.form_submit_button("💾 **Guardar Configuración Completa**", type="primary"):
                st.success("✅ **Configuración de distribución guardada correctamente**")
                st.info(f"📦 **Peso total en distribución:** {formatear_numero(peso_total_distribuir_kg, 4)} kg "
                       f"(Producto + Empaques)")
    
    # --- RESUMEN FINAL ---
    st.markdown("---")
    st.subheader("📊 Resumen de Distribución")
    
    # Cálculo de emisiones para el resumen
    emisiones_totales = 0
    datos_resumen = []
    
    for canal in st.session_state.distribucion['canales']:
        if canal.get('nombre'):
            rutas_validas = [r for r in canal.get('rutas', []) if r.get('origen')]
            distancia_total = sum(r.get('distancia_km', 0) for r in rutas_validas)
            
            # Calcular emisiones para este canal
            emisiones_canal = 0
            for ruta in rutas_validas:
                if ruta.get('distancia_km', 0) > 0:
                    factor = next((f for f in factores.to_dict('records') 
                                 if f['category'] == 'transporte' and f['item'] == ruta['tipo_transporte']), None)
                    if factor:
                        carga_ton = ruta.get('carga_kg', 0) / 1000
                        emisiones_canal += ruta['distancia_km'] * carga_ton * factor['factor_kgCO2e_per_unit']
            
            emisiones_totales += emisiones_canal
            
            # CONVERTIR A g CO₂e y formatear con máximo 4 decimales
            emisiones_canal_g = emisiones_canal * 1000
            
            datos_resumen.append({
                'Canal': canal['nombre'],
                'Porcentaje': f"{canal['porcentaje']:.1f}%",
                'Peso': f"{formatear_numero(canal.get('peso_distribuido_kg', 0), 4)} kg",
                'Rutas': len(rutas_validas),
                'Distancia': f"{formatear_numero(distancia_total, 1)} km",  # 1 decimal para distancias
                'Huella Carbono': f"{formatear_numero(emisiones_canal_g, 4)} g CO₂e"  # Cambiado a g CO₂e
            })
    
    if datos_resumen:
        df_resumen = pd.DataFrame(datos_resumen)
        st.dataframe(df_resumen, use_container_width=True)
        
        # Mostrar emisiones totales en g CO₂e
        emisiones_totales_g = emisiones_totales * 1000
        st.success(f"**Huella de carbono total estimada: {formatear_numero(emisiones_totales_g, 4)} g CO₂e**")
        
        # Mostrar desglose del peso total
        st.info(f"🔍 **Desglose del peso total en distribución:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Producto", f"{formatear_numero(peso_producto_kg, 4)} kg")
        with col2:
            st.metric("Empaques", f"{formatear_numero(peso_empaques_total_kg, 4)} kg")
        with col3:
            st.metric("Total", f"{formatear_numero(peso_total_distribuir_kg, 4)} kg")
    
# Página 8: Retail
elif pagina == "8. Retail":
    st.title("8. Almacenamiento en Retail")
    st.info("🏪 Define las condiciones de almacenamiento del producto en el punto de venta")
    
    # Verificación básica de datos previos
    if not st.session_state.producto.get('nombre'):
        st.warning("⚠️ Primero define un producto en la página 1")
        st.stop()
    
    # Inicializar estructura de retail si no existe
    if 'retail' not in st.session_state:
        st.session_state.retail = {}
        
    # Inicializar valores por defecto si no existen
    if 'dias_almacenamiento' not in st.session_state.retail:
        st.session_state.retail['dias_almacenamiento'] = 7
    if 'tipo_almacenamiento' not in st.session_state.retail:
        st.session_state.retail['tipo_almacenamiento'] = 'temperatura_ambiente'
    if 'consumo_energia_kwh' not in st.session_state.retail:
        st.session_state.retail['consumo_energia_kwh'] = 0.0
    
    # Definir opciones simples de almacenamiento
    opciones_almacenamiento = {
        'temperatura_ambiente': {
            'nombre': 'Temperatura ambiente (estante)',
            'factor_energia': 0.784931507  # kWh por día (iluminación básica)
        },
        'congelado': {
            'nombre': 'Congelado/Refrigerado',
            'factor_energia': 0.8  # kWh por día (refrigeración/congelación)
        }
    }
    
    with st.form("retail_form"):
        st.subheader("📦 Condiciones de Almacenamiento en Retail")
        
        # 1. Tiempo en retail
        dias = st.number_input(
            "**¿Cuántos días permanece el producto en el punto de venta?**",
            min_value=1,
            max_value=365,
            value=st.session_state.retail['dias_almacenamiento'],
            help="Tiempo estimado desde que llega al retail hasta la venta"
        )
        
        # 2. Tipo de almacenamiento
        tipo_almacenamiento = st.radio(
            "**¿En qué condiciones se almacena el producto?**",
            options=[opt['nombre'] for opt in opciones_almacenamiento.values()],
            index=0
        )
        
        # Identificar tipo seleccionado
        tipo_key = [k for k, v in opciones_almacenamiento.items() 
                   if v['nombre'] == tipo_almacenamiento][0]
        
        # Campo de consumo energético personalizado para refrigeración/congelación
        consumo_personalizado = None
        if tipo_key == 'congelado':
            consumo_sugerido = opciones_almacenamiento[tipo_key]['factor_energia'] * dias
            st.info(f"💡 Consumo sugerido: {formatear_numero(consumo_sugerido)} kWh por día")
            
            consumo_personalizado = st.number_input(
                "**Consumo energético diario (kWh/día)**",
                min_value=0.0,
                value=float(opciones_almacenamiento[tipo_key]['factor_energia']),
                step=0.000000001,
                format="%.10f",
                help="Puede ajustar el consumo según las condiciones específicas del retail"
            )
        
        if st.form_submit_button("💾 Guardar Configuración"):
            try:
                # Calcular consumo total
                if tipo_key == 'congelado' and consumo_personalizado:
                    consumo_total = consumo_personalizado * dias
                else:
                    consumo_total = opciones_almacenamiento[tipo_key]['factor_energia'] * dias
                
                st.session_state.retail.update({
                    'dias_almacenamiento': dias,
                    'tipo_almacenamiento': tipo_key,
                    'consumo_energia_kwh': consumo_total
                })
                
                # Calcular emisiones por consumo eléctrico
                try:
                    factor_electricidad = obtener_factor(factores, 'energia', 'electricidad')
                    if isinstance(factor_electricidad, tuple):
                        factor_electricidad = factor_electricidad[0]  # Tomar solo el valor numérico
                    
                    # Asegurarse de que ambos sean números
                    consumo_kwh = float(consumo_total)
                    factor_num = float(factor_electricidad)
                    
                    emisiones = consumo_kwh * factor_num
                    st.session_state.retail['emisiones_estimadas'] = emisiones
                    
                    st.success("✅ Configuración guardada correctamente")
                    st.success(f"📊 Emisiones estimadas: {formatear_numero(emisiones)} kg CO₂e")
                    
                except Exception as e:
                    st.error(f"❌ Error al calcular emisiones: {str(e)}")
                    st.session_state.retail['emisiones_estimadas'] = 0.0
                    
            except Exception as e:
                st.error(f"❌ Error al guardar configuración: {str(e)}")
    
    # Mostrar resumen si hay datos
    if st.session_state.retail.get('emisiones_estimadas') is not None:
        st.markdown("---")
        st.subheader("📊 Resumen")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Días en retail",
                f"{st.session_state.retail['dias_almacenamiento']} días"
            )
        with col2:
            st.metric(
                "Consumo total",
                f"{formatear_numero(st.session_state.retail['consumo_energia_kwh'])} kWh"
            )
        with col3:
            st.metric(
                "Emisiones estimadas",
                f"{formatear_numero(st.session_state.retail['emisiones_estimadas'])} kg CO₂e"
            )
    
elif pagina == "9. Uso y Fin de Vida":
    st.title("9. Uso y Fin de Vida")
    st.info("🔄 Define los consumos durante el uso del producto y la gestión final de empaques")
    
    # Verificación básica de datos previos
    if not st.session_state.producto.get('nombre'):
        st.warning("⚠️ Primero define un producto en la página 1")
        st.stop()
    
    if not st.session_state.empaques or not any(emp.get('nombre') for emp in st.session_state.empaques):
        st.warning("⚠️ Primero define los empaques del producto en la página 3")
        st.stop()
    
    # Inicializar estructura si no existe
    if 'uso_fin_vida' not in st.session_state:
        st.session_state.uso_fin_vida = {
            'tiene_consumos': False,
            'consumo_energia_kwh': 0.0,
            'consumo_agua_m3': 0.0,
            'tiempo_vida_util': 1.0,
            'gestion_empaques': []
        }
    
    # Sección 1: Consumos Durante Uso
    st.subheader("🔌 Consumos Durante Uso")
    
    tiene_consumos = st.checkbox(
        "¿El producto requiere agua o energía para su uso/consumo?",
        value=st.session_state.uso_fin_vida.get('tiene_consumos', False),
        help="Por ejemplo: productos que requieren refrigeración, cocción, lavado, etc."
    )
    
    if tiene_consumos:
        with st.form("form_consumos_uso"):
            st.markdown("#### 📊 Configuración de Consumos")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                energia = st.number_input(
                    "Consumo energético por uso (kWh)",
                    min_value=0.0,
                    value=st.session_state.uso_fin_vida.get('energia_uso_kwh', 0.0),
                    help="Energía consumida en cada uso del producto",
                    key="energia_uso"
                )
                
            with col2:
                agua = st.number_input(
                    "Consumo de agua por uso (m³)",
                    min_value=0.0,
                    value=st.session_state.uso_fin_vida.get('agua_uso_m3', 0.0),
                    help="Agua consumida en cada uso del producto",
                    key="agua_uso"
                )
                
            with col3:
                tiempo = st.number_input(
                    "Tiempo de vida útil (años)",
                    min_value=0.1,
                    value=st.session_state.uso_fin_vida.get('tiempo_vida_util', 1.0),
                    help="Duración estimada del producto",
                    key="tiempo_vida"
                )
            
            # Calcular emisiones preliminares
            emisiones_energia = calcular_emisiones_energia(energia, 'electricidad', factores)
            emisiones_agua = calcular_emisiones_agua(agua, factores)
            emisiones_totales = emisiones_energia + emisiones_agua
            
            # Mostrar estimación de emisiones
            st.markdown("#### 📈 Estimación de Emisiones")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Emisiones por energía", 
                         f"{formatear_numero(emisiones_energia)} kg CO₂e")
            with col2:
                st.metric("Emisiones por agua", 
                         f"{formatear_numero(emisiones_agua)} kg CO₂e")
            
            submitted = st.form_submit_button("💾 Guardar Consumos", 
                                           use_container_width=True)
            
            if submitted:
                st.session_state.uso_fin_vida.update({
                    'tiene_consumos': True,
                    'energia_uso_kwh': energia,
                    'agua_uso_m3': agua,
                    'tiempo_vida_util': tiempo,
                    'emisiones_uso': emisiones_totales
                })
                st.success("✅ Consumos guardados correctamente")
    else:
        st.session_state.uso_fin_vida['tiene_consumos'] = False
    
    # Sección 2: Gestión de Empaques Post-Consumo
    st.markdown("---")
    st.subheader("♻️ Gestión de Empaques Post-Consumo")
    
    opciones_gestion = ['Vertedero', 'Incineracion', 'Compostaje', 'Reciclaje']
    opciones_transporte = list(obtener_opciones_categoria('transporte'))
    
    with st.form("gestion_empaques_form"):
        st.markdown("#### 📦 Configuración de Fin de Vida")
        gestion_empaques = []
        emisiones_totales_fin_vida = 0
        
        for i, empaque in enumerate(st.session_state.empaques):
            if not empaque.get('nombre'):
                continue
            
            with st.expander(f"**{empaque['nombre']}** ({empaque.get('material', 'Material no especificado')})", expanded=True):
                # Buscar si ya existe gestión para este empaque
                gestion_existente = next((g for g in st.session_state.uso_fin_vida.get('gestion_empaques', [])
                                        if g.get('id_empaque') == i), None)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CORRECCIÓN: Manejar índice de gestión existente
                    gestion_actual = gestion_existente.get('tipo_gestion', 'Vertedero') if gestion_existente else 'Vertedero'
                    indice_gestion = opciones_gestion.index(gestion_actual) if gestion_actual in opciones_gestion else 0
                    
                    gestion = st.selectbox(
                        f"**Gestión para {empaque['nombre']}**",
                        options=opciones_gestion,
                        index=indice_gestion,
                        key=f"gestion_fin_vida_{i}"
                    )
                
                with col2:
                    # Transporte de residuos
                    distancia = st.number_input(
                        f"**Distancia transporte (km)**",
                        min_value=0.0,
                        value=gestion_existente.get('distancia_km', 0.0) if gestion_existente else 0.0,
                        step=1.0,
                        format="%.1f",
                        key=f"distancia_fin_vida_{i}"
                    )
                    
                    # CORRECCIÓN: Manejar índice de transporte existente
                    transporte_actual = gestion_existente.get('tipo_transporte', 'Camión diesel') if gestion_existente else 'Camión diesel'
                    indice_transporte = opciones_transporte.index(transporte_actual) if transporte_actual in opciones_transporte else 0
                    
                    transporte = st.selectbox(
                        f"**Transporte**",
                        options=opciones_transporte,
                        index=indice_transporte,
                        key=f"transporte_fin_vida_{i}"
                    )
                
                # Preparar datos para cálculo de emisiones
                porcentajes = {
                    'porcentaje_vertedero': 100 if gestion == 'Vertedero' else 0,
                    'porcentaje_incineracion': 100 if gestion == 'Incineracion' else 0,
                    'porcentaje_compostaje': 100 if gestion == 'Compostaje' else 0,
                    'porcentaje_reciclaje': 100 if gestion == 'Reciclaje' else 0
                }
                
                # Calcular emisiones
                peso = empaque.get('peso_kg', 0)
                emisiones = calcular_emisiones_residuos(peso, factores, porcentajes)
                emisiones_totales_fin_vida += emisiones
                
                # Mostrar emisiones estimadas
                st.info(f"Emisiones estimadas: {formatear_numero(emisiones)} kg CO₂e")
                
                # Guardar datos de gestión
                gestion_empaques.append({
                    'id_empaque': i,
                    'nombre_empaque': empaque['nombre'],
                    'material': empaque.get('material', ''),
                    'peso_kg': peso,
                    'tipo_gestion': gestion,
                    'distancia_km': distancia,
                    'tipo_transporte': transporte,
                    'emisiones': emisiones
                })
        
        # Botón de guardar y resumen
        st.markdown("---")
        st.subheader("📊 Resumen de Gestión")
        
        # Mostrar métricas de resumen
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Empaques gestionados", len(gestion_empaques))
        with col2:
            total_residuos_kg = sum(g['peso_kg'] for g in gestion_empaques)
            st.metric("Peso total", f"{formatear_numero(total_residuos_kg)} kg")
        with col3:
            st.metric("Emisiones totales", f"{formatear_numero(emisiones_totales_fin_vida)} kg CO₂e")
        
        # Botón de guardar
        if st.form_submit_button("💾 Guardar Configuración de Fin de Vida", type="primary", use_container_width=True):
            st.session_state.uso_fin_vida['gestion_empaques'] = gestion_empaques
            st.session_state.uso_fin_vida['emisiones_fin_vida'] = emisiones_totales_fin_vida
            st.success("✅ Configuración de fin de vida guardada correctamente")
    
    # Mostrar resumen si hay datos
    if st.session_state.uso_fin_vida.get('emisiones'):
        st.markdown("---")
        st.subheader("📊 Resumen de Emisiones")
        
        emisiones = st.session_state.uso_fin_vida['emisiones']
        desglose = emisiones['desglose']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Emisiones Totales",
                f"{formatear_numero(emisiones['total'])} kg CO₂e"
            )
            
            if desglose['uso']['energia'] > 0 or desglose['uso']['agua'] > 0:
                st.markdown("##### Emisiones durante uso:")
                if desglose['uso']['energia'] > 0:
                    st.markdown(f"- Energía: {formatear_numero(desglose['uso']['energia'])} kg CO₂e")
                if desglose['uso']['agua'] > 0:
                    st.markdown(f"- Agua: {formatear_numero(desglose['uso']['agua'])} kg CO₂e")
        
        with col2:
            if desglose['fin_vida']:
                st.markdown("##### Emisiones por fin de vida:")
                for empaque, datos in desglose['fin_vida'].items():
                    st.markdown(f"**{empaque}**")
                    st.markdown(f"- Peso: {formatear_numero(datos['peso_kg'])} kg")
                    st.markdown(f"- Emisiones: {formatear_numero(datos['emisiones'])} kg CO₂e")
                    with st.expander("Ver distribución"):
                        for tipo, porcentaje in datos['porcentajes'].items():
                            st.markdown(f"- {tipo.replace('porcentaje_', '').title()}: {porcentaje}%")
        st.markdown("---")
        st.subheader("📈 Resumen")
        
        # Resumen de consumos
        if st.session_state.uso_fin_vida['tiene_consumos']:
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.metric(
                    "Consumo energético total",
                    f"{formatear_numero(st.session_state.uso_fin_vida['consumo_energia_kwh'] * st.session_state.uso_fin_vida['tiempo_vida_util'])} kWh"
                )
            with col_c2:
                st.metric(
                    "Consumo agua total",
                    f"{formatear_numero(st.session_state.uso_fin_vida['consumo_agua_m3'] * st.session_state.uso_fin_vida['tiempo_vida_util'])} m³"
                )
            with col_c3:
                st.metric(
                    "Tiempo de vida",
                    f"{formatear_numero(st.session_state.uso_fin_vida['tiempo_vida_util'])} años"
                )
        
        # Resumen de gestión de empaques
        st.write("**Gestión de Empaques:**")
        for gestion in st.session_state.uso_fin_vida['gestion_empaques']:
            st.info(
                f"**{gestion['empaque']}**: {gestion['tipo_gestion']} a {formatear_numero(gestion['distancia_km'])} km "
                f"por {gestion['tipo_transporte']}"
            )
    
elif pagina == "10. Resultados":
    st.title("10. Resultados de Huella de Carbono")
    
    # Verificar que existe un producto
    if not st.session_state.producto.get('nombre'):
        st.warning("⚠️ Primero define un producto en la página 1")
        st.stop()
    
    # Importar las funciones de cálculo
    from utils.calculos import (
        calcular_emisiones_totales_completas, 
        calcular_emisiones_detalladas_completas,
        obtener_detalle_materias_primas_mejorado,
        obtener_detalle_transporte_mejorado
    )
    
    # BOTÓN PARA CALCULAR - IMPLEMENTACIÓN CORRECTA
    st.subheader("🧮 Ejecutar Cálculos Completos")
    
    col_calc1, col_calc2 = st.columns([2, 1])
    with col_calc1:
        if st.button("🔄 Calcular Huella de Carbono Completa", type="primary", use_container_width=True):
            try:
                with st.spinner("Calculando huella de carbono para todas las etapas..."):
                    # Validar datos mínimos
                    if not st.session_state.materias_primas or not any(mp.get('producto') for mp in st.session_state.materias_primas):
                        st.error("❌ Debe ingresar al menos una materia prima en la página 2")
                    else:
                        # Ejecutar cálculos DETALLADOS usando la nueva función
                        emisiones_totales, desglose_detallado = calcular_emisiones_detalladas_completas(st.session_state, factores)
                        
                        # Guardar resultados en session_state
                        st.session_state.resultados_calculados = {
                            'emisiones_totales': emisiones_totales,
                            'desglose_detallado': desglose_detallado,
                            'fecha_calculo': pd.Timestamp.now(),
                            'producto_nombre': st.session_state.producto['nombre'],
                            'peso_producto_kg': st.session_state.producto.get('peso_neto_kg', 0)
                        }
                        
                        st.success(f"✅ Cálculos completados: {formatear_numero(emisiones_totales, 4)} kg CO₂e")
                        
            except Exception as e:
                st.error(f"❌ Error en los cálculos: {str(e)}")
                st.info("💡 Verifica que todos los datos estén completos en las páginas anteriores")
    
    with col_calc2:
        if st.button("🗑️ Limpiar Resultados", type="secondary", use_container_width=True):
            if 'resultados_calculados' in st.session_state:
                del st.session_state.resultados_calculados
            st.rerun()
    
    # Mostrar resultados si existen
    if 'resultados_calculados' in st.session_state:
        resultados = st.session_state.resultados_calculados
        emisiones_totales = resultados['emisiones_totales']
        desglose_detallado = resultados['desglose_detallado']
        peso_producto_kg = resultados['peso_producto_kg']
        
        # 0. SUPUESTOS Y METODOLOGÍA
        st.header("📋 Supuestos y Metodología")
        
        with st.expander("🔍 **Ver supuestos de cálculo**", expanded=True):
            st.markdown("""
            ### 📊 **Metodología de Cálculo**
            
            **Alcance del Estudio:** Cradle-to-Gate (de la cuna a la puerta) + Uso y Fin de Vida
            
            **Etapas Incluidas:**
            - **📦 Materias Primas:** Producción de ingredientes + empaques de materias primas
            - **📦 Empaques:** Producción de empaques del producto final  
            - **🚚 Transporte:** Transporte de materias primas y empaques hasta fábrica
            - **⚡ Procesamiento:** Energía, agua y gestión de mermas en producción
            - **🚛 Distribución:** Transporte del producto terminado a puntos de venta
            - **🏪 Retail:** Almacenamiento en puntos de venta
            - **♻️ Fin de Vida:** Consumos durante uso + gestión de empaques post-consumo
            
            **Supuestos Clave:**
            - Factores de emisión basados en base de datos internacionales
            - Transporte terrestre considerado como modo principal
            - Gestión de residuos según tipo especificado (vertedero, reciclaje, etc.)
            - Consumos energéticos basados en datos ingresados por el usuario
            - Peso en distribución incluye producto + empaques del producto final
            """)
        
        # 1. RESUMEN EJECUTIVO
        st.header("📊 Resumen Ejecutivo")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Huella Total", f"{formatear_numero(emisiones_totales, 4)} kg CO₂e")
        with col2:
            emisiones_g = emisiones_totales * 1000
            st.metric("Huella Total", f"{formatear_numero(emisiones_g, 4)} g CO₂e")
        with col3:
            # Calcular por kg de producto
            if peso_producto_kg > 0:
                emisiones_por_kg = emisiones_totales / peso_producto_kg
                st.metric("Por kg de producto", f"{formatear_numero(emisiones_por_kg, 4)} kg CO₂e/kg")
            else:
                st.metric("Por kg de producto", "N/A")
        with col4:
            if peso_producto_kg > 0:
                emisiones_por_kg_g = (emisiones_totales / peso_producto_kg) * 1000
                st.metric("Por kg de producto", f"{formatear_numero(emisiones_por_kg_g, 4)} g CO₂e/kg")
        
        # 2. DISTRIBUCIÓN POR ETAPA (GRÁFICOS)
        st.subheader("📈 Distribución de Huella de Carbono por Etapa")
        
        # Preparar datos para gráficos
        etapas_totales = {
            'Materias Primas': desglose_detallado['materias_primas']['total'],
            'Empaques': desglose_detallado['empaques']['total'],
            'Transporte': desglose_detallado['transporte']['total'],
            'Procesamiento': desglose_detallado['procesamiento']['total'],
            'Distribución': desglose_detallado['distribucion']['total'],
            'Retail': desglose_detallado['retail']['total'],
            'Fin de Vida': desglose_detallado['fin_vida']['total']
        }
        
        # Filtrar etapas con emisiones significativas
        etapas_significativas = {k: v for k, v in etapas_totales.items() if v > 0.001}
        
        if etapas_significativas:
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de barras
                fig_barras = px.bar(
                    x=list(etapas_significativas.keys()),
                    y=list(etapas_significativas.values()),
                    title="Huella de Carbono por Etapa (kg CO₂e)",
                    labels={'x': 'Etapa del Ciclo de Vida', 'y': 'kg CO₂e'},
                    color=list(etapas_significativas.values()),
                    color_continuous_scale='Viridis'
                )
                fig_barras.update_traces(
                    text=[f"{formatear_numero(v, 4)} kg" for v in etapas_significativas.values()],
                    textposition='auto'
                )
                fig_barras.update_layout(showlegend=False)
                st.plotly_chart(fig_barras, use_container_width=True)
            
            with col2:
                # Gráfico de torta
                fig_torta = px.pie(
                    names=list(etapas_significativas.keys()),
                    values=list(etapas_significativas.values()),
                    title="Distribución Porcentual por Etapa",
                    hole=0.3
                )
                fig_torta.update_traces(
                    textinfo='percent+label',
                    textposition='inside'
                )
                st.plotly_chart(fig_torta, use_container_width=True)
            
            # 3. DESGLOSE DETALLADO POR ETAPA
            st.header("🔍 Desglose Detallado por Etapa del Ciclo de Vida")
            
            # MATERIAS PRIMAS
            with st.expander("📦 **1. Materias Primas**", expanded=True):
                etapa_mp = desglose_detallado['materias_primas']
                porcentaje_mp = (etapa_mp['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Materias Primas", 
                         f"{formatear_numero(etapa_mp['total'], 4)} kg CO₂e ({porcentaje_mp:.1f}%)")
                
                if etapa_mp['fuentes']:
                    st.subheader("Desglose por Material")
                    datos_mp = []
                    for material, datos in etapa_mp['fuentes'].items():
                        datos_mp.append({
                            'Material': material,
                            'Cantidad (kg)': formatear_numero(datos.get('cantidad_kg', 0), 4),
                            'Huella Material (kg CO₂e)': formatear_numero(datos.get('emisiones_material', 0), 4),
                            'Huella Empaque MP (kg CO₂e)': formatear_numero(datos.get('emisiones_empaque', 0), 4),
                            'Total (kg CO₂e)': formatear_numero(datos.get('total', 0), 4)
                        })
                    df_mp = pd.DataFrame(datos_mp)
                    st.dataframe(df_mp, use_container_width=True)
                else:
                    st.info("No hay datos detallados de materias primas")
            
            # EMPAQUES
            with st.expander("📦 **2. Empaques del Producto**", expanded=True):
                etapa_emp = desglose_detallado['empaques']
                porcentaje_emp = (etapa_emp['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Empaques", 
                         f"{formatear_numero(etapa_emp['total'], 4)} kg CO₂e ({porcentaje_emp:.1f}%)")
                
                if etapa_emp['fuentes']:
                    st.subheader("Desglose por Empaque")
                    datos_emp = []
                    for empaque, datos in etapa_emp['fuentes'].items():
                        datos_emp.append({
                            'Empaque': empaque,
                            'Material': datos.get('material', 'No especificado'),
                            'Peso (kg)': formatear_numero(datos.get('peso_kg', 0), 4),
                            'Huella Carbono (kg CO₂e)': formatear_numero(datos.get('emisiones', 0), 4)
                        })
                    df_emp = pd.DataFrame(datos_emp)
                    st.dataframe(df_emp, use_container_width=True)
                else:
                    st.info("No hay datos detallados de empaques")
            
            # TRANSPORTE
            with st.expander("🚚 **3. Transporte (MP + Empaques)**", expanded=True):
                etapa_trans = desglose_detallado['transporte']
                porcentaje_trans = (etapa_trans['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Transporte", 
                         f"{formatear_numero(etapa_trans['total'], 4)} kg CO₂e ({porcentaje_trans:.1f}%)")
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.subheader("📦 Transporte Materias Primas")
                    trans_mp = etapa_trans['fuentes']['materias_primas']
                    st.metric("Huella MP", f"{formatear_numero(trans_mp['emisiones'], 4)} kg CO₂e")
                    
                    if trans_mp['detalle']:
                        datos_trans_mp = []
                        for item in trans_mp['detalle']:
                            if 'producto' in item:
                                for ruta in item.get('rutas', []):
                                    datos_trans_mp.append({
                                        'Material': item['producto'],
                                        'Ruta': f"{ruta.get('origen', '')} → {ruta.get('destino', '')}",
                                        'Distancia (km)': formatear_numero(ruta.get('distancia_km', 0), 1),
                                        'Transporte': ruta.get('tipo_transporte', 'No especificado'),
                                        'Huella (kg CO₂e)': formatear_numero(ruta.get('emisiones', 0), 4)
                                    })
                        if datos_trans_mp:
                            df_trans_mp = pd.DataFrame(datos_trans_mp)
                            st.dataframe(df_trans_mp, use_container_width=True)
                        else:
                            st.info("No hay rutas detalladas de transporte MP")
                
                with col_t2:
                    st.subheader("📦 Transporte Empaques")
                    trans_emp = etapa_trans['fuentes']['empaques']
                    st.metric("Huella Empaques", f"{formatear_numero(trans_emp['emisiones'], 4)} kg CO₂e")
                    
                    if trans_emp['detalle']:
                        datos_trans_emp = []
                        for item in trans_emp['detalle']:
                            if 'nombre' in item:
                                for ruta in item.get('rutas', []):
                                    datos_trans_emp.append({
                                        'Empaque': item['nombre'],
                                        'Ruta': f"{ruta.get('origen', '')} → {ruta.get('destino', '')}",
                                        'Distancia (km)': formatear_numero(ruta.get('distancia_km', 0), 1),
                                        'Transporte': ruta.get('tipo_transporte', 'No especificado'),
                                        'Huella (kg CO₂e)': formatear_numero(ruta.get('emisiones', 0), 4)
                                    })
                        if datos_trans_emp:
                            df_trans_emp = pd.DataFrame(datos_trans_emp)
                            st.dataframe(df_trans_emp, use_container_width=True)
                        else:
                            st.info("No hay rutas detalladas de transporte empaques")
            
            # PROCESAMIENTO
            with st.expander("⚡ **4. Procesamiento (Producción)**", expanded=True):
                etapa_proc = desglose_detallado['procesamiento']
                porcentaje_proc = (etapa_proc['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Procesamiento", 
                         f"{formatear_numero(etapa_proc['total'], 4)} kg CO₂e ({porcentaje_proc:.1f}%)")
                
                if etapa_proc['fuentes']:
                    datos_proc = []
                    # Procesar fuentes de energía
                    if 'Energía Producción' in etapa_proc['fuentes']:
                        datos_proc.append({
                            'Fuente': 'Energía Eléctrica',
                            'Tipo': 'Electricidad de red',
                            'Consumo': f"{formatear_numero(st.session_state.produccion.get('energia_kwh', 0), 4)} kWh",
                            'Huella Carbono (kg CO₂e)': formatear_numero(etapa_proc['fuentes']['Energía Producción'], 4)
                        })
                    
                    # Procesar fuentes de agua
                    if 'Agua Producción' in etapa_proc['fuentes']:
                        datos_proc.append({
                            'Fuente': 'Agua',
                            'Tipo': 'Agua potable',
                            'Consumo': f"{formatear_numero(st.session_state.produccion.get('agua_m3', 0), 4)} m³",
                            'Huella Carbono (kg CO₂e)': formatear_numero(etapa_proc['fuentes']['Agua Producción'], 4)
                        })
                    
                    # Procesar gestión de mermas
                    emisiones_mermas_total = sum(
                        v for k, v in etapa_proc['fuentes'].items() 
                        if k.startswith('Merma') and isinstance(v, (int, float))
                    )
                    if emisiones_mermas_total > 0:
                        datos_proc.append({
                            'Fuente': 'Gestión de Mermas',
                            'Tipo': 'Residuos de producción',
                            'Consumo': '-',
                            'Huella Carbono (kg CO₂e)': formatear_numero(emisiones_mermas_total, 4)
                        })
                    
                    if datos_proc:
                        df_proc = pd.DataFrame(datos_proc)
                        st.dataframe(df_proc, use_container_width=True)
                    else:
                        st.info("No hay datos detallados de procesamiento")
                else:
                    st.info("No hay datos de procesamiento")
            
            # DISTRIBUCIÓN
            with st.expander("🚛 **5. Distribución**", expanded=True):
                etapa_dist = desglose_detallado['distribucion']
                porcentaje_dist = (etapa_dist['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Distribución", 
                         f"{formatear_numero(etapa_dist['total'], 4)} kg CO₂e ({porcentaje_dist:.1f}%)")
                
                if etapa_dist['fuentes']:
                    datos_dist = []
                    for canal, datos in etapa_dist['fuentes'].items():
                        if canal.startswith('Distribución '):
                            nombre_canal = canal.replace('Distribución ', '')
                            datos_dist.append({
                                'Canal': nombre_canal,
                                'Porcentaje': f"{st.session_state.distribucion['canales'][0].get('porcentaje', 0):.1f}%",
                                'Huella Carbono (kg CO₂e)': formatear_numero(datos, 4)
                            })
                    
                    if datos_dist:
                        df_dist = pd.DataFrame(datos_dist)
                        st.dataframe(df_dist, use_container_width=True)
                    else:
                        st.info("No hay datos detallados de distribución")
                else:
                    st.info("No hay datos de distribución")
            
            # RETAIL
            with st.expander("🏪 **6. Retail**", expanded=True):
                etapa_retail = desglose_detallado['retail']
                porcentaje_retail = (etapa_retail['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Retail", 
                         f"{formatear_numero(etapa_retail['total'], 4)} kg CO₂e ({porcentaje_retail:.1f}%)")
                
                if etapa_retail['fuentes']:
                    for fuente, datos in etapa_retail['fuentes'].items():
                        if fuente == 'Energía Retail':
                            st.write(f"**Energía para almacenamiento:**")
                            st.write(f"- Consumo: {formatear_numero(st.session_state.retail.get('consumo_energia_kwh', 0), 4)} kWh")
                            st.write(f"- Días almacenamiento: {st.session_state.retail.get('dias_almacenamiento', 0)} días")
                            st.write(f"- Tipo almacenamiento: {st.session_state.retail.get('tipo_almacenamiento', 'No especificado')}")
                            st.write(f"- Huella carbono: {formatear_numero(datos, 4)} kg CO₂e")
                else:
                    st.info("No hay datos de retail")
            
            # FIN DE VIDA
            with st.expander("♻️ **7. Uso y Fin de Vida**", expanded=True):
                etapa_fv = desglose_detallado['fin_vida']
                porcentaje_fv = (etapa_fv['total'] / emisiones_totales * 100) if emisiones_totales > 0 else 0
                st.metric("Huella Total Uso y Fin de Vida", 
                         f"{formatear_numero(etapa_fv['total'], 4)} kg CO₂e ({porcentaje_fv:.1f}%)")
                
                if etapa_fv['fuentes']:
                    datos_fv = []
                    
                    # Consumo durante uso
                    if 'uso' in etapa_fv['fuentes']:
                        uso_data = etapa_fv['fuentes']['uso']
                        if uso_data.get('energia', 0) > 0:
                            datos_fv.append({
                                'Fuente': 'Consumo Energético durante Uso',
                                'Detalle': f"{formatear_numero(st.session_state.uso_fin_vida.get('energia_uso_kwh', 0), 4)} kWh",
                                'Huella Carbono (kg CO₂e)': formatear_numero(uso_data['energia'], 4)
                            })
                        if uso_data.get('agua', 0) > 0:
                            datos_fv.append({
                                'Fuente': 'Consumo de Agua durante Uso',
                                'Detalle': f"{formatear_numero(st.session_state.uso_fin_vida.get('agua_uso_m3', 0), 4)} m³",
                                'Huella Carbono (kg CO₂e)': formatear_numero(uso_data['agua'], 4)
                            })
                    
                    # Gestión de empaques post-consumo
                    if 'fin_vida' in etapa_fv['fuentes']:
                        for empaque, datos in etapa_fv['fuentes']['fin_vida'].items():
                            datos_fv.append({
                                'Fuente': f'Gestión de {empaque}',
                                'Detalle': 'Empaques al fin de vida',
                                'Huella Carbono (kg CO₂e)': formatear_numero(datos.get('emisiones', 0), 4)
                            })
                    
                    if datos_fv:
                        df_fv = pd.DataFrame(datos_fv)
                        st.dataframe(df_fv, use_container_width=True)
                    else:
                        st.info("No hay datos detallados de uso y fin de vida")
                else:
                    st.info("No hay datos de uso y fin de vida")
            
            # 4. TABLA RESUMEN COMPARATIVA
            st.header("📋 Resumen Comparativo por Etapa")
            
            datos_resumen = []
            for etapa_nombre, etapa_key in [
                ('Materias Primas', 'materias_primas'),
                ('Empaques', 'empaques'),
                ('Transporte', 'transporte'),
                ('Procesamiento', 'procesamiento'),
                ('Distribución', 'distribucion'),
                ('Retail', 'retail'),
                ('Fin de Vida', 'fin_vida')
            ]:
                etapa = desglose_detallado[etapa_key]
                if etapa['total'] > 0.001:
                    porcentaje = (etapa['total'] / emisiones_totales) * 100
                    datos_resumen.append({
                        'Etapa': etapa_nombre,
                        'Huella Carbono (kg CO₂e)': formatear_numero(etapa['total'], 4),
                        'Huella Carbono (g CO₂e)': formatear_numero(etapa['total'] * 1000, 4),
                        'Porcentaje (%)': f"{porcentaje:.1f}%"
                    })
            
            if datos_resumen:
                df_resumen = pd.DataFrame(datos_resumen)
                df_resumen = df_resumen.sort_values('Huella Carbono (kg CO₂e)', ascending=False)
                st.dataframe(df_resumen, use_container_width=True)
            else:
                st.info("No hay emisiones significativas para mostrar")
            
            # 5. RECOMENDACIONES
            st.header("💡 Recomendaciones para Reducción")
            
            # Identificar las 3 etapas con mayor impacto
            etapas_ordenadas = []
            for etapa_key, etapa_data in desglose_detallado.items():
                if etapa_data['total'] > 0.001:
                    etapas_ordenadas.append((etapa_key, etapa_data['total']))
            
            etapas_ordenadas.sort(key=lambda x: x[1], reverse=True)
            top_3 = etapas_ordenadas[:3]
            
            nombres_etapas = {
                'materias_primas': 'Materias Primas',
                'empaques': 'Empaques',
                'transporte': 'Transporte',
                'procesamiento': 'Procesamiento',
                'distribucion': 'Distribución',
                'retail': 'Retail',
                'fin_vida': 'Fin de Vida'
            }
            
            for i, (etapa_key, emisiones) in enumerate(top_3, 1):
                etapa_nombre = nombres_etapas.get(etapa_key, etapa_key)
                porcentaje = (emisiones / emisiones_totales) * 100
                
                with st.expander(f"**#{i} - {etapa_nombre}** - {formatear_numero(emisiones, 4)} kg CO₂e ({porcentaje:.1f}%)", expanded=True):
                    if etapa_key == 'materias_primas':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 🏭 **Evaluar proveedores locales** para reducir distancias de transporte
                        - 📊 **Optimizar cantidades** utilizadas para reducir mermas
                        - 🔄 **Considerar materiales alternativos** con menor huella de carbono
                        - 🌱 **Priorizar ingredientes de temporada** y locales
                        - 🔍 **Analizar empaques de materias primas** para reducción
                        """)
                    elif etapa_key == 'empaques':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 📉 **Reducir peso** y volumen de empaques
                        - ♻️ **Usar materiales reciclados** y reciclables
                        - 🎯 **Diseñar para reciclabilidad** y reutilización
                        - 🌿 **Considerar materiales biodegradables** o compostables
                        - 📦 **Optimizar diseño** para eficiencia en transporte
                        """)
                    elif etapa_key == 'transporte':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 🗺️ **Optimizar rutas** de distribución y recolección
                        - 🚛 **Consolidar envíos** para mejorar eficiencia de carga
                        - ⚡ **Evaluar modos de transporte** más eficientes (eléctricos, ferroviario)
                        - 📦 **Reducir peso** de empaques para disminuir carga transportada
                        - 🏭 **Priorizar proveedores locales** cuando sea posible
                        """)
                    elif etapa_key == 'procesamiento':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 💡 **Implementar eficiencia energética** en procesos
                        - ☀️ **Considerar energías renovables** en planta
                        - ⏰ **Optimizar horarios** de producción para eficiencia
                        - 🔧 **Mantenimiento preventivo** de equipos
                        - 💧 **Reducir consumo de agua** y optimizar tratamiento
                        - 📊 **Minimizar mermas** mediante mejor control de procesos
                        """)
                    elif etapa_key == 'distribucion':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 🚚 **Optimizar logística** de última milla
                        - 📍 **Consolidar centros** de distribución
                        - 🌡️ **Mejorar eficiencia** en almacenamiento
                        - 🔄 **Implementar sistemas** de retorno de empaques
                        - 🗺️ **Planificar rutas** más eficientes
                        """)
                    elif etapa_key == 'retail':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - 💡 **Mejorar eficiencia energética** en refrigeración/iluminación
                        - ⏱️ **Optimizar tiempos** de almacenamiento
                        - 🌡️ **Mantener temperaturas** óptimas para reducción energética
                        - 📊 **Monitorear consumos** energéticos regularmente
                        """)
                    elif etapa_key == 'fin_vida':
                        st.markdown("""
                        **Acciones recomendadas:**
                        - ♻️ **Promover reciclaje** de empaques post-consumo
                        - 🌿 **Fomentar compostaje** cuando sea aplicable
                        - 💡 **Optimizar consumos** durante uso del producto
                        - 📚 **Educar al consumidor** sobre disposición adecuada
                        - 🔄 **Diseñar para circularidad** y reutilización
                        """)
            
            # 6. EXPORTACIÓN
            st.markdown("---")
            st.subheader("📤 Exportar Resultados")
            
            if st.button("💾 Exportar Resultados Detallados a Excel", type="secondary"):
                try:
                    # Crear DataFrame para exportación
                    datos_export = []
                    for etapa_nombre, etapa_key in [
                        ('Materias Primas', 'materias_primas'),
                        ('Empaques', 'empaques'),
                        ('Transporte', 'transporte'),
                        ('Procesamiento', 'procesamiento'),
                        ('Distribución', 'distribucion'),
                        ('Retail', 'retail'),
                        ('Fin de Vida', 'fin_vida')
                    ]:
                        etapa = desglose_detallado[etapa_key]
                        if etapa['total'] > 0.001:
                            datos_export.append({
                                'Etapa': etapa_nombre,
                                'Huella Carbono (kg CO₂e)': etapa['total'],
                                'Huella Carbono (g CO₂e)': etapa['total'] * 1000,
                                'Porcentaje (%)': (etapa['total'] / emisiones_totales) * 100
                            })
                    
                    df_export = pd.DataFrame(datos_export)
                    
                    # Exportar a Excel
                    import openpyxl
                    from datetime import datetime
                    
                    archivo = f"huella_carbono_detallada_{st.session_state.producto['nombre']}.xlsx"
                    
                    with pd.ExcelWriter(archivo, engine='openpyxl') as writer:
                        df_export.to_excel(writer, sheet_name='Resumen por Etapa', index=False)
                        
                        # Hoja de supuestos
                        supuestos_data = {
                            'Parámetro': [
                                'Producto', 'Unidad Funcional', 'Peso Neto (kg)', 'Fecha Cálculo',
                                'Alcance del Estudio', 'Metodología'
                            ],
                            'Valor': [
                                st.session_state.producto['nombre'],
                                st.session_state.producto['unidad_funcional'],
                                formatear_numero(peso_producto_kg, 4),
                                datetime.now().strftime("%Y-%m-%d %H:%M"),
                                'Cradle-to-Gate + Uso y Fin de Vida',
                                'Análisis de Ciclo de Vida (ACV) simplificado'
                            ]
                        }
                        df_supuestos = pd.DataFrame(supuestos_data)
                        df_supuestos.to_excel(writer, sheet_name='Supuestos', index=False)
                    
                    with open(archivo, "rb") as file:
                        st.download_button(
                            label="📥 Descargar Archivo Excel",
                            data=file,
                            file_name=archivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("✅ Archivo listo para descargar")
                    
                except Exception as e:
                    st.error(f"Error al exportar: {str(e)}")
        
        else:
            st.info("ℹ️ No hay emisiones significativas para mostrar. Verifica que hayas ingresado datos en las páginas anteriores.")
    
    else:
        st.info("ℹ️ **Presiona el botón 'Calcular Huella de Carbono Completa' para ejecutar los cálculos y ver los resultados**")
        st.markdown("""
        ### 📋 ¿Qué se calculará?
        
        El sistema analizará todas las etapas del ciclo de vida con desglose detallado:
        
        - **📦 Materias Primas:** Producción de ingredientes + empaques de MP
        - **📦 Empaques:** Producción de empaques del producto final  
        - **🚚 Transporte:** Transporte de MP y empaques hasta fábrica
        - **⚡ Procesamiento:** Energía, agua y gestión de mermas en producción
        - **🚛 Distribución:** Transporte del producto a puntos de venta
        - **🏪 Retail:** Almacenamiento en puntos de venta
        - **♻️ Uso y Fin de Vida:** Consumos durante uso + gestión de empaques
        
        ### ⚠️ Requisitos previos
        - Producto definido (Página 1)
        - Al menos una materia prima (Página 2)
        - Datos opcionales en otras páginas para cálculo completo
        """)

# Información sobre factores
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ Factores de Emisión")
st.sidebar.info(f"Usando {len(factores)} factores")

if st.sidebar.button("👁️ **Ver factores**"):
    st.sidebar.dataframe(factores[['category', 'item', 'factor_kgCO2e_per_unit', 'source']])

# Botón para reiniciar todo
st.sidebar.markdown("---")
if st.sidebar.button("🔄 **Reiniciar Todo**", type="secondary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Información de desarrollo
st.sidebar.markdown("---")
st.sidebar.info("**FASE 1** ✅ Completada\n- Sistema de unidades\n- Transporte individual\n- Balance real")