import type { CounterState } from "../model/counter.js";

/** Vista del contador: solo pinta y avisa clics. */
export interface CounterView {
  onIncrement(handler: () => void): void;
  render(state: CounterState): void;
}

/**
 * Monta la vista del contador en un nodo.
 *
 * @param root - Nodo donde se dibuja la vista.
 * @returns Vista con render y suscripcion a clics.
 */
export function createCounterView(root: HTMLElement): CounterView {
  root.innerHTML = `
    <button type="button" data-action="increment">+1</button>
    <output data-role="value">0</output>
  `;
  const button = root.querySelector<HTMLButtonElement>("[data-action=increment]");
  const output = root.querySelector<HTMLOutputElement>("[data-role=value]");
  if (!button || !output) {
    throw new Error("La vista no se monto completa");
  }

  return {
    onIncrement(handler: () => void): void {
      button.addEventListener("click", handler);
    },
    render(state: CounterState): void {
      output.value = String(state.value);
    },
  };
}
