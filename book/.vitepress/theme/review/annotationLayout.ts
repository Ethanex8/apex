/**
 * Purpose: Compute document-relative CSS pixel coordinates for PR review margin markers
 *          (diff gutter bars, per-block `+` comment buttons, and thread marker chips).
 * Usage:   Called by `PrReviewOverlay.vue` (`collectBlockAnnotations`, `collectThreadMarkers`)
 *          during layout measurement and verified in `review.test.mts`.
 * Invariants:
 *   - Margin gutter bars and desktop `+` buttons clamp horizontally against `.vp-doc`'s outer
 *     left edge (`Math.min(blockRect.left, docLeft)`) so indented `<li>`/`<blockquote>` outside
 *     list markers (`1.`, bullets) never flow across the vertical gutter bar on mobile or desktop.
 *   - Viewport geometry inputs (`blockRect`, `docLeft`, `docWidth`) are converted consistently into
 *     document CSS pixel space via `scrollX`/`scrollY`, and every returned coordinate is `>= 0`.
 */

const GUTTER_OUTER_OFFSET_PX = 10
const MIN_GUTTER_LEFT_PX = 3
const MIN_BLOCK_HEIGHT_PX = 12
const DESKTOP_ADD_BTN_OFFSET_PX = 34
const MIN_DESKTOP_BTN_LEFT_PX = 6
const COMPACT_ADD_BTN_RIGHT_INSET_PX = 22
const COMPACT_ADD_BTN_MAX_RIGHT_INSET_PX = 26
const COMPACT_ADD_BTN_MIN_LEFT_PX = 8
const COMPACT_ADD_BTN_TOP_SHIFT_PX = -10
const MIN_BTN_TOP_PX = 4
const DESKTOP_ADD_BTN_TOP_SHIFT_PX = 3

const CHIP_RIGHT_GAP_PX = 8
const CHIP_CLEARANCE_RIGHT_PX = 10
const CHIP_ESTIMATED_WIDTH_PX = 92
const CHIP_MIN_LEFT_PX = 8
const CHIP_RIGHT_CLAMP_INSET_PX = 96
const CHIP_OVERLAP_TOP_SHIFT_PX = -12
const CHIP_MARGIN_TOP_SHIFT_PX = 2

/** Minimal DOMRect subset required to place block annotations and thread marker chips. */
export interface BlockRectLike {
  /** Top edge relative to viewport in CSS pixels. */
  top: number
  /** Left edge relative to viewport in CSS pixels. */
  left: number
  /** Right edge relative to viewport in CSS pixels. */
  right: number
  /** Rendered element height in CSS pixels. */
  height: number
}

/** Document-relative CSS pixel positions for an annotated block's diff bar and `+` trigger. */
export interface BlockAnnotationLayout {
  /** Top coordinate of the vertical diff gutter bar in document CSS pixels (`>= 0`). */
  gutterTop: number
  /** Left coordinate of the vertical diff gutter bar in document CSS pixels (`>= 0`). */
  gutterLeft: number
  /** Clamped vertical height of the diff gutter bar in CSS pixels. */
  gutterHeight: number
  /** Top coordinate of the block's `+` add-comment button in document CSS pixels (`>= 0`). */
  buttonTop: number
  /** Left coordinate of the block's `+` add-comment button in document CSS pixels (`>= 0`). */
  buttonLeft: number
}

/** Document-relative CSS pixel coordinates for a grouped thread marker pill. */
export interface ThreadChipPosition {
  /** Top coordinate of the floating thread chip in document CSS pixels (`>= 0`). */
  top: number
  /** Left coordinate of the floating thread chip in document CSS pixels (`>= 0`). */
  left: number
}

