import random

def simular_jornada_completa(escenario, stock_inicial):
    # --- PARÁMETROS Y CONDICIONES INICIALES (CI) ---
    Tf = 270.0            # Tiempo final de la jornada (270 minutos)
    alpha = 0.5           # Tiempo de preparación por milanesa (minutos)
    precioMilanesa = 1500 # Valor de ejemplo para el cálculo de ingresos
    Tol = 15.0            # Tolerancia máxima de espera del cliente (minutos)
    
    # Evaluar Escenario (ES) -> Factor de Afluencia (FA)
    if escenario.upper() == "SABADO":
        FA = 0.5
    else:
        FA = 1.0
        
    # Inicializar variables (Bloque T=0 | TL=0 | N=0 | NC=0)
    T = 0.0
    TL = 0.0
    N = 0
    NC = 0
    stock_actual = stock_inicial
    
    # Métricas de salida
    ganancia_total = 0.0
    perdida_total = 0.0
    clientes_atendidos = 0
    clientes_perdidos_cola = 0
    clientes_perdidos_tolerancia = 0
    clientes_perdidos_cierre = 0
    clientes_perdidos_stock = 0

    print(f"=== INICIO DE SIMULACIÓN ({escenario.upper()}) ===")
    print(f"Stock Inicial: {stock_inicial} unidades\n")
    print(f"{'N':<4}{'HL':<8}{'M':<5}{'TP':<6}{'NC':<4}{'HI':<8}{'TE':<6}{'HF':<8}{'Estado':<25}")
    print("-" * 85)

    # Lista para llevar el registro de los momentos en que se liberará el operario
    # Nos sirve para calcular de forma exacta cuánta gente hay en la cola (NC) al llegar un cliente
    tiempos_liberacion_activos = []

    # --- BUCLE PRINCIPAL ---
    while True:
        # Calcular TA (Distribución empírica basada en tus datos)
        r1 = random.random()
        if r1 < 0.10:     ta_base = 3.0
        elif r1 < 0.30:   ta_base = 5.0
        elif r1 < 0.60:   ta_base = 15.0
        elif r1 < 0.85:   ta_base = 25.0
        else:             ta_base = 32.0
            
        TA = ta_base * FA
        N = N + 1
        HL = T + TA  # Hora de Llegada
        
        # Rombo de Decisión: ¿HL > Tf?
        if HL > Tf:
            clientes_perdidos_cierre += 1
            print(f"-   {HL:<8.2f}{'-':<5}{'-':<6}{'-':<4}{'-':<8}{'-':<6}{'-':<8}{'Perdido por cierre':<25}")
            break
            
        # Calcular NC (Clientes en cola en el momento exacto de la llegada HL)
        # Filtramos cuántos clientes anteriores todavía no terminaron de ser atendidos
        tiempos_liberacion_activos = [t for t in tiempos_liberacion_activos if t > HL]
        NC = len(tiempos_liberacion_activos)
        
        # Generar cantidad demandada (M)
        r2 = random.random()
        if r2 < 0.0450:    M = 2
        elif r2 < 0.1240:  M = 4
        elif r2 < 0.4050:  M = 6
        elif r2 < 0.4610:  M = 8
        elif r2 < 0.5280:  M = 10
        elif r2 < 0.7750:  M = 12
        elif r2 < 0.8540:  M = 18
        elif r2 < 0.9210:  M = 24
        elif r2 < 0.9770:  M = 36
        else:              M = 48

        TP = M * alpha
        
        # Rombo de Decisión: ¿NC > 3?
        if NC > 3:
            perdida = M * precioMilanesa
            perdida_total += perdida
            clientes_perdidos_cola += 1
            print(f"{N:<4}{HL:<8.2f}{M:<5}{TP:<6.1f}{NC:<4}{'-':<8}{'-':<6}{'-':<8}{'Perdido (Cola > 3)':<25}")
            T = HL
            continue
            
        # Calcular HI y TE (Lógica del Máximo)
        HI = max(HL, TL)
        TE = HI - HL
        
        # Rombo de Decisión: ¿TE >= Tol?
        if TE >= Tol:
            perdida = M * precioMilanesa
            perdida_total += perdida
            clientes_perdidos_tolerancia += 1
            print(f"{N:<4}{HL:<8.2f}{M:<5}{TP:<6.1f}{NC:<4}{HI:<8.2f}{TE:<6.1f}{'-':<8}{'Perdido (Supera Tol)':<25}")
            T = HL
            continue
            
        # --- CONTROL DE STOCK ---
        if stock_actual >= M:
            stock_actual -= M
            
            HF = HI + TP
            TL = HF
            tiempos_liberacion_activos.append(TL) # Registrar para futuros cálculos de NC
            
            ganancia = M * precioMilanesa
            ganancia_total += ganancia
            clientes_atendidos += 1
            
            print(f"{N:<4}{HL:<8.2f}{M:<5}{TP:<6.1f}{NC:<4}{HI:<8.2f}{TE:<6.1f}{HF:<8.2f}{f'Atendido (Stock: {stock_actual})':<25}")
        else:
            # Si no hay stock suficiente, el cliente se pierde por quiebre de inventario
            perdida = M * precioMilanesa
            perdida_total += perdida
            clientes_perdidos_stock += 1
            print(f"{N:<4}{HL:<8.2f}{M:<5}{TP:<6.1f}{NC:<4}{'-':<8}{'-':<6}{'-':<8}{'Perdido (Sin Stock)':<25}")
            
        T = HL

    # --- REPORTE FINAL ---
    print("-" * 85)
    print("=== RESUMEN DE LA EXPERIMENTACIÓN ===")
    print(f"Clientes Atendidos con éxito: {clientes_atendidos}")
    print(f"Clientes Perdidos por Cola saturada (>3): {clientes_perdidos_cola}")
    print(f"Clientes Perdidos por Paciencia/Tolerancia (>=15 min): {clientes_perdidos_tolerancia}")
    print(f"Clientes Perdidos por Quiebre de Stock: {clientes_perdidos_stock}")
    print(f"Clientes Rechazados por Cierre de local: {clientes_perdidos_cierre}")
    print(f"GANANCIA TOTAL OBTENIDA: ${ganancia_total:,.2f}")
    print(f"PÉRDIDA TOTAL POR VENTAS NO REALIZADAS: ${perdida_total:,.2f}")
    print(f"Stock Remanente: {stock_actual} unidades")

# Ejecutar una corrida de prueba (Podés variar el stock para tus experimentos)
simular_jornada_completa(escenario="SABADO", stock_inicial=150)