/** Baseline portable: solo duplicacion de estilos (sin opiniones de formato). */
export default {
  customSyntax: "postcss-scss",
  rules: {
    "declaration-block-no-duplicate-properties": true,
    "declaration-block-no-shorthand-property-overrides": true,
    "no-duplicate-selectors": true,
    "shorthand-property-no-redundant-values": true,
  },
};
