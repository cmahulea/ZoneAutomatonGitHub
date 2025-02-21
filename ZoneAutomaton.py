from typing import Set, Tuple

class ZoneAutomaton:
    def __init__(self,
                 states: Set[Tuple[str, Tuple[float, float, bool, bool]]],
                 events: Set[str],
                 transitions: Set[Tuple[Tuple[str, Tuple[float, float, bool, bool]], str, Tuple[str, Tuple[float, float, bool, bool]]]],
                 initial_states: Set[Tuple[str, Tuple[float, float, bool, bool]]]):
        """
        Inicializa un autómata de zonas.

        :param states: Conjunto de estados extendidos (V), donde cada estado es una tupla (estado, zona).
                       Cada zona se representa como (inicio, fin, inicio_inclusivo, fin_inclusivo).
        :param events: Conjunto de eventos (E_τ), que incluye eventos observables y de avance temporal.
        :param transitions: Conjunto de transiciones (Δ_z) representadas como
                            ((estado, zona), evento, (siguiente_estado, zona)).
        :param initial_states: Conjunto de estados extendidos iniciales (V0).
        """
        # Se incluyen eventos de tiempo basados en el límite superior de cada zona.
        self.states = states
        self.events = events.union({f"{z[1]}" for _, z in states}).union({f"{z[1]}+" for _, z in states})
        self.transitions = sorted(transitions, key=lambda t: t[0][0])
        self.initial_states = initial_states

    @classmethod
    def from_timed_automaton(cls, timed_automaton):
        """
        Construye un autómata de zonas a partir de un TFA dado.
        """
        states = set()
        events = timed_automaton.events.copy()
        transitions = set()
        initial_states = set()

        # Se inicia con los estados en los que todas las transiciones entrantes reinician el reloj.
        processing_queue = list(timed_automaton.find_states_with_reset_inputs())
        processed_states = set()

        while processing_queue:
            state = processing_queue.pop(0)
            print(f"Processing state: {state}")
            if state in processed_states:
                continue

            zones = timed_automaton.compute_zones(state)
            for i, zone in enumerate(zones):
                extended_state = (state, zone)
                states.add(extended_state)
                if state in timed_automaton.initial_states and i == 0:
                    initial_states.add(extended_state)

                # Agregar transiciones de avance temporal entre zonas, si corresponde.
                if i < len(zones) - 1:
                    current_zone = zones[i]
                    next_zone = zones[i + 1]
                    # Se utiliza el límite superior de la zona actual para etiquetar la transición.
                    if current_zone[3]:
                        event_label_plus = f"{zone[1]}+"
                        transitions.add((extended_state, event_label_plus, (state, next_zone)))
                        events.add(event_label_plus)
                    else:
                        event_label = f"{zone[1]}"
                        transitions.add((extended_state, event_label, (state, next_zone)))
                        events.add(event_label)

                # Para cada evento lógico, se evalúa la transición usando un tiempo representativo dentro de la zona.
                if zone[1] == float('inf'):
                    rep_time = zone[0] + 1  # Valor arbitrario en caso de zona no acotada
                else:
                    rep_time = zone[0] if zone[0] == zone[1] else (zone[0] + zone[1]) / 2

                for event in timed_automaton.events:
                    next_state_zone = timed_automaton.get_next_state(state, event, rep_time)
                    if next_state_zone:
                        next_state, _ = next_state_zone
                        reset_interval = timed_automaton.reset_function((state, event, next_state))
                        if reset_interval is not None:
                            next_zone_val = reset_interval
                        else:
                            next_zone_val = zone  # Se mantiene en la misma zona si no hay reinicio
                        transitions.add((extended_state, event, (next_state, next_zone_val)))
                        if next_state not in processed_states:
                            processing_queue.append(next_state)

            processed_states.add(state)

        return cls(states, events, transitions, initial_states)

    def print_automaton(self):
        """
        Imprime los detalles del autómata de zonas.
        """
        print("Zone Automaton:")
        print(f"States: {self.states}")
        print(f"Events: {self.events}")
        print("Transitions:")
        for transition in self.transitions:
            print(f"  {transition[0]} -- {transition[1]} --> {transition[2]}")
        print(f"Initial States: {self.initial_states}")

    def draw_automaton(self, filename="zone_automaton", format="pdf"):
        """
        Dibuja el autómata de zonas usando Graphviz y guarda el resultado en un archivo.

        :param filename: Nombre base del archivo de salida (sin extensión).
        :param format: Formato de salida (por ejemplo, 'png', 'pdf').
        :return: Objeto Digraph de graphviz.
        """
        from graphviz import Digraph

        # Función auxiliar para formatear la zona (intervalo)
        def format_zone(zone):
            start, end, start_inc, end_inc = zone
            start_bracket = "[" if start_inc else "("
            end_bracket = "]" if end_inc else ")"
            return f"{start_bracket}{start}, {end}{end_bracket}"

        dot = Digraph(comment="Zone Automaton")

        # Crear nodos para cada estado extendido
        for state in self.states:
            state_name, zone = state
            # Se genera un identificador único para cada nodo a partir de sus componentes
            node_id = f"{state_name}_{zone[0]}_{zone[1]}_{int(zone[2])}_{int(zone[3])}"
            label = f"{state_name}\n{format_zone(zone)}"
            print("Label=",label)
            dot.node(node_id, label=label)

        # Crear arcos para cada transición
        for src, event, dst in self.transitions:
            src_name, src_zone = src
            dst_name, dst_zone = dst
            src_id = f"{src_name}_{src_zone[0]}_{src_zone[1]}_{int(src_zone[2])}_{int(src_zone[3])}"
            dst_id = f"{dst_name}_{dst_zone[0]}_{dst_zone[1]}_{int(dst_zone[2])}_{int(dst_zone[3])}"
            dot.edge(src_id, dst_id, label=str(event))

        # Renderiza y guarda el archivo
        dot.render(filename, format=format, cleanup=True)
        return dot