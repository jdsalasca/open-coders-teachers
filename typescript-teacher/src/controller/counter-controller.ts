import { type CounterState, increment, initialCounter } from "../model/counter.js";
import type { CounterView } from "../view/counter-view.js";

/** Controlador: conecta el modelo con la vista. */
export interface CounterController {
  start(): void;
}

/**
 * Crea el controlador del contador.
 *
 * @param view - Vista ya montada.
 * @returns Controlador listo para arrancar.
 */
export function createCounterController(view: CounterView): CounterController {
  let state: CounterState = initialCounter();

  return {
    start(): void {
      view.onIncrement(() => {
        state = increment(state);
        view.render(state);
      });
      view.render(state);
    },
  };
}
