import { useCallback, useState } from "react";

import { type Counter, inc } from "../model/counter";
import { parseCounter } from "../model/counter-schema";

/** Lo que la vista puede leer y disparar. */
export interface CounterViewModel {
  readonly value: number;
  increment(): void;
}

/**
 * ViewModel del contador: estado y acciones, sin JSX.
 *
 * @param seed - estado inicial sin validar.
 * @returns Valor actual y accion de incremento.
 */
export function useCounter(seed: unknown = { value: 0 }): CounterViewModel {
  const [counter, setCounter] = useState<Counter>(() => parseCounter(seed));
  const increment = useCallback((): void => {
    setCounter((current) => inc(current));
  }, []);

  return { value: counter.value, increment };
}
