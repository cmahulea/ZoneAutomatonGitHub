from typing import Set, Tuple, Optional
from graphviz import Digraph


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
        Finally, for each extended state, self-loop transitions are added for every timed event
        whose numeric value (interpreted as an integer, possibly with a trailing '+')
        falls within the zone interval.
        """
        # Get computed clock bounds for all states (a dict: state -> sorted list of bounds)
        all_bounds = timed_automaton.compute_all_zones()
        print('Zones', all_bounds)

        all_bounds_values = timed_automaton.compute_all_guard_and_reset_values()
        print("all_bounds_values", all_bounds_values)

        # Helper: compute zone intervals from sorted bounds.
        def compute_intervals(bounds):
            intervals = []
            if not bounds:
                return intervals
            # If the last bound is infinity, remove it.
            if bounds[-1] == float('inf'):
                bounds = bounds[:-1]
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
            a, b, a_inc, b_inc = current_zone
            if a == b and a_inc and b_inc:
                return f"{b}+"
            else:
                return f"{b}"

        # Local helper to check if an event label represents a timed event.
        def is_timed_event(event: str) -> bool:
            if event.endswith('+'):
                event = event[:-1]
            if event.isdigit():
                return True
            if event.startswith('-') and event[1:].isdigit():
                return True
            return False

        # Local helper to check if a numeric value is within a zone interval.
        def value_in_zone(event: str, zone: Tuple[float, float, bool, bool]) -> bool:
            """
            Determina si el valor numérico representado por el evento cae dentro del intervalo 'zone',
            considerando los límites abiertos/cerrados y que, si el evento termina en '+', se suma un pequeño epsilon.

            Si el intervalo es degenerate ([a, a] con ambos extremos cerrados), devuelve False.

            :param event: Etiqueta del evento, p. ej. "5" o "5+".
            :param zone: Intervalo representado como (lower, upper, lower_inclusive, upper_inclusive).
            :return: True si el valor (ajustado en caso de '+') está dentro del intervalo, False en otro caso.
            """
            lower, upper, lower_inc, upper_inc = zone

            # Si el intervalo es degenerate [a,a] cerrado, no se añade self-loop.
            if lower == upper and lower_inc and upper_inc:
                return False

            epsilon = 1e-9
            try:
                # Si el evento termina en '+', interpretar como número + epsilon.
                if event.endswith('+'):
                    v = float(event.rstrip('+')) + epsilon
                else:
                    v = float(event)
            except ValueError:
                return False

            # Comparación considerando los límites abiertos/cerrados.
            if lower_inc:
                lower_ok = v >= lower + epsilon
            else:
                lower_ok = v > lower + epsilon

            if upper == float('inf'):
                upper_ok = True
            else:
                if upper_inc:
                    upper_ok = v <= upper
                else:
                    upper_ok = v < upper

            return lower_ok and upper_ok

        # Build a set of timed events from the TFA events.

        states = set()
        events = timed_automaton.events.copy()
        transitions = set()
        initial_states = set()

        # Compute a global set of intervals from the overall bounds.
        zone_intervals_global = compute_intervals(all_bounds_values)

        # Calcular la lista de eventos temporales a partir de all_bounds_values
        timed_event_list = []
        for value in all_bounds_values:
            # Agregar la representación sin '+' y con '+'
            timed_event_list.append(str(value))
            timed_event_list.append(str(value) + "+")

        # Process each state in the TFA.
        for state in timed_automaton.states:
            #bounds = all_bounds.get(state, [])
            #lower_value = 0
            #upper_value = 6
            bounds = all_bounds_values
            #bounds = list(range(lower_value, upper_value))
            # Use state-specific intervals if available; otherwise, fall back to global intervals.
            zone_intervals = compute_intervals(bounds) if bounds else zone_intervals_global
            extended_states_for_state = []
            for zone in zone_intervals:
                extended_state = (state, zone)
                states.add(extended_state)
                extended_states_for_state.append(extended_state)
            if state in timed_automaton.initial_states and extended_states_for_state:
                initial_states.add(extended_states_for_state[0])

            # Add temporal transitions between successive zones for the same state.
            for i in range(len(extended_states_for_state) - 1):
                src = extended_states_for_state[i]
                dst = extended_states_for_state[i + 1]
                label = time_event_label(zone_intervals[i], zone_intervals[i + 1])
                transitions.add((src, label, dst))
                events.add(label)

            #print('Timed Events=',timed_event_list)

            # Para cada estado extendido, se añaden self-loops para cada evento temporizado
            # cuyo valor numérico (con epsilon en caso de '+' si procede) se encuentre dentro del intervalo.
            for ext_state, zone in zip(extended_states_for_state, zone_intervals):
                lower, upper, lower_inc, upper_inc = zone
                for event in timed_event_list:
                    # Si el evento termina en '+' y su valor base coincide con el límite inferior
                    # y el límite inferior está abierto, se omite ese self-loop.
                    if is_timed_event(event):
                        if value_in_zone(event, zone):
                            transitions.add((ext_state, event, ext_state))

            # For each logical event, add transitions from the extended states.
            for ext_state, zone in zip(extended_states_for_state, zone_intervals):
                lower, upper, lower_inc, upper_inc = zone
                rep_time = lower + 1 if upper == float('inf') else (lower if lower == upper else (lower + upper) / 2)
                for event in timed_automaton.events:
                    next_state_zone = timed_automaton.get_next_state(state, event, rep_time)
                    if next_state_zone:
                        next_state, _ = next_state_zone
                        reset_interval = timed_automaton.reset_function((state, event, next_state))
                        if reset_interval is not None:
                            next_zone = (reset_interval[0], reset_interval[0], True, True)
                        else:
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

        Si entre dos nodos (o self-loops) existen varias transiciones, se dibuja un único arco
        con la lista de eventos en orden ascendente, delimitados por {}.

        :param filename: Nombre base del archivo de salida (sin extensión).
        :param format: Formato de salida (por ejemplo, 'png', 'pdf').
        :return: Objeto Digraph de graphviz.
        """

        def format_zone(zone):
            start, end, start_inc, end_inc = zone
            start_bracket = "[" if start_inc else "("
            end_bracket = "]" if end_inc else ")"
            return f"{start_bracket}{start}, {end}{end_bracket}"

        dot = Digraph(comment="Zone Automaton")
        # Establecer atributos para controlar el tamaño y margen de la gráfica, evitando dimensiones excesivas.
        dot.attr('graph', size="8.5,11!", margin="0.1")

        # Crear un diccionario para asignar un id único a cada nodo
        node_ids = {}
        for state in self.states:
            state_name, zone = state
            node_id = f"{state_name}_{zone[0]}_{zone[1]}_{int(zone[2])}_{int(zone[3])}"
            node_ids[state] = node_id
            label = f"{state_name}\n{format_zone(zone)}"
            dot.node(node_id, label=label)

        # Agrupar las transiciones: clave (src, dst), valor: conjunto de eventos
        edge_groups = {}
        for src, event, dst in self.transitions:
            key = (src, dst)
            if key not in edge_groups:
                edge_groups[key] = set()
            edge_groups[key].add(event)

        # Dibujar los arcos agrupados
        for (src, dst), events in edge_groups.items():
            src_id = node_ids[src]
            dst_id = node_ids[dst]
            sorted_events = sorted(events)
            if len(sorted_events) > 1:
                label = "{" + ", ".join(sorted_events) + "}"
            else:
                label = "".join(
                    sorted_events)  # O simplemente sorted_events[0] si estás seguro de que siempre hay al menos un evento
            dot.edge(src_id, dst_id, label=label)

        dot.render(filename, format=format, cleanup=True)
        return dot

    def reduce_states(self):
        """
        Returns a new ZoneAutomaton with unreachable states removed.
        Unreachable states are those that cannot be reached from any of the initial states
        following the transitions.
        """
        # Compute reachable states using a breadth-first search.
        reachable_states = set()
        frontier = list(self.initial_states)
        while frontier:
            current = frontier.pop(0)
            if current not in reachable_states:
                reachable_states.add(current)
                # Look for transitions originating from the current state.
                for (src, event, dst) in self.transitions:
                    if src == current and dst not in reachable_states:
                        frontier.append(dst)

        # Filter transitions: keep only those whose source and destination are reachable.
        reduced_transitions = {
            (src, event, dst)
            for (src, event, dst) in self.transitions
            if src in reachable_states and dst in reachable_states
        }

        # Recompute the events set from the remaining transitions.
        reduced_events = {event for (_, event, _) in reduced_transitions}

        # The initial states remain those in the intersection.
        reduced_initial_states = self.initial_states.intersection(reachable_states)

        # Return a new ZoneAutomaton with the reduced components.
        return ZoneAutomaton(reachable_states, reduced_events, reduced_transitions, reduced_initial_states)

    def _is_observable(self, event: str) -> bool:
        """
        Returns True if the event is observable.
        Unobservable events are assumed to have parentheses around them.
        """
        return not (event.startswith("(") and event.endswith(")"))

    def _compute_unobservable_closure(self, states: set) -> set:
        """
        Computes the closure of a set of extended states with respect to unobservable transitions.
        That is, it returns all states reachable from any state in 'states' by following transitions
        whose events are unobservable.
        """
        closure = set(states)
        stack = list(states)
        while stack:
            current_state = stack.pop()
            for (src, event, dst) in self.transitions:
                if src == current_state and not self._is_observable(event) and dst not in closure:
                    closure.add(dst)
                    stack.append(dst)
        return closure

    def compute_observer(self):
        """
        Computes the observer automaton, ensuring that each observer state (a frozenset of extended states)
        has a common time interval (i.e. the time intervals of the constituent states are compatible).

        The observer is constructed as follows:
          1. The initial observer state is the unobservable closure of the set of initial states,
             filtered to include only those states whose time intervals have a non-empty intersection.
          2. For each observer state Q and each observable event e, the next state is computed as the
             unobservable closure of all states reachable via an e-transition from any state in Q,
             but only if the resulting set of extended states has a common time interval.
          3. Only observable events are retained in the observer transitions.

        Returns:
            A dictionary representing the observer automaton with the following keys:
              - "states": a set of frozensets of extended states (each frozenset is an observer state)
              - "events": the set of observable events
              - "transitions": a set of tuples (source, event, destination) where source and destination are frozensets
              - "initial_state": the initial observer state (a frozenset)
        """

        # Función auxiliar para calcular la intersección de dos intervalos.
        def intersect_intervals(i1: Tuple[float, float, bool, bool],
                                i2: Tuple[float, float, bool, bool]) -> Tuple[float, float, bool, bool]:
            lower1, upper1, linc1, uinc1 = i1
            lower2, upper2, linc2, uinc2 = i2
            lower = max(lower1, lower2)
            # Determinar si el límite inferior es inclusivo:
            if lower1 == lower2:
                linc = linc1 and linc2
            elif lower1 > lower2:
                linc = linc1
            else:
                linc = linc2
            upper = min(upper1, upper2)
            if upper1 == upper2:
                uinc = uinc1 and uinc2
            elif upper1 < upper2:
                uinc = uinc1
            else:
                uinc = uinc2
            # Verificar que la intersección no sea vacía:
            if lower < upper or (lower == upper and linc and uinc):
                return (lower, upper, linc, uinc)
            else:
                return None

        # Función auxiliar para calcular la intersección de una lista de intervalos.
        def common_interval(intervals) -> Optional[Tuple[float, float, bool, bool]]:
            if not intervals:
                return None
            current = intervals[0]
            for inter in intervals[1:]:
                current = intersect_intervals(current, inter)
                if current is None:
                    return None
            return current

        # Dada una observer state (frozenset de estados extendidos), se calcula el intervalo común.
        def common_zone(observer_state) -> Optional[Tuple[float, float, bool, bool]]:
            zones = [zone for (_, zone) in observer_state]
            return common_interval(zones)

        # Paso 1: calcular el estado observador inicial (la clausura no observable de los estados iniciales)
        initial_closure = self._compute_unobservable_closure(self.initial_states)
        initial_obs = frozenset(initial_closure)
        #print('initial_obs',initial_obs)

        # Solo consideramos el estado inicial si sus intervalos son compatibles.
        if common_zone(initial_obs) is None:
            # Si no hay intersección, se descarta (o se puede lanzar un error)
            initial_obs = frozenset()

        observer_states = {initial_obs}
        observer_transitions = {}  # clave: (observer_state, event), valor: next observer state
        queue = [initial_obs]

        # Se consideran solo los eventos observables.
        observable_events = {e for e in self.events if self._is_observable(e)}

        print('Observable event:',observable_events)
        # Bucle principal: para cada estado observador y cada evento observable,
        # se calcula el conjunto de estados alcanzables y se verifica que tengan un intervalo común.
        while queue:
            current_obs_state = queue.pop(0)
            #print('Current_obs_state',current_obs_state)
            # Verificar que el estado observador tenga un intervalo común válido.
            #if common_zone(current_obs_state) is None:
            #    continue
            for event in observable_events:
                next_states = set()
                for state in current_obs_state:
                    for (src, trans_event, dst) in self.transitions:
                        if src == state and trans_event == event:
                            next_states.add(dst)
                if next_states:
                    next_closure = frozenset(self._compute_unobservable_closure(next_states))
                    #if common_zone(next_closure) is not None:
                    observer_transitions[(current_obs_state, event)] = next_closure
                    if next_closure not in observer_states:
                        observer_states.add(next_closure)
                        queue.append(next_closure)

        observer_transitions_set = {
            (src, event, dst) for ((src, event), dst) in observer_transitions.items()
        }

        return {
            "states": observer_states,
            "events": observable_events,
            "transitions": observer_transitions_set,
            "initial_state": initial_obs
        }


    def reduce_adjacent_state_pair(self,
                                   q1: Tuple[str, Tuple[float, float, bool, bool]],
                                   q2: Tuple[str, Tuple[float, float, bool, bool]]
                                   ) -> Tuple[str, Tuple[float, float, bool, bool]]:
        """
        Fusiona dos estados extendidos q1 y q2 si:
          - Ambos pertenecen al mismo estado discreto.
          - Están conectados únicamente por una única transición cuyo evento es de tiempo.

        La fusión se realiza creando un nuevo estado que combina los intervalos de q1 y q2,
        tomando el límite inferior de q1 y el límite superior de q2, y se actualizan los conjuntos
        de estados, transiciones e iniciales redirigiendo todas las conexiones hacia el nuevo estado.

        :param q1: Primer estado extendido (ej.: ("q", (a, b, a_inc, b_inc))).
        :param q2: Segundo estado extendido (ej.: ("q", (c, d, c_inc, d_inc))).
        :return: El nuevo estado fusionado.
        :raises ValueError: Si los estados no pertenecen al mismo estado discreto o la transición
                            entre ellos no es única o no corresponde a un evento de tiempo.
        """
        # Verificar que ambos estados tengan el mismo nombre discreto.
        if q1[0] != q2[0]:
            raise ValueError("Los estados no pertenecen al mismo estado discreto y no pueden fusionarse.")

        # Buscar la única transición que conecta q1 con q2.
        candidate_transitions = [t for t in self.transitions if t[0] == q1 and t[2] == q2]
        if len(candidate_transitions) != 1 or not self._is_timed_event(candidate_transitions[0][1]):
            raise ValueError("No existe una única transición con evento de tiempo entre los estados proporcionados.")

        # Fusionar los intervalos: se asume que q1 y q2 son adyacentes y se unen.
        zone1 = q1[1]  # (a, b, a_inc, b_inc)
        zone2 = q2[1]  # (c, d, c_inc, d_inc)
        fused_zone = (zone1[0], zone2[1], zone1[2], zone2[3])
        new_state = (q1[0], fused_zone)

        # Actualizar el conjunto de estados: eliminar q1 y q2 e incluir el nuevo estado.
        self.states = {s for s in self.states if s != q1 and s != q2}
        self.states.add(new_state)

        # Actualizar las transiciones: redirigir todas las transiciones que tienen a q1 o q2
        # como fuente o destino hacia el nuevo estado.
        new_transitions = set()
        for (src, event, dst) in self.transitions:
            # Omitir la transición que conecta directamente q1 con q2.
            if src == q1 and dst == q2:
                continue
            new_src = new_state if src in (q1, q2) else src
            new_dst = new_state if dst in (q1, q2) else dst
            new_transitions.add((new_src, event, new_dst))
        self.transitions = new_transitions

        # Actualizar los estados iniciales, reemplazando q1 o q2 por el nuevo estado si están presentes.
        self.initial_states = {new_state if s in (q1, q2) else s for s in self.initial_states}

        return new_state

    def _is_timed_event(self, event: str) -> bool:
        """
        Determina si un evento es de tiempo.
        Se asume que un evento de tiempo es aquel cuyo label puede convertirse a float,
        permitiendo opcionalmente que termine con '+'.
        """
        try:
            float(event.rstrip('+'))
            return True
        except ValueError:
            return False

    def reduce_adjacent_states(self):
        """
        Iteratively reduces the automaton by merging adjacent extended states connected by a timed event transition.
        The reduction is performed if either:
          - The source node has no other outgoing transitions; or
          - For every non-timed outgoing transition from the source, there is a corresponding transition from the destination
            with the same event and target.
        This updates the automaton's states, transitions, and initial states.
        """
        merged = True
        while merged:
            merged = False
            # Iterate over a copy of the transitions.
            for t in list(self.transitions):
                src, event, dst = t
                # Candidate: states must belong to the same discrete state and the transition must be timed.
                if src[0] != dst[0] or not self._is_timed_event(event):
                    continue

                # Gather all outgoing transitions from src.
                outgoing_from_src = [tr for tr in self.transitions if tr[0] == src]

                # Case 1: src has only one outgoing transition.
                if len(outgoing_from_src) == 1:
                    try:
                        self.reduce_adjacent_state_pair(src, dst)
                        merged = True
                        break  # Restart the iteration after modification.
                    except ValueError:
                        continue
                else:
                    # Case 2: src has additional outgoing transitions.
                    # For each non-timed transition (src, e, X) from src, check that there's a corresponding (dst, e, X).
                    non_timed_transitions = [tr for tr in outgoing_from_src if not self._is_timed_event(tr[1])]
                    all_match = True
                    for (_, e, target) in non_timed_transitions:
                        corresponding = [tr for tr in self.transitions if
                                         tr[0] == dst and tr[1] == e and tr[2] == target]
                        if not corresponding:
                            all_match = False
                            break
                    if all_match:
                        try:
                            self.reduce_adjacent_state_pair(src, dst)
                            merged = True
                            break  # Restart the iteration after modification.
                        except ValueError:
                            continue
        return self

    def draw_automaton_by_state(self, filename, format):
        """
        Dibuja el autómata de zonas agrupando los estados extendidos en filas,
        de manera que cada fila corresponde a un estado discreto y sus diferentes zonas,
        y establece la orientación en landscape.
        """

        def format_zone(zone):
            start, end, start_inc, end_inc = zone
            start_bracket = "[" if start_inc else "("
            end_bracket = "]" if end_inc else ")"
            return f"{start_bracket}{start}, {end}{end_bracket}"

        dot = Digraph(comment="Zone Automaton by State")
        # Configurar la orientación en landscape: rankdir=LR indica una disposición de izquierda a derecha.
        dot.attr('graph', size="11,8.5!", margin="0.1", rankdir="LR")

        # Agrupar los estados extendidos por su estado discreto.
        state_groups = {}
        for state in self.states:
            discrete_state, zone = state
            state_groups.setdefault(discrete_state, []).append(state)

        node_ids = {}
        # Crear subgrafos para cada estado discreto
        for discrete_state, states_group in state_groups.items():
            with dot.subgraph(name=f"cluster_{discrete_state}") as c:
                c.attr(label=discrete_state)
                # Usar rank=same para que se alineen en la misma fila.
                c.attr(rank='same')
                for state in states_group:
                    _, zone = state
                    node_id = f"{state[0]}_{zone[0]}_{zone[1]}_{int(zone[2])}_{int(zone[3])}"
                    node_ids[state] = node_id
                    label = f"{state[0]}\n{format_zone(zone)}"
                    c.node(node_id, label=label)

        # Agrupar y dibujar las transiciones, similar al método original.
        edge_groups = {}
        for src, event, dst in self.transitions:
            key = (src, dst)
            if key not in edge_groups:
                edge_groups[key] = set()
            edge_groups[key].add(event)

        for (src, dst), events in edge_groups.items():
            src_id = node_ids[src]
            dst_id = node_ids[dst]
            sorted_events = sorted(events)
            if len(sorted_events) > 1:
                label = "{" + ", ".join(sorted_events) + "}"
            else:
                label = sorted_events[0]
            dot.edge(src_id, dst_id, label=label)

        dot.render(filename, format=format, cleanup=True)
        return dot