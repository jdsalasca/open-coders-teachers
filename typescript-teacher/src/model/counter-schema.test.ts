import { describe, expect, it } from "vitest";

import { parseCounter } from "./counter-schema.js";

describe("parseCounter", () => {
  it("acepta un payload valido", () => {
    expect(parseCounter({ value: 2 })).toEqual({ value: 2 });
  });

  it("rechaza negativos", () => {
    expect(() => parseCounter({ value: -1 })).toThrow();
  });

  it("rechaza tipos equivocados", () => {
    expect(() => parseCounter({ value: "2" })).toThrow();
  });

  it("rechaza enteros inseguros", () => {
    expect(() => parseCounter({ value: Number.MAX_SAFE_INTEGER + 1 })).toThrow();
  });
});
