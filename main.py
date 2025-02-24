from TFA_ex2 import define_example2
from TimedAutomaton import TimedFiniteAutomaton
from ZoneAutomaton import ZoneAutomaton  # Import the ZoneAutomaton class





def main():
    # Inicializar el autómata temporizado (asegúrate de que define_example1() retorne intervalos en el formato (m, n, m_inclusive, n_inclusive))
    tfa = define_example2()
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

    zones = tfa.compute_all_zones()

    print(f"\nZones for all states:",zones)

    # Construir y mostrar el autómata de zonas
    zone_automaton = ZoneAutomaton.from_timed_automaton(tfa)
    print("\n=== Zone Automaton ===")
    zone_automaton.print_automaton()

    zone_automaton.draw_automaton("zone_automaton","pdf")

    #reduced_zone_automaton = zone_automaton.reduce_states()

    #reduced_zone_automaton.draw_automaton("zone_automaton_reduced","pdf")

if __name__ == '__main__':
    main()
