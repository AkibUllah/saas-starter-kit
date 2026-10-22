"use client";

import { useCallback, useState, type FormEvent } from "react";
import type { ZodType } from "zod";
import { ApiError } from "./api";
import { fieldErrors } from "./validation";

/** Minimal form state: zod validation on submit, server field errors mapped back, one busy flag. */
export function useForm<T extends Record<string, unknown>>(schema: ZodType<T, any, any>, initial: T) {
  const [values, setValues] = useState<T>(initial);
  type Errors = Partial<Record<keyof T | "_", string>>;
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);

  const setField = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => (e[key] ? { ...e, [key]: undefined } : e));
  }, []);

  const handleSubmit = (onValid: (data: T) => Promise<void>) => async (event: FormEvent) => {
    event.preventDefault();
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      setErrors(fieldErrors(parsed.error) as Errors);
      return;
    }
    setBusy(true);
    setErrors({});
    try {
      await onValid(parsed.data);
    } catch (err) {
      if (err instanceof ApiError) {
        const fields = err.fieldErrors();
        setErrors((Object.keys(fields).length ? fields : { _: err.message }) as Errors);
      } else {
        setErrors({ _: err instanceof Error ? err.message : "Something went wrong" } as Errors);
      }
    } finally {
      setBusy(false);
    }
  };

  return { values, setField, errors, setErrors, busy, handleSubmit, reset: () => setValues(initial) };
}
