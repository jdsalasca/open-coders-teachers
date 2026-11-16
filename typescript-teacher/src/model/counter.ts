/** Estado del contador. Nada de DOM ni de controladores aqui. */
export interface CounterState {
  readonly value: number;
}

/**
 * Estado inicial.
 *
 * @returns Contador en cero.
 */
export function initialCounter(): CounterState {
  return { value: 0 };
}

/**
 * Suma uno sin mutar el estado.
 *
 * @param state - Estado actual.
 * @returns Estado nuevo.
 */
export function increment(state: CounterState): CounterState {
  return { value: state.value + 1 };
}
