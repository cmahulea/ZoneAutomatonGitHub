from TFA_ex1 import define_example1
from TimedAutomaton import TimedFiniteAutomaton
from ZoneAutomaton import ZoneAutomaton  # Import the ZoneAutomaton class





def main():
    # Inicializar el autómata temporizado (asegúrate de que define_example1() retorne intervalos en el formato (m, n, m_inclusive, n_inclusive))
    tfa = define_example1()
    print("=== Timed Finite Automaton ===")
    tfa.print_automaton()

    # Secuencia de eventos temporizados
    event_sequence = [("b", 0.5), ("c", 2), ("a", 2)]
    result = tfa.run(initial_state="x0", event_sequence=event_sequence)
    if result is not None:
        final_state, final_clock = result
        print(f"\nFinal state: {final_state}, Final clock: {final_clock}")
    else:
        print("\nLa secuencia de eventos es inválida.")

    # Computar las zonas para un estado dado (por ejemplo, "x4")
    state_to_compute = "x2"
    zones = tfa.compute_zones(state_to_compute)
    print(f"\nZones for state {state_to_compute}:")
    for zone in zones:
        # Cada zona se representa como (inicio, fin, inicio_inclusivo, fin_inclusivo)
        print(f"  Zone: {zone}")

    reset_states = tfa.find_states_with_reset_inputs()
    print(f"\nStates where all input arcs reset the timer: {reset_states}")

    # Construir y mostrar el autómata de zonas
    zone_automaton = ZoneAutomaton.from_timed_automaton(tfa)
    print("\n=== Zone Automaton ===")
    zone_automaton.print_automaton()


if __name__ == '__main__':
    main()
