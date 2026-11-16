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
      <h1 className={styles.title}>React teacher</h1>
      <p className={styles.lead}>MVVM: la vista no conoce el modelo.</p>
      <p className={styles.count}>Valor: {value}</p>
      <Button label="Incrementar" onClick={increment} />
    </main>
  );
}

export default App;
