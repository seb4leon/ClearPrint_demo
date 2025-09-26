"""
Calculadora de Huella de Carbono - FASE 1 COMPLETA
Sistema con unidades, transporte individual y balance de masa real
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.calculos import (
    calcular_emisiones_materias_primas,
    calcular_emisiones_empaques,
    calcular_emisiones_transporte_materias_primas,
    calcular_emisiones_transporte_empaques,
    calcular_emisiones_energia,
    calcular_emisiones_agua,
    calcular_emisiones_residuos,
    exportar_resultados_excel
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
        'transportes_materias_primas': [],  # Nuevo: transporte individual
        'transportes_empaques': [],        # Nuevo: transporte individual
        'produccion': {
            'energia_kwh': 0.0,
            'tipo_energia': 'Red eléctrica promedio',
            'agua_m3': 0.0,
            'residuos_produccion': []  # Nuevo: residuos por elemento
        },
        'distribucion': {
            'canales': []  # Nuevo: para fase 2
        },
        'retail': {
            # Placeholder para fase 2
        },
        'uso_fin_vida': {
            'energia_uso_kwh': 0.0,
            'duracion_uso_anios': 1,
            'agua_uso_m3': 0.0,
            'gestion_fin_vida': []  # Nuevo: gestión por elemento
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

# Cargar factores de emisión
@st.cache_data
def cargar_factores():
    try:
        factores = pd.read_csv('data/factors.csv')
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

factores = cargar_factores()

# Función para obtener opciones de cada categoría
def obtener_opciones_categoria(categoria):
    return factores[factores['category'] == categoria]['item'].unique()

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
                    step=0.1,
                    format="%.3f",
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
                    step=0.1,
                    format="%.3f",
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
                            value=st.session_state.materias_primas[i].get('cantidad_teorica', 0.0),
                            key=f"cantidad_teorica_{i}",
                            step=0.1,
                            format="%.3f"
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
                            value=st.session_state.materias_primas[i].get('cantidad_real', 0.0),
                            key=f"cantidad_real_{i}",
                            step=0.1,
                            format="%.3f"
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
                
                # Empaque de la materia prima (opcional)
                with st.expander("📦 **Empaque de esta materia prima (opcional)**"):
                    tiene_empaque = st.checkbox(
                        "¿Esta materia prima viene empaquetada?",
                        value=bool(st.session_state.materias_primas[i].get('empaque')),
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
                            peso_empaque = st.number_input(
                                f"**Peso del empaque**",
                                min_value=0.0,
                                value=st.session_state.materias_primas[i].get('empaque', {}).get('peso', 0.0),
                                key=f"peso_empaque_{i}",
                                step=0.01,
                                format="%.3f"
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

# Página 7: Distribución (SIMPLIFICADA - Actualización automática)
elif pagina == "7. Distribución":
    st.title("7. Distribución del Producto")
    st.info("🚚 Define los canales de distribución y el transporte del producto terminado")
    
    # Verificar datos previos necesarios
    if not st.session_state.producto.get('nombre'):
        st.warning("⚠️ Primero define un producto en la página 1")
        st.stop()
    
    peso_producto_kg = st.session_state.producto.get('peso_neto_kg', 0)
    if peso_producto_kg <= 0:
        st.warning("⚠️ El producto debe tener un peso neto mayor a 0")
        st.stop()
    
    # Inicializar estructura de distribución
    if 'canales' not in st.session_state.distribucion:
        st.session_state.distribucion['canales'] = [{'nombre': '', 'porcentaje': 100.0, 'rutas': [{}]}]
    
    opciones_transporte = list(obtener_opciones_categoria('transporte'))
    
    with st.form("distribucion_form"):
        st.subheader("📦 Configuración de Canales de Distribución")
        
        # Número de canales (actualización automática como en páginas anteriores)
        num_canales = st.number_input(
            "**¿Cuántos canales de distribución diferentes tiene el producto?**",
            min_value=1,
            max_value=10,
            value=len(st.session_state.distribucion['canales']),
            help="Ej: Venta online, Tienda física, Exportación, etc.",
            key="num_canales_input"
        )
        
        # ACTUALIZACIÓN AUTOMÁTICA (sin botón) - igual que en páginas 2, 3, 4, 5
        if len(st.session_state.distribucion['canales']) != num_canales:
            if num_canales > len(st.session_state.distribucion['canales']):
                # Agregar nuevos canales
                nuevos_canales = [{'nombre': f'Canal {i+1}', 'porcentaje': 0.0, 'rutas': [{}]} 
                                for i in range(len(st.session_state.distribucion['canales']), num_canales)]
                st.session_state.distribucion['canales'].extend(nuevos_canales)
                
                # Recalcular porcentajes equitativamente
                if st.session_state.distribucion['canales']:
                    porcentaje_por_canal = 100.0 / len(st.session_state.distribucion['canales'])
                    for canal in st.session_state.distribucion['canales']:
                        canal['porcentaje'] = porcentaje_por_canal
            else:
                # Reducir canales (mantener los primeros)
                st.session_state.distribucion['canales'] = st.session_state.distribucion['canales'][:num_canales]
        
        porcentaje_total = 0.0
        
        # Configurar cada canal
        for i in range(len(st.session_state.distribucion['canales'])):
            canal = st.session_state.distribucion['canales'][i]
            
            with st.expander(f"**Canal de Distribución {i+1}**", expanded=True):
                col_c1, col_c2, col_c3 = st.columns([3, 2, 2])
                
                with col_c1:
                    # Nombre del canal
                    nuevo_nombre = st.text_input(
                        f"Nombre del canal",
                        value=canal.get('nombre', f'Canal {i+1}'),
                        placeholder="Ej: Venta Online, Tienda Física, Exportación...",
                        key=f"nombre_canal_{i}"
                    )
                    canal['nombre'] = nuevo_nombre
                
                with col_c2:
                    # Porcentaje de distribución
                    nuevo_porcentaje = st.number_input(
                        f"Porcentaje de distribución (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(canal.get('porcentaje', 0.0)),
                        step=1.0,
                        format="%.1f",
                        key=f"porcentaje_input_{i}"
                    )
                    canal['porcentaje'] = nuevo_porcentaje
                    porcentaje_total += nuevo_porcentaje
                
                with col_c3:
                    # Calcular y mostrar peso distribuido
                    peso_distribuido_kg = (peso_producto_kg * nuevo_porcentaje) / 100
                    canal['peso_distribuido_kg'] = peso_distribuido_kg
                    st.metric(
                        "Peso distribuido", 
                        f"{formatear_numero(peso_distribuido_kg)} kg"
                    )
                
                # CONFIGURACIÓN DE RUTAS PARA ESTE CANAL
                st.write("**Rutas de transporte para este canal:**")
                
                # Número de rutas (actualización automática)
                if 'rutas' not in canal:
                    canal['rutas'] = [{}]
                
                num_rutas = st.number_input(
                    f"¿Cuántas rutas de transporte tiene este canal?",
                    min_value=1,
                    max_value=5,
                    value=len(canal['rutas']),
                    key=f"num_rutas_{i}"
                )
                
                # ACTUALIZACIÓN AUTOMÁTICA de rutas (sin botón)
                if len(canal['rutas']) != num_rutas:
                    if num_rutas > len(canal['rutas']):
                        # Agregar nuevas rutas
                        nuevas_rutas = [{} for _ in range(num_rutas - len(canal['rutas']))]
                        canal['rutas'].extend(nuevas_rutas)
                    else:
                        # Reducir rutas
                        canal['rutas'] = canal['rutas'][:num_rutas]
                
                # Configurar cada ruta (SIN AUTOCOMPLETADO)
                for j in range(len(canal['rutas'])):
                    ruta = canal['rutas'][j]
                    
                    with st.container():
                        st.write(f"**Ruta {j+1}**")
                        col_r1, col_r2, col_r3, col_r4 = st.columns([2, 2, 1, 1])
                        
                        with col_r1:
                            # ORIGEN SIMPLE - sin autocompletado
                            nuevo_origen = st.text_input(
                                f"Origen",
                                value=ruta.get('origen', ''),
                                placeholder="Ej: Fábrica, Centro distribución, Puerto",
                                key=f"origen_{i}_{j}"
                            )
                            ruta['origen'] = nuevo_origen
                        
                        with col_r2:
                            # DESTINO SIMPLE - sin autocompletado
                            nuevo_destino = st.text_input(
                                f"Destino",
                                value=ruta.get('destino', ''),
                                placeholder="Ej: Cliente, Tienda, Almacén, Puerto destino",
                                key=f"destino_{i}_{j}"
                            )
                            ruta['destino'] = nuevo_destino
                        
                        with col_r3:
                            nueva_distancia = st.number_input(
                                f"Distancia (km)",
                                min_value=0.0,
                                value=float(ruta.get('distancia_km', 0.0)),
                                step=1.0,
                                format="%.1f",
                                key=f"distancia_{i}_{j}"
                            )
                            ruta['distancia_km'] = nueva_distancia
                        
                        with col_r4:
                            transporte_actual = ruta.get('tipo_transporte', 'Camión diesel')
                            indice_transporte = opciones_transporte.index(transporte_actual) if transporte_actual in opciones_transporte else 0
                            
                            nuevo_transporte = st.selectbox(
                                f"Transporte",
                                options=opciones_transporte,
                                index=indice_transporte,
                                key=f"transporte_{i}_{j}"
                            )
                            ruta['tipo_transporte'] = nuevo_transporte
                        
                        # La carga se calcula automáticamente
                        ruta['carga_kg'] = peso_distribuido_kg
        
        # VALIDACIÓN Y CÁLCULOS
        st.subheader("📊 Validación de Distribución")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            st.metric("Porcentaje total", f"{porcentaje_total:.1f}%")
        with col_v2:
            st.metric("Peso producto total", f"{formatear_numero(peso_producto_kg)} kg")
        
        # Validación de porcentajes
        diferencia_porcentaje = abs(porcentaje_total - 100.0)
        with col_v3:
            if diferencia_porcentaje < 0.1:
                st.metric("Validación", "✅ Correcto")
                submit_disabled = False
            else:
                st.metric("Validación", "❌ Incorrecto")
                submit_disabled = True
        
        if diferencia_porcentaje > 0.1:
            st.error(f"⚠️ La suma de porcentajes debe ser 100%. Actual: {porcentaje_total:.1f}%")
            st.info("💡 Ajusta los porcentajes para que sumen exactamente 100%")
        
        # Cálculo de emisiones estimadas (solo si la validación es correcta)
        if not submit_disabled:
            st.subheader("📈 Emisiones Estimadas de Distribución")
            
            emisiones_totales = 0
            for i, canal in enumerate(st.session_state.distribucion['canales']):
                if canal.get('nombre') and canal.get('rutas'):
                    emisiones_canal = 0
                    for ruta in canal['rutas']:
                        if ruta.get('distancia_km', 0) > 0 and ruta.get('tipo_transporte'):
                            factor = next((f for f in factores.to_dict('records') 
                                         if f['category'] == 'transporte' and f['item'] == ruta['tipo_transporte']), None)
                            if factor:
                                carga_ton = ruta.get('carga_kg', 0) / 1000
                                emisiones_ruta = ruta['distancia_km'] * carga_ton * factor['factor_kgCO2e_per_unit']
                                emisiones_canal += emisiones_ruta
                    
                    emisiones_totales += emisiones_canal
                    
                    if emisiones_canal > 0:
                        st.metric(
                            f"Emisiones {canal['nombre']}", 
                            f"{formatear_numero(emisiones_canal)} kg CO₂e"
                        )
            
            if emisiones_totales > 0:
                st.success(f"**Emisiones totales de distribución: {formatear_numero(emisiones_totales)} kg CO₂e**")
        
        # BOTÓN DE GUARDADO
        if st.form_submit_button("💾 **Guardar Configuración**", disabled=submit_disabled, type="primary"):
            st.success("✅ **Configuración de distribución guardada correctamente**")
    
    # RESUMEN FINAL
    st.markdown("---")
    st.subheader("📋 Resumen de Distribución")
    
    if st.session_state.distribucion['canales']:
        datos_resumen = []
        for canal in st.session_state.distribucion['canales']:
            if canal.get('nombre'):
                rutas_validas = [r for r in canal.get('rutas', []) if r.get('origen')]
                distancia_total = sum(r.get('distancia_km', 0) for r in rutas_validas)
                
                datos_resumen.append({
                    'Canal': canal['nombre'],
                    'Porcentaje': f"{canal['porcentaje']:.1f}%",
                    'Peso Distribuido': f"{formatear_numero(canal.get('peso_distribuido_kg', 0))} kg",
                    'Rutas Configuradas': len(rutas_validas),
                    'Distancia Total': f"{formatear_numero(distancia_total)} km"
                })
        
        if datos_resumen:
            df_resumen = pd.DataFrame(datos_resumen)
            st.dataframe(df_resumen, use_container_width=True)
            
            # Estadísticas generales
            total_rutas = sum(len([r for r in c.get('rutas', []) if r.get('origen')]) 
                            for c in st.session_state.distribucion['canales'])
            total_distancia = sum(sum(r.get('distancia_km', 0) for r in c.get('rutas', []) 
                                  if r.get('origen')) for c in st.session_state.distribucion['canales'])
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Total canales", len(datos_resumen))
            with col_stats2:
                st.metric("Total rutas", total_rutas)
            with col_stats3:
                st.metric("Distancia total", f"{formatear_numero(total_distancia)} km")
    
elif pagina == "8. Retail":
    st.title("8. Retail y Almacenamiento")
    st.warning("🔄 **PÁGINA EN DESARROLLO - FASE 2**")
    st.info("""
    **Próximamente en FASE 2:**
    - Tiempo en retail
    - Consumos energéticos (refrigeración)
    - Pérdidas en punto de venta
    - Gestión de residuos retail
    """)
    
elif pagina == "9. Uso y Fin de Vida":
    st.title("9. Uso y Fin de Vida")
    st.warning("🔄 **PÁGINA EN DESARROLLO - FASE 2**")
    st.info("""
    **Próximamente en FASE 2:**
    - Consumo durante uso mejorado
    - Gestión individual por elemento
    - Transporte a gestión final
    - Balance de masa completo
    """)
    
elif pagina == "10. Resultados":
    st.title("10. Resultados de Huella de Carbono")
    st.warning("🔄 **PÁGINA EN DESARROLLO - FASE 2**")
    st.info("""
    **Próximamente en FASE 2:**
    - Cálculos completos con nueva estructura
    - Trazabilidad individual por material
    - Balance de masa detallado
    - Reporte de coherencia de datos
    """)
    
    # Mostrar datos actuales para prueba
    if st.session_state.producto['nombre']:
        st.subheader("📊 Datos Actuales (FASE 1)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Producto", st.session_state.producto['nombre'])
            st.metric("Materias primas", len([mp for mp in st.session_state.materias_primas if mp.get('producto')]))
        
        with col2:
            st.metric("Empaques", len([emp for emp in st.session_state.empaques if emp.get('nombre')]))
            st.metric("Unidad funcional", st.session_state.producto['unidad_funcional'])

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