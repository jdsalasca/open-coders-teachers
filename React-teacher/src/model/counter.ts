/** Estado del contador. Sin React: el modelo es puro. */
export interface Counter {
  readonly value: number;
}

/**
 * Estado inicial del contador.
 *
 * @returns Contador en cero.
 */
export function initialCounter(): Counter {
  return { value: 0 };
}

/**
 * Incrementa sin mutar. Satura en el entero seguro maximo.
 *
 * @param counter - Estado actual.
 * @returns Estado nuevo.
 */
export function inc(counter: Counter): Counter {
  return { value: Math.min(counter.value + 1, Number.MAX_SAFE_INTEGER) };
}