/** Clamp `value` so `min` always wins cleanly over `max` even on collapsed viewports. */
function clampFloor(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

/**
 * Compute document-space coordinates for one block's PR diff gutter bar and `+` button.
 *
 * @param blockRect Annotated block bounding box in viewport CSS pixels.
 * @param docLeft Outer `.vp-doc` left edge in viewport CSS pixels.
 * @param scrollX Horizontal document scroll offset (`window.scrollX`) in CSS pixels.
 * @param scrollY Vertical document scroll offset (`window.scrollY`) in CSS pixels.
 * @param docWidth Visible viewport width (`documentElement.clientWidth`) in CSS pixels.
 * @param compactMode Whether narrow-screen inline-top `+` button placement is active.
 */
export function computeBlockAnnotationLayout(
  blockRect: BlockRectLike,
  docLeft: number,
  scrollX: number,
  scrollY: number,
  docWidth: number,
  compactMode: boolean,
): BlockAnnotationLayout {
  // Clamp indented list items and blockquotes to `.vp-doc`'s outer edge so list numbers stay clear.
  const anchorLeftDoc = Math.min(blockRect.left, docLeft) + scrollX
  const docTop = blockRect.top + scrollY
  const docRight = blockRect.right + scrollX
  const viewportRightDoc = docWidth + scrollX

  const gutterLeft = Math.max(MIN_GUTTER_LEFT_PX, anchorLeftDoc - GUTTER_OUTER_OFFSET_PX)
  const buttonLeft = compactMode
    ? clampFloor(
        docRight - COMPACT_ADD_BTN_RIGHT_INSET_PX,
        COMPACT_ADD_BTN_MIN_LEFT_PX,
        viewportRightDoc - COMPACT_ADD_BTN_MAX_RIGHT_INSET_PX,
      )
    : Math.max(MIN_DESKTOP_BTN_LEFT_PX, anchorLeftDoc - DESKTOP_ADD_BTN_OFFSET_PX)

  const buttonTop = compactMode
    ? Math.max(MIN_BTN_TOP_PX, docTop + COMPACT_ADD_BTN_TOP_SHIFT_PX)
    : Math.max(0, docTop + DESKTOP_ADD_BTN_TOP_SHIFT_PX)

  return {
    gutterTop: Math.max(0, docTop),
    gutterLeft,
    gutterHeight: Math.max(MIN_BLOCK_HEIGHT_PX, blockRect.height),
    buttonTop,
    buttonLeft,
  }
}

/**
 * Compute document-space coordinates for a block's thread marker chip, pulling it inward when narrow.
 *
 * @param blockRect Anchored block bounding box in viewport CSS pixels.
 * @param scrollX Horizontal document scroll offset (`window.scrollX`) in CSS pixels.
 * @param scrollY Vertical document scroll offset (`window.scrollY`) in CSS pixels.
 * @param docWidth Visible viewport width (`documentElement.clientWidth`) in CSS pixels.
 */
export function computeThreadChipPosition(
  blockRect: BlockRectLike,
  scrollX: number,
  scrollY: number,
  docWidth: number,
): ThreadChipPosition {
  const docTop = blockRect.top + scrollY
  const docRight = blockRect.right + scrollX
  const viewportRightDoc = docWidth + scrollX

  const fitsRightMargin =
    docRight + CHIP_CLEARANCE_RIGHT_PX + CHIP_ESTIMATED_WIDTH_PX <= viewportRightDoc
  const left = fitsRightMargin
    ? Math.max(CHIP_MIN_LEFT_PX, docRight + CHIP_RIGHT_GAP_PX)
    : clampFloor(
        docRight - CHIP_ESTIMATED_WIDTH_PX,
        CHIP_MIN_LEFT_PX,
        viewportRightDoc - CHIP_RIGHT_CLAMP_INSET_PX,
      )
  // Lift inward-pulled chips above the block header line while keeping coordinates non-negative.
  const topOffset =
    left < docRight ? CHIP_OVERLAP_TOP_SHIFT_PX : CHIP_MARGIN_TOP_SHIFT_PX

  return {
    top: Math.max(0, docTop + topOffset),
    left,
  }
}
