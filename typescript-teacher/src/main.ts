import { createCounterController } from "./controller/counter-controller.js";
import { createCounterView } from "./view/counter-view.js";

/**
 * Composition root: la unica pieza que conoce las tres capas.
 *
 * @param root - Nodo donde vive la aplicacion.
 */
export function bootstrap(root: HTMLElement): void {
  const view = createCounterView(root);
  createCounterController(view).start();
}

const root = document.getElementById("app");
if (!root) {
  throw new Error("Falta el nodo #app en index.html");
}

bootstrap(root);
