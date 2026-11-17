import { type CounterState, increment } from "../model/counter.js";
import { parseCounter } from "../model/counter-schema.js";
import type { CounterView } from "../view/counter-view.js";

/** Controlador: conecta el modelo con la vista. */
export interface CounterController {
  start(): void;
}

/**
 * Crea el controlador del contador.
 *
 * @param view - Vista ya montada.
 * @param initial - estado inicial sin validar.
 * @returns Controlador listo para arrancar.
 */
export function createCounterController(
  view: CounterView,
  initial: unknown = { value: 0 },
): CounterController {
  let state: CounterState = parseCounter(initial);
  let started = false;

  return {
    start(): void {
      if (started) {
        return;
      }
      started = true;
      view.onIncrement(() => {
        state = increment(state);
        view.render(state);
      });
      view.render(state);
    },
  };
}
