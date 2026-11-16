import { describe, expect, it } from "vitest";

import type { CounterState } from "../model/counter.js";
import type { CounterView } from "../view/counter-view.js";
import { createCounterController } from "./counter-controller.js";

/**
 * Vista falsa: registra lo que el controlador le pide.
 *
 * @returns Vista y listas de eventos/renderizados.
 */
function fakeView(): {
  view: CounterView;
  handlers: Array<() => void>;
  rendered: CounterState[];
} {
  const handlers: Array<() => void> = [];
  const rendered: CounterState[] = [];
  return {
    handlers,
    rendered,
    view: {
      onIncrement(handler: () => void): void {
        handlers.push(handler);
      },
      render(state: CounterState): void {
        rendered.push(state);
      },
    },
  };
}

describe("counter-controller", () => {
  it("pinta el estado inicial al arrancar", () => {
    const { view, rendered } = fakeView();

    createCounterController(view).start();

    expect(rendered).toEqual([{ value: 0 }]);
  });

  it("incrementa cuando la vista avisa un clic", () => {
    const { view, handlers, rendered } = fakeView();
    const controller = createCounterController(view);
    controller.start();

    handlers[0]?.();

    expect(rendered.at(-1)).toEqual({ value: 1 });
  });
});
