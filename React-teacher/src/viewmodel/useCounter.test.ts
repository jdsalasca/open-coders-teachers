import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useCounter } from "./useCounter";

describe("useCounter", () => {
  it("arranca en cero", () => {
    const { result } = renderHook(() => useCounter());

    expect(result.current.value).toBe(0);
  });

  it("incrementa el valor", () => {
    const { result } = renderHook(() => useCounter());

    act(() => {
      result.current.increment();
    });

    expect(result.current.value).toBe(1);
  });
});
