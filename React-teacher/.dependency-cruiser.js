/** @type {import("dependency-cruiser").IConfig} */
export default {
  forbidden: [
    {
      name: "modelo-aislado",
      severity: "error",
      comment: "El modelo no conoce React, ni viewmodel, ni vista.",
      from: { path: "^src/model/" },
      to: { pathNot: "^src/model" },
    },
    {
      name: "viewmodel-sin-vista",
      severity: "error",
      comment: "El ViewModel no puede depender de la vista (MVVM).",
      from: { path: "^src/viewmodel/" },
      to: { path: "^src/view/" },
    },
    {
      name: "vista-sin-modelo",
      severity: "error",
      comment: "La vista consume el ViewModel, no el modelo.",
      from: { path: "^src/view/" },
      to: { path: "^src/model/" },
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
