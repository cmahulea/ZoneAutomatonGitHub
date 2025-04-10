from typing import Tuple, Optional
from TimedAutomaton import TimedFiniteAutomaton
from graphviz import Digraph


# Define la función de temporización Γ con intervalos en el formato (m, n, m_inclusive, n_inclusive)
def timing_function(transition: Tuple[str, str, str]) -> Tuple[float, float, bool, bool]:
    timing_map = {
        ("x1", "(u1)", "x2"): (2, float('inf'), True, False),
        ("x1", "(u2)", "x3"): (0, float('inf'), True, False),
        ("x3", "(u3)", "x4"): (5, float('inf'), True, False),
    }
    return timing_map.get(transition, (0, 0, True, True))

# Define la función de reinicio con intervalos en el formato (m, n, m_inclusive, n_inclusive)
def reset_function(transition: Tuple[str, str, str]) -> Optional[Tuple[float, float, bool, bool]]:
    reset_map = {
        ("x1", "(u1)", "x2"): (0, 0, True, True),
    }
    return reset_map.get(transition, None)

def define_example():
    # Definir los parámetros del autómata
    states = {"x1", "x2", "x3", "x4"}
    events = {"(u1)","(u2)","(u3)"}
    transitions = {
        ("x1", "(u1)", "x2"),
        ("x1", "(u2)", "x3"),
        ("x3", "(u3)", "x4"),
    }
    initial_states = {"x1"}

    # Inicializar el autómata temporizado
    tfa = TimedFiniteAutomaton(
        states=states,
        events=events,
        transitions=transitions,
        timing_function=timing_function,
        reset_function=reset_function,
        initial_states=initial_states
    )

    return tfa

