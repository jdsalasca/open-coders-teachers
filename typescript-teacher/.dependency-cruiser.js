/** @type {import("dependency-cruiser").IConfig} */
export default {
  forbidden: [
    {
      name: "modelo-aislado",
      severity: "error",
      comment: "El modelo no conoce vista ni controlador.",
      from: { path: "^src/model/" },
      to: { pathNot: "^src/model" },
    },
    {
      name: "vista-sin-controlador",
      severity: "error",
      comment: "La vista no maneja el flujo: eso es del controlador.",
      from: { path: "^src/view/" },
      to: { path: "^src/controller/" },
    },
    {
      name: "sin-ciclos",
      severity: "error",
      comment: "Un ciclo entre capas rompe la direccion de dependencias.",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
    exclude: { path: "(^|/)node_modules/" },
  },
};
