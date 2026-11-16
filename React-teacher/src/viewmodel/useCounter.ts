import { useCallback, useState } from "react";

import { type Counter, inc, initialCounter } from "../model/counter";

/** Lo que la vista puede leer y disparar. */
export interface CounterViewModel {
  readonly value: number;
  increment(): void;
}

/**
 * ViewModel del contador: estado y acciones, sin JSX.
 *
 * @returns Valor actual y accion de incremento.
 */
export function useCounter(): CounterViewModel {
  const [counter, setCounter] = useState<Counter>(initialCounter);
  const increment = useCallback((): void => {
    setCounter((current) => inc(current));
  }, []);

  return { value: counter.value, increment };
}
