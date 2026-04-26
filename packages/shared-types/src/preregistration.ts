/**
 * Pre-registration schema for KineMind experiments.
 *
 * Validates pre-registration documents before OSF submission and during
 * data collection pipeline ingestion.  The schema is intentionally strict:
 * missing hypotheses or analyses are a hard validation error.
 *
 * @module preregistration
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Sub-schemas
// ---------------------------------------------------------------------------

export const HypothesisSchema = z.object({
  id: z.string().min(1),
  statement: z.string().min(1),
  directional: z.boolean(),
  predictedDirection: z
    .enum(["positive", "negative", "non-zero"])
    .optional()
    .describe("Required when directional === true"),
  exclusionRule: z
    .string()
    .optional()
    .describe("Session-level exclusion condition specific to this hypothesis"),
});

export const AnalysisSchema = z.object({
  type: z
    .enum(["primary", "secondary", "exploratory"])
    .describe("Analysis classification: primary analyses drive sample-size"),
  description: z.string().min(1),
  model: z.string().min(1).describe("Verbatim model formula (R / Python / prose)"),
  alphaCorrection: z
    .enum(["none", "bonferroni-holm", "benjamini-hochberg"])
    .default("benjamini-hochberg")
    .describe("Multiple comparison correction applied across primary analyses"),
});

export const ExclusionRuleSchema = z.object({
  rule: z.string().min(1).describe("Human-readable exclusion condition"),
  threshold: z.number().optional().describe("Numeric threshold if applicable"),
  justification: z.string().min(1).describe("Scientific or ethical justification"),
});

export const StoppingRuleSchema = z
  .object({
    type: z
      .enum(["fixed-N", "sequential"])
      .describe("fixed-N: enrol exactly N; sequential: use alpha-spending function"),
    N: z.number().int().positive().optional().describe("Target sample size for fixed-N designs"),
    alphaSpending: z
      .string()
      .optional()
      .describe("Alpha-spending function name for sequential designs"),
  })
  .refine(
    (data) =>
      data.type === "sequential" ? data.alphaSpending !== undefined : data.N !== undefined,
    {
      message: "fixed-N designs must specify N; sequential designs must specify alphaSpending",
    },
  );

// ---------------------------------------------------------------------------
// Top-level pre-registration schema
// ---------------------------------------------------------------------------

export const PreregistrationSchema = z.object({
  studyId: z.string().min(1).describe("Globally unique study identifier, e.g. kmm-h1-pilot-2026q2"),
  registrationDate: z
    .string()
    .datetime()
    .optional()
    .describe("ISO-8601 datetime when the registration was locked on OSF"),
  registrationPlatform: z
    .enum(["osf", "aspredicted", "internal"])
    .optional()
    .describe("Repository used for pre-registration"),
  hypotheses: z
    .array(HypothesisSchema)
    .min(1)
    .describe("At least one pre-registered hypothesis required"),
  analyses: z
    .array(AnalysisSchema)
    .min(1)
    .describe("At least one pre-registered analysis required"),
  exclusionCriteria: z
    .array(ExclusionRuleSchema)
    .describe("Session-level exclusion criteria applied before analysis"),
  stoppingRule: StoppingRuleSchema,
  ethics: z.object({
    irbApproval: z.string().optional().describe("IRB / ethics committee approval reference number"),
    consentVersion: z.string().min(1).describe("Consent form version string, e.g. v0.2-2026-04-27"),
    dataRetentionDays: z
      .number()
      .int()
      .positive()
      .default(3650)
      .describe("GDPR-required retention period in days (default 10 years)"),
  }),
  predictedEffectSize: z
    .number()
    .optional()
    .describe("Predicted standardised effect size used for power calculation (e.g. beta_logN)"),
  power: z
    .number()
    .min(0)
    .max(1)
    .optional()
    .describe("Target statistical power (0–1); typically 0.80"),
  estimatedSampleSize: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("N required to achieve target power at predicted effect size"),
});

// ---------------------------------------------------------------------------
// Exported types
// ---------------------------------------------------------------------------

export type Hypothesis = z.infer<typeof HypothesisSchema>;
export type Analysis = z.infer<typeof AnalysisSchema>;
export type ExclusionRule = z.infer<typeof ExclusionRuleSchema>;
export type StoppingRule = z.infer<typeof StoppingRuleSchema>;
export type Preregistration = z.infer<typeof PreregistrationSchema>;
