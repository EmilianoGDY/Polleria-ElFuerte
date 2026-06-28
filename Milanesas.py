import random

def simular_jornada(escenario, stock_inicial):
    # --- PARÁMETROS DEL SISTEMA ---
    TF = 270.0          # Tiempo final de la jornada (270 minutos)
    alpha = 0.5         # Tiempo de preparación por milanesa (0.5 minutos)
    tiempo_base = 2.0   # Tiempo base de empaque y cobro (2 minutos)
    
    # Determinar Factor de Afluencia (FA) según el escenario
    if escenario.upper() == "SABADO":
        FA = 0.5        # Sábados: arribos el doble de rápido (menor tiempo entre llegadas)
    else:
        FA = 1.0        # Días de semana: afluencia normal
        
    # --- INICIALIZACIÓN DE VARIABLES ---
    T = 0.0             # Reloj de la simulación
    TL = 0.0            # Tiempo de liberación del operario
    N = 0               # Contador de clientes
    
    stock_actual = stock_inicial
    ventas_totales = 0
    ventas_perdidas_totales = 0
    tiempo_espera_total = 0.0
    clientes_esperaron = 0

    print(f"=== SIMULACIÓN DE JORNADA ({escenario.upper()}) ===")
    print(f"Stock Inicial (Variable de Control): {stock_inicial} unidades\n")
    print(f"{'Cliente':<8}{'Arribo (HL)':<12}{'Demanda (M)':<12}{'Preparación (TP)':<18}{'Inicio (HI)':<12}{'Espera (TE)':<12}{'Fin (HF)':<12}{'Stock Rem.':<10}")
    print("-" * 96)

    # --- BUCLE PRINCIPAL (EVENTOS) ---
    while True:
        # 1. Tiempo entre Arribos (TA) - Distribución Empírica
        r1 = random.random()
        if r1 < 0.10:     ta_base = 3.0
        elif r1 < 0.30:   ta_base = 5.0
        elif r1 < 0.60:   ta_base = 15.0
        elif r1 < 0.85:   ta_base = 25.0
        else:             ta_base = 32.0
            
        TA = ta_base * FA
        HL = T + TA  # Hora de Llegada
        
        # Condición de corte: Fin de jornada (Fecha Fija)
        if HL > TF:
            break
            
        N += 1
        T = HL  
        
        # 2. Cantidad Demandada (M) - Variable de Entrada Estocástica
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

        # 3. Tiempo de Preparación (TP)
        TP = tiempo_base + (M * alpha)
        
        # 4. Lógica de la Línea de Espera (¿HL >= TL?)
        if HL >= TL:
            HI = HL
            TE = 0.0
        else:
            HI = TL
            TE = TL - HL
            tiempo_espera_total += TE
            clientes_esperaron += 1
            
        HF = HI + TP
        TL = HF
        
        # 5. Control de Stock
        if stock_actual >= M:
            stock_actual -= M
            ventas_totales += M
        else:
            ventas_perdidas_totales += (M - stock_actual)
            ventas_totales += stock_actual
            stock_actual = 0

        # Mostrar fila en pantalla
        print(f"{N:<8}{HL:<12.2f}{M:<12}{TP:<18.2f}{HI:<12.2f}{TE:<12.2f}{HF:<12.2f}{stock_actual:<10}")

    # --- REPORTE DE MÉTRICAS ---
    print("-" * 96)
    print("=== RESULTADOS DE LA JORNADA ===")
    print(f"Total Clientes Atendidos: {N}")
    print(f"Total Milanesas Vendidas: {ventas_totales} unidades")
    print(f"Ventas Perdidas (Demanda Insatisfecha): {ventas_perdidas_totales} unidades")
    print(f"Stock Sobrante al cierre: {stock_actual} unidades")
    print(f"Tiempo de Espera Promedio en cola: {(tiempo_espera_total / N if N > 0 else 0):.2f} minutos")
    print(f"Porcentaje de clientes que hicieron cola: {(clientes_esperaron / N * 100 if N > 0 else 0):.1f}%\n")

# --- AQUÍ DEFINÍS TU EXPERIMENTO ---
# Modificá el escenario ("SEMANA" o "SABADO") y el stock para probar qué pasa
simular_jornada(escenario="SEMANA", stock_inicial=155)