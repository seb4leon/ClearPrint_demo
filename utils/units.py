"""
Sistema de conversión de unidades para la calculadora de huella de carbono
Formato español: punto para miles, coma para decimales
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

def formatear_numero(numero, decimales=3):
    """
    Formatea un número al formato español (punto para miles, coma para decimales)
    """
    try:
        if numero is None or numero == 0:
            return "0"
        
        numero = float(numero)
        
        # Formatear según la magnitud del número
        if abs(numero) >= 1000000:
            return locale.format_string("%.1f", numero, grouping=True).replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(numero) >= 1000:
            return locale.format_string("%.0f", numero, grouping=True).replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(numero) >= 100:
            return locale.format_string("%.1f", numero, grouping=True).replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(numero) >= 10:
            return locale.format_string("%.2f", numero, grouping=True).replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formato = f"%.{decimales}f"
            return locale.format_string(formato, numero, grouping=True).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        # Fallback si locale no funciona
        return f"{numero:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
    
    return tipos[0] == tipos[1] and tipos[0] != 'desconocido'

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

# Tests básicos
if __name__ == "__main__":
    # Test conversiones
    print("1000 g =", convertir_unidad(1000, 'g', 'kg'), "kg")
    print("1 kg =", convertir_unidad(1, 'kg', 'g'), "g")
    print("1000 ml =", convertir_unidad(1000, 'ml', 'L'), "L")
    
    # Test formato
    print("Formato español:", formatear_numero(1234.567))
    print("Formato español:", formatear_numero(0.001234))