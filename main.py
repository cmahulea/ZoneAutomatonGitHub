from TFA_ex2 import define_example2
from TimedAutomaton import TimedFiniteAutomaton
from ZoneAutomaton import ZoneAutomaton  # Import the ZoneAutomaton class
from TFA_ex2 import draw_observer




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
        print("\nThe event sequence is invalid.")

    zones = tfa.compute_all_zones()

    print(f"\nZones for all states:",zones)

    # Construir y mostrar el autómata de zonas
    zone_automaton = ZoneAutomaton.from_timed_automaton(tfa)
    zone_automaton = zone_automaton.reduce_states()
    print("\n=== Zone Automaton ===")
    print("Number of states in the zone automaton:", len(zone_automaton.states))
    print("Number of transitions in the zone automaton:", len(zone_automaton.transitions))
    print("Number of events in the zone automaton:", len(zone_automaton.events))

    zone_automaton.draw_automaton("zone_automaton","pdf")

    #reduced_zone_automaton1 = zone_automaton.reduce_adjacent_states()
    #reduced_zone_automaton.draw_automaton("zone_automaton_reduced", "pdf")

    # Calcular el observador a partir del autómata de zonas
#    observer = reduced_zone_automaton.compute_observer()
    observer = zone_automaton.compute_observer()
    print("\n=== Observer Automaton ===")
    print("Number of states in the observer:", len(observer["states"]))
    print("Number of transitions in the observer:", len(observer["transitions"]))
    print("Number of events in the observer:", len(observer["events"]))
    print("Initial observer state:", observer["initial_state"])
    draw_observer(observer, "observer_automaton", "pdf")
    # Dibujar el observador en formato PDF.
    draw_observer(observer, "observer_automaton", "pdf")

if __name__ == '__main__':
    main()
