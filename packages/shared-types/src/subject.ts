import { z } from "zod";

/**
 * Demographic and individual-difference covariates collected at session start.
 * Identifiers are deliberately limited to opaque hashed strings; PII never
 * leaves the participant's browser.
 */
export const SubjectSchema = z.object({
  id: z.string().min(1).max(64),
  ageBin: z
    .enum(["18-24", "25-34", "35-44", "45-54", "55-64", "65+", "prefer-not-to-say"])
    .optional(),
  handedness: z.enum(["right", "left", "ambidextrous", "prefer-not-to-say"]).optional(),
  origamiExperience: z
    .enum(["none", "occasional", "frequent", "expert", "prefer-not-to-say"])
    .optional(),
  language: z.string().optional(),
  consentVersion: z.string(),
  consentTimestamp: z.string().datetime(),
});

export type Subject = z.infer<typeof SubjectSchema>;
