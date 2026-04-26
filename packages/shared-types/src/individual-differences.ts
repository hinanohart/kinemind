/**
 * Individual-differences questionnaire schemas for KineMind participant sessions.
 *
 * Three validated instruments are collected at session start:
 *   - AQ-10 (Allison et al., 2012): autistic-trait screening
 *   - MRT (Vandenberg & Kuse, 1978): mental rotation ability
 *   - VVIQ-2 (Marks, 1995): vividness of visual imagery
 *
 * All schemas enforce the published scoring ranges to catch data-entry errors.
 *
 * @module individual-differences
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// AQ-10 (Autism Spectrum Quotient – 10 item)
// ---------------------------------------------------------------------------

/**
 * AQ-10 response schema.
 *
 * Responses are scored 0–3 (0 = strongly disagree, 3 = strongly agree).
 * Items 1, 7, 8, 10 are reverse-scored before summation; this schema
 * records raw (pre-reversal) values; reversal is applied in the analysis
 * pipeline.
 *
 * Reference: Allison, C., Auyeung, B., & Baron-Cohen, S. (2012).
 *   Toward brief "Red Flags" for autism spectrum disorders.
 *   *Journal of the American Academy of Child and Adolescent Psychiatry*, 51(2), 202–212.
 */
export const AQ10ResponseSchema = z.object({
  schema: z.literal("AQ-10"),
  responses: z
    .array(z.number().int().min(0).max(3))
    .length(10)
    .describe("10 raw Likert responses (0 = strongly disagree, 3 = strongly agree)"),
  totalScore: z
    .number()
    .int()
    .min(0)
    .max(10)
    .describe("Sum score after reverse-coding items 1, 7, 8, 10"),
});

// ---------------------------------------------------------------------------
// MRT – Mental Rotation Test (Vandenberg & Kuse, 1978)
// ---------------------------------------------------------------------------

/**
 * Single MRT item response.
 *
 * Each MRT item presents a reference 3D figure and four response options; two
 * of the four are correct rotations.  The item is scored correct (1 pt) only
 * if both correct options are selected and no distractors are chosen.
 */
export const MRTItemResponseSchema = z.object({
  itemId: z.string().describe("Item identifier, e.g. '1a', '1b' following the published numbering"),
  responseTime: z.number().nonnegative().describe("Item response time in milliseconds"),
  selectedOptions: z
    .array(z.number().int().min(0).max(3))
    .describe("0-indexed indices of selected response options (0–3)"),
  correct: z.boolean().describe("True iff both correct options selected and no distractors chosen"),
});

/**
 * MRT full-test response schema.
 *
 * Reference: Vandenberg, S.G., & Kuse, A.R. (1978).
 *   Mental rotations, a group test of three-dimensional spatial visualization.
 *   *Perceptual and Motor Skills*, 47(2), 599–604.
 */
export const MRTResponseSchema = z.object({
  schema: z.literal("MRT-Vandenberg-Kuse"),
  itemResponses: z
    .array(MRTItemResponseSchema)
    .describe("Per-item responses; 24 items in the full test"),
  totalCorrect: z.number().int().min(0).max(24).describe("Number of correctly solved items (0–24)"),
});

// ---------------------------------------------------------------------------
// VVIQ-2 – Vividness of Visual Imagery Questionnaire (2nd edition)
// ---------------------------------------------------------------------------

/**
 * VVIQ-2 response schema.
 *
 * The VVIQ-2 contains 32 items rated 1 (no image at all) to 5 (perfectly
 * clear and as vivid as normal vision).  Higher scores indicate more vivid
 * imagery.
 *
 * Reference: Marks, D.F. (1995).
 *   New directions for mental imagery research.
 *   *Journal of Mental Imagery*, 19(3-4), 153–167.
 */
export const VVIQResponseSchema = z.object({
  schema: z.literal("VVIQ-2"),
  responses: z
    .array(z.number().int().min(1).max(5))
    .length(32)
    .describe("32 Likert responses (1 = no image, 5 = perfectly vivid)"),
  totalScore: z.number().int().min(32).max(160).describe("Sum of all 32 item ratings"),
});

// ---------------------------------------------------------------------------
// Exported types
// ---------------------------------------------------------------------------

export type AQ10Response = z.infer<typeof AQ10ResponseSchema>;
export type MRTItemResponse = z.infer<typeof MRTItemResponseSchema>;
export type MRTResponse = z.infer<typeof MRTResponseSchema>;
export type VVIQResponse = z.infer<typeof VVIQResponseSchema>;
