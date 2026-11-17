import type { JSX } from "react";

import { useCounter } from "../viewmodel/useCounter";
import styles from "./App.module.scss";
import { Button } from "./components/Button/Button";

/**
 * Vista principal: consume el ViewModel, nunca el modelo.
 *
 * @returns La pantalla del contador.
 */
function App(): JSX.Element {
  const { value, increment } = useCounter();

  return (
    <main className={styles.app}>
      <section aria-labelledby="app-title" className={styles.card}>
        <p className={styles.eyebrow}>MVVM | Vite | TypeScript</p>
        <h1 className={styles.title} id="app-title">
          React teacher
        </h1>
        <p className={styles.lead}>Un contador simple, con capas grandes.</p>

        <div className={styles.meter}>
          <span className={styles.label}>Valor actual</span>
          <output aria-live="polite" className={styles.count} data-testid="count">
            {value}
          </output>
        </div>

        <Button label="Incrementar" onClick={increment} />
        <p className={styles.footer}>view -&gt; viewmodel -&gt; model | sin logica en el JSX</p>
      </section>
    </main>
  );
}

export default App;
