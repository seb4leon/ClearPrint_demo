"""
Sistema de conversión de unidades para la calculadora de huella de carbono
Formato español: punto para miles, coma para decimales
ELIMINACIÓN AUTOMÁTICA DE CEROS DECIMALES NO SIGNIFICATIVOS
"""

import locale

# Configurar locale para formato español
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Spanish_Spain.1252')
    except:
        pass  # Usar formato por defecto si no hay locale español

# Factores de conversión a unidades base (kg para masa, L para volumen)
UNIDADES_MASA = {
    'mg': 0.000001,
    'g': 0.001,
    'kg': 1.0,
    'ton': 1000.0,
    'lb': 0.453592,
    'oz': 0.0283495
}

UNIDADES_VOLUMEN = {
    'ml': 0.001,
    'L': 1.0,
    'm³': 1000.0,
    'galón': 3.78541,
    'pinta': 0.473176
}

UNIDADES_ENERGIA = {
    'kWh': 1.0,
    'MJ': 0.277778,
    'kcal': 0.001163,
    'BTU': 0.000293071
}

def convertir_unidad(valor, unidad_origen, unidad_destino='kg'):
    """
    Convierte un valor entre unidades
    """
    try:
        valor = float(valor)
        
        # Identificar tipo de unidad
        if unidad_origen in UNIDADES_MASA and unidad_destino in UNIDADES_MASA:
            factor_origen = UNIDADES_MASA[unidad_origen]
            factor_destino = UNIDADES_MASA[unidad_destino]
            
        elif unidad_origen in UNIDADES_VOLUMEN and unidad_destino in UNIDADES_VOLUMEN:
            factor_origen = UNIDADES_VOLUMEN[unidad_origen]
            factor_destino = UNIDADES_VOLUMEN[unidad_destino]
            
        elif unidad_origen in UNIDADES_ENERGIA and unidad_destino in UNIDADES_ENERGIA:
            factor_origen = UNIDADES_ENERGIA[unidad_origen]
            factor_destino = UNIDADES_ENERGIA[unidad_destino]
            
        else:
            # Si las unidades no son del mismo tipo o no se reconocen
            raise ValueError(f"No se puede convertir {unidad_origen} a {unidad_destino}")
        
        # Convertir a unidad base primero, luego a destino
        valor_base = valor * factor_origen
        valor_convertido = valor_base / factor_destino
        
        return valor_convertido
        
    except (ValueError, KeyError) as e:
        raise ValueError(f"Error en conversión: {str(e)}")

def formatear_numero(numero, decimales=None):
    """
    Formatea un número al formato español (punto para miles, coma para decimales)
    ELIMINA AUTOMÁTICAMENTE CEROS NO SIGNIFICATIVOS DESPUÉS DEL PUNTO DECIMAL
    
    Args:
        numero: Número a formatear (int, float, o string)
        decimales: Número máximo de decimales a mostrar (None = automático)
    
    Returns:
        String formateado sin ceros innecesarios
    """
    try:
        if numero is None:
            return "0"
        
        # Convertir a float si es string
        if isinstance(numero, str):
            # Manejar formato español (coma decimal) e inglés (punto decimal)
            numero_limpio = numero.replace('.', '').replace(',', '.')
            try:
                numero = float(numero_limpio)
            except:
                return "0"
        
        numero = float(numero)
        
        # Caso especial: número entero
        if numero == int(numero):
            parte_entera = f"{int(numero):,}".replace(",", ".")
            return parte_entera
        
        # Para números con decimales - NUEVA LÓGICA MEJORADA
        if decimales is not None:
            # Si se especifican decimales, usar ese formato exacto
            formato = f"%.{decimales}f"
            numero_str = formato % numero
        else:
            # Determinar automáticamente los decimales significativos
            # Usar formato científico para detectar ceros no significativos
            numero_str = f"{numero:.10f}"  # Usar 10 decimales como máximo para análisis
            
            # Eliminar ceros a la derecha del punto decimal
            if '.' in numero_str:
                parte_entera, parte_decimal = numero_str.split('.')
                # Eliminar ceros consecutivos desde la derecha
                parte_decimal_limpia = parte_decimal.rstrip('0')
                
                # Si no quedan decimales, devolver solo la parte entera
                if not parte_decimal_limpia:
                    numero_str = parte_entera
                else:
                    numero_str = f"{parte_entera}.{parte_decimal_limpia}"
        
        # Reemplazar punto decimal por coma para formato español
        numero_str = numero_str.replace('.', ',')
        
        # Formatear parte entera con separadores de miles
        if ',' in numero_str:
            parte_entera_str, parte_decimal_str = numero_str.split(',')
            try:
                parte_entera = int(parte_entera_str)
                parte_entera_formateada = f"{parte_entera:,}".replace(",", ".")
                return f"{parte_entera_formateada},{parte_decimal_str}"
            except:
                return numero_str
        else:
            try:
                parte_entera = int(numero_str)
                return f"{parte_entera:,}".replace(",", ".")
            except:
                return numero_str
            
    except Exception as e:
        print(f"Error al formatear número {numero}: {str(e)}")
        return str(numero) if numero is not None else "0"

