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
        Constructs a zone automaton from a given timed finite automaton (TFA).
        The computation uses the new compute_all_zones() function, which returns,
        for each state, a sorted list of clock bounds. From these bounds, the following
        zone intervals are computed:
          - For bounds B = [b0, b1, ..., b_{n-1}], zones are:
              [b0, b0], (b0, b1), [b1, b1], (b1, b2), ..., [b_{n-1}, b_{n-1}], (b_{n-1}, ∞).
          - Consequently, if B = {0,1,5}, the intervals are:
              [0,0], (0,1), [1,1], (1,5), [5,5], (5,∞).
        Additionally, temporal (time advance) transitions are added between successive zones.
        """
        # Get computed clock bounds for all states (a dict: state -> sorted list of bounds)
        all_bounds = timed_automaton.compute_all_zones()

        # Helper: compute zone intervals from sorted bounds.
        def compute_intervals(bounds):
            intervals = []
            if not bounds:
                return intervals
            # Add degenerate interval at first bound: [b0, b0]
            intervals.append((bounds[0], bounds[0], True, True))
            for i in range(len(bounds) - 1):
                # Open interval (b_i, b_{i+1})
                intervals.append((bounds[i], bounds[i + 1], False, False))
                # Degenerate interval at b_{i+1}: [b_{i+1}, b_{i+1]]
                intervals.append((bounds[i + 1], bounds[i + 1], True, True))
            # Add open interval from last bound to infinity: (b_{n-1}, ∞)
            intervals.append((bounds[-1], float('inf'), False, False))
            return intervals

        # Helper: determine the time event label between two consecutive zones.
        def time_event_label(current_zone, next_zone):
            # current_zone = (a, b, a_inc, b_inc)
            a, b, a_inc, b_inc = current_zone
            # If the current zone is degenerate, label with "b+"; otherwise, label with "b".
            if a == b and a_inc and b_inc:
                return f"{b}+"
            else:
                return f"{b}"

        states = set()
        events = timed_automaton.events.copy()
        transitions = set()
        initial_states = set()

        # Process each state in the TFA.
        for state in timed_automaton.states:
            bounds = all_bounds.get(state, [])
            if not bounds:
                continue  # Skip if no bounds computed.
            zone_intervals = compute_intervals(bounds)
            # Create extended states for this state based on its zone intervals.
            extended_states_for_state = []
            for zone in zone_intervals:
                extended_state = (state, zone)
                states.add(extended_state)
                extended_states_for_state.append(extended_state)
            # Mark the first extended state as initial if the state is an initial state.
            if state in timed_automaton.initial_states:
                initial_states.add(extended_states_for_state[0])

            # Add temporal transitions between successive zones for the same state.
            for i in range(len(extended_states_for_state) - 1):
                src = extended_states_for_state[i]
                dst = extended_states_for_state[i + 1]
                label = time_event_label(zone_intervals[i], zone_intervals[i + 1])
                transitions.add((src, label, dst))
                events.add(label)

            # For each logical event, add transitions from the extended states.
            for ext_state, zone in zip(extended_states_for_state, zone_intervals):
                lower, upper, lower_inc, upper_inc = zone
                # Choose a representative time within the zone.
                if upper == float('inf'):
                    rep_time = lower + 1  # Arbitrary value for unbounded interval.
                else:
                    if lower == upper:  # Degenerate zone.
                        rep_time = lower
                    else:
                        rep_time = (lower + upper) / 2
                # Evaluate transitions for each event.
                for event in timed_automaton.events:
                    next_state_zone = timed_automaton.get_next_state(state, event, rep_time)
                    if next_state_zone:
                        next_state, _ = next_state_zone
                        reset_interval = timed_automaton.reset_function((state, event, next_state))
                        if reset_interval is not None:
                            # If a reset occurs, the clock is reset; use the lower bound (degenerate interval).
                            next_zone = (reset_interval[0], reset_interval[0], True, True)
                        else:
                            # Otherwise, remain in the same zone.
                            next_zone = zone
                        dst_extended = (next_state, next_zone)
                        transitions.add((ext_state, event, dst_extended))
                        states.add(dst_extended)

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

    def draw_automaton(self, filename, format):
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
            #print("Label=",label)
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

    def reduce_states(self):
        """
        Returns a new ZoneAutomaton with reduced extended states.
        Extended states (of the form (x, zone)) for the same discrete state x are merged
        if they are connected only by a timed transition and if either the non-timed incoming
        (or outgoing) transitions of the first state are empty or equal to those of the second.
        Also, their zone intervals must be compatible for merging, meaning that the upper bound of the
        first equals the lower bound of the second and the first interval is closed at its upper end.
        The new zone is the convex hull (union) of the merged intervals.
        """
        def is_timed_label(label: str) -> bool:
            # A timed label is assumed to be either a numeric string or a numeric string followed by '+'.
            return label.isdigit() or (label.endswith("+") and label[:-1].isdigit())

        def union_intervals(i1: Tuple[float, float, bool, bool],
                            i2: Tuple[float, float, bool, bool]) -> Tuple[float, float, bool, bool]:
            """
            Returns the convex hull (union) of two adjacent intervals.
            Assumes:
                i1 = (l1, u1, li1, ui1) and i2 = (l2, u2, li2, ui2) with u1 == l2.
            The resulting interval is (l1, u2, li1, ui2).
            """
            return (i1[0], i2[1], i1[2], i2[3])

        def get_non_timed_outgoing(ext_state, transitions) -> Set[Tuple[str, Tuple[str, Tuple[float, float, bool, bool]]]]:
            # Returns outgoing transitions (label, destination) from ext_state excluding timed transitions.
            return {(label, dst) for (src, label, dst) in transitions
                    if src == ext_state and not is_timed_label(label)}

        def get_non_timed_incoming(ext_state, transitions) -> Set[Tuple[Tuple[str, Tuple[float, float, bool, bool]], str]]:
            # Returns incoming transitions (source, label) to ext_state excluding timed transitions.
            return {(src, label) for (src, label, dst) in transitions
                    if dst == ext_state and not is_timed_label(label)}

        def can_merge(s1, s2) -> bool:
            """
            Determines if two extended states s1 and s2 (for the same discrete state) can be merged.
            They can be merged if:
              (a) There is a timed transition from s1 to s2,
              (b) Their non-timed incoming transitions are either empty (for s1) or equal for both s1 and s2,
              (c) Their non-timed outgoing transitions are either empty (for s1) or equal for both s1 and s2, and
              (d) Their zone intervals are compatible for merging:
                  Let i1 = s1[1] and i2 = s2[1]. Then i1[1] (the upper bound of i1)
                  must equal i2[0] (the lower bound of i2) and i1 must be closed at its upper bound.
            """

            print("Check merging ",s1," with ",s2)
            if s1[0] != s2[0]:
                return False
            if not any(src == s1 and dst == s2 and is_timed_label(label)
                       for (src, label, dst) in self.transitions):
                #print("src=",src,"label=",label,"dst=",dst)
                return False

            nt_in1 = get_non_timed_incoming(s1, self.transitions)
            nt_in2 = get_non_timed_incoming(s2, self.transitions)
            nt_out1 = get_non_timed_outgoing(s1, self.transitions)
            nt_out2 = get_non_timed_outgoing(s2, self.transitions)
            print("nt_in1=",nt_in1,"nt_in2=",nt_in2,"nt_out1=",nt_out1,"nt_out2=",nt_out2)

            # Allow merging if s1 has no non-timed incoming transitions or if they match s2.
            if nt_in1 and nt_in1 != nt_in2:
                return False
            # Similarly for outgoing transitions.
            if nt_out1 and nt_out1 != nt_out2:
                return False

            i1, i2 = s1[1], s2[1]
            # The intervals must be adjacent.
            if i1[1] != i2[0]:
                return False
            # To merge, the first interval must be closed at its upper bound.
            if not i1[3]:
                return False
            print("\nMergeable")
            return True

        # Group extended states by their discrete state.
        groups = {}
        for ext_state in self.states:
            x, zone = ext_state
            groups.setdefault(x, []).append(ext_state)

        print("Groups=",groups)
        new_states = set()
        mapping = {}  # Maps each original extended state to its merged (new) extended state.
        new_initial_states = set()

        for x, state_list in groups.items():
            # Sort extended states for x by the lower bound of their zone.
            state_list.sort(key=lambda s: s[1][0])
            merged_group = []
            for s in state_list:
                if merged_group and can_merge(merged_group[-1], s):
                    # Merge current extended state with s.
                    merged_group[-1] = (x, union_intervals(merged_group[-1][1], s[1]))
                else:
                    merged_group.append(s)
            # Build mapping: each original extended state is mapped to the merged state covering it.
            for old_state in state_list:
                assigned = False
                for m in merged_group:
                    if m[1][0] <= old_state[1][0] and m[1][1] >= old_state[1][1]:
                        mapping[old_state] = m
                        assigned = True
                        break
                if not assigned:
                    mapping[old_state] = old_state
            new_states.update(merged_group)
            # For discrete initial states, choose the merged state with the smallest lower bound.
            if x in self._discrete_initial_states():
                new_initial_states.add(min(merged_group, key=lambda s: s[1][0]))

        # Remap transitions using the mapping.
        new_transitions = set()
        for (src, label, dst) in self.transitions:
            new_src = mapping.get(src, src)
            new_dst = mapping.get(dst, dst)
            new_transitions.add((new_src, label, new_dst))
        new_events = {e for (_, e, _) in new_transitions}

        return ZoneAutomaton(new_states, new_events, new_transitions, new_initial_states)

    def _discrete_initial_states(self) -> Set[str]:
        """
        Helper method to extract the underlying discrete initial states from the extended initial states.
        """
        return {x for (x, _) in self.initial_states}


