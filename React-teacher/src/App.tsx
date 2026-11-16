import type { JSX } from "react";

import styles from "./App.module.scss";
import { Button } from "./components/Button/Button";

/**
 * Pantalla de ejemplo del curso.
 *
 * @returns La vista principal de la aplicacion.
 */
function App(): JSX.Element {
  return (
    <main className={styles.app}>
      <h1 className={styles.title}>React teacher</h1>
      <p className={styles.lead}>Componentes, SCSS por modulo y reglas de lint.</p>
      <Button label="Comenzar" onClick={() => undefined} />
    </main>
  );
}

export default App;
