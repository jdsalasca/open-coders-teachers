/** Baseline portable: nada de ciclos entre modulos. */
module.exports = {
  forbidden: [
    {
      name: "sin-ciclos",
      severity: "error",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    exclude: { path: "(node_modules|dist|build|coverage)" },
  },
};
