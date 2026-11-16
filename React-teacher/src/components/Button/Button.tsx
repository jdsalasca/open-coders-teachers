import type { JSX, MouseEventHandler } from "react";

import styles from "./Button.module.scss";

interface ButtonProps {
  label: string;
  onClick: MouseEventHandler<HTMLButtonElement>;
}

/**
 * Boton reutilizable con estilos del modulo SCSS.
 *
 * @param props - Texto y accion del boton.
 * @returns Boton accesible con sus estilos.
 */
export function Button({ label, onClick }: ButtonProps): JSX.Element {
  return (
    <button className={styles.button} type="button" onClick={onClick}>
      {label}
    </button>
  );
}
