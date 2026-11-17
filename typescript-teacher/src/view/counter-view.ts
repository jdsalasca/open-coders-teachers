import "./counter-view.scss";

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
    <main class="app">
      <section class="card" aria-labelledby="counter-title">
        <p class="eyebrow">MVC | Vite | TypeScript</p>
        <h1 class="title" id="counter-title">TypeScript teacher</h1>
        <p class="lead">Un contador simple, con la vista separada del controlador.</p>
        <div class="meter">
          <span class="label">Valor actual</span>
          <output class="value" data-role="value" aria-live="polite">0</output>
        </div>
        <button class="button" type="button" data-action="increment">
          <span class="plus" aria-hidden="true">+</span>
          Incrementar
        </button>
        <p class="footer">view -&gt; controller -&gt; model | sin logica en el DOM</p>
      </section>
    </main>
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
