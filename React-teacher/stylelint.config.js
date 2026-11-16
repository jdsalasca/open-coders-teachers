/** @type {import("stylelint").Config} */
export default {
  extends: ["stylelint-config-standard-scss"],
  ignoreFiles: ["dist/**", "node_modules/**"],
  rules: {
    // Estilos duplicados
    "declaration-block-no-duplicate-properties": [
      true,
      { ignore: ["consecutive-duplicates-with-different-syntaxes"] },
    ],
    "declaration-block-no-shorthand-property-overrides": true,
    "no-duplicate-selectors": true,
    "shorthand-property-no-redundant-values": true,

    // SCSS moderno: @use en vez de @import
    "at-rule-disallowed-list": [["import"], { message: "Usa @use en lugar de @import." }],

    // Orden y tamano
    "max-nesting-depth": 3,
    "selector-max-compound-selectors": 4,

    // Nombres: kebab-case para clases y custom properties
    "selector-class-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    "custom-property-pattern": "^[a-z][a-z0-9]*(-[a-z0-9]+)*$",

    // Los tokens se agrupan con lineas en blanco a proposito
    "scss/dollar-variable-empty-line-before": null,

    // Falso positivo con anidamiento SCSS
    "no-descending-specificity": null,
  },
};