def formatear_numero_sin_ceros(numero, max_decimales=6):
    """
    Función alternativa específica para eliminar ceros decimales
    (Mantener por compatibilidad)
    """
    return formatear_numero(numero, None)

def obtener_unidades_disponibles(tipo='masa'):
    """
    Devuelve las unidades disponibles para un tipo específico
    """
    if tipo == 'masa':
        return list(UNIDADES_MASA.keys())
    elif tipo == 'volumen':
        return list(UNIDADES_VOLUMEN.keys())
    elif tipo == 'energia':
        return list(UNIDADES_ENERGIA.keys())
    else:
        return []

def validar_unidades_compatibles(unidad1, unidad2):
    """
    Valida que dos unidades sean del mismo tipo (masa, volumen, etc.)
    """
    tipos = []
    for unidad in [unidad1, unidad2]:
        if unidad in UNIDADES_MASA:
            tipos.append('masa')
        elif unidad in UNIDADES_VOLUMEN:
            tipos.append('volumen')
        elif unidad in UNIDADES_ENERGIA:
            tipos.append('energia')
        else:
            tipos.append('desconocido')
    
    return len(tipos) == 2 and tipos[0] == tipos[1] and tipos[0] != 'desconocido'

def mostrar_numero_formateado(valor, unidad=""):
    """
    Función auxiliar para mostrar números formateados con unidades
    Elimina ceros innecesarios automáticamente
    """
    if valor is None or valor == 0:
        return f"0 {unidad}".strip()
    
    valor_formateado = formatear_numero(valor)
    return f"{valor_formateado} {unidad}".strip()

# Tests básicos mejorados
if __name__ == "__main__":
    print("=== PRUEBAS DE FORMATEO SIN CEROS ===")
    
    # Test conversiones
    print("1000 g =", convertir_unidad(1000, 'g', 'kg'), "kg")
    print("1 kg =", convertir_unidad(1, 'kg', 'g'), "g")
    
    # Test formato - CASOS CRÍTICOS MEJORADOS
    test_cases = [
        (35.0, "35.0 → Debe mostrar '35'"),
        (35.000000, "35.000000 → Debe mostrar '35'"),
        (5.06, "5.06 → Debe mostrar '5,06'"),  
        (5.060000, "5.060000 → Debe mostrar '5,06'"),
        (1234.567, "1234.567 → Debe mostrar '1.234,567'"),
        (1234.567000, "1234.567000 → Debe mostrar '1.234,567'"),
        (0.001234, "0.001234 → Debe mostrar '0,001234'"),
        (0.001234000, "0.001234000 → Debe mostrar '0,001234'"),
        (1000.00, "1000.00 → Debe mostrar '1.000'"),
        (1000.00100, "1000.00100 → Debe mostrar '1.000,001'"),
        (0.0, "0.0 → Debe mostrar '0'"),
        (0.0000, "0.0000 → Debe mostrar '0'"),
        (1234567.890, "1234567.890 → Debe mostrar '1.234.567,89'"),
    ]
    
    for numero, descripcion in test_cases:
        resultado = formatear_numero(numero)
        print(f"{descripcion}")
        print(f"Resultado: '{resultado}'\n")