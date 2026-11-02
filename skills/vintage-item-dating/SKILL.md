---
name: vintage-item-dating
description: Date and price a second-hand garment from photos of its labels, by building a comparison board from live marketplace listings instead of trusting seller-stated decades. Use when asked how old a piece of clothing is, whether it is real vintage, what a thrifted or resale item is worth, or to read a care label, neck tag, or brand tag.
license: MIT
triggers:
  - vintage clothing
  - vintage item
  - date this garment
  - how old is this jacket
  - care label
  - clothing label
  - neck tag
  - brand tag
  - thrift find
  - resale value
  - is this real vintage
  - deadstock
---

# Vintage item dating

Dating a garment from photos is an evidence problem, not a lookup problem. There is no authoritative database for most brands, seller-stated decades are unreliable, and the rules published in "how to spot vintage" guides are often wrong. This skill produces **a comparison board the user can judge for themselves**, not a confident single date.

## Core principle

Rank evidence by how hard it is to fake or get wrong:

1. **Dated by the object itself** - a year embroidered on the garment, a team season, an event print. Strongest. These items date their own labels, so collect them.
2. **Physically printed on the label** - country, fibre composition, importer, care symbols, factory codes.
3. **Construction and materials** - stitch types, fabric, hardware.
4. **Style** - silhouette, colour-blocking, graphics. Weak, cyclical, easily revived.
5. **What a seller wrote in a listing title.** Not evidence. See below.

## Step 1 - request the right photos

Ask for these before analysing. Without the care label, any date is a guess:

- **Care label, both sides** - usually in a side seam or a pocket. The single highest-value document.
- **Composition label** - fibre content and language list.
- **Neck or brand tag** - straight on, filling the frame.
- **Hardware macro** - the back of a zipper pull, shot from 10-15 cm with side lighting. Maker stamps need real resolution; upscaling a 25-pixel stamp produces noise, not letters.
- **Whole garment, front and back, laid flat** - back graphics drive price more than anything else.
- **Inside seams, cuffs, hem.**

If a label is partly hidden under a collar or seam, ask for a shot with it folded back. Do not infer the hidden line.

## Step 2 - read the care label properly

Extract every field. Each one is independent evidence:

- **Country of manufacture.** Often reshapes both date and price. A brand moving production offshore is a dateable transition.
- **Fibre composition** and whether a lining is declared at all.
- **Importer or distributor block.** Frequently a template with the local importer swapped in per market. Treat the company name as a trading name, not a legal entity, unless corroborated.
- **Number of languages.** More languages and denser typesetting trend later.
- **Internal codes** - factory codes, article numbers. Usually no public decoder, but record them.
- **Care symbol order.** ISO 3758 order is washing, bleaching, drying, ironing, professional care. Artwork that places tumble-drying last often descends from the older four-symbol set with drying appended, which hints earlier. Soft signal only.
- **Absence of modern markers** - no website URL, no heritage slogan, no QR code.

## Step 3 - do not trust seller-stated decades

This is the most important operational finding, and it is measurable.

On resale platforms, an era in the title is a search keyword, not a date. To show this, pull a sample of listings for the brand and count how many titles claim more than one era at once:

```
For each listing title, flag which of 80s / 90s / Y2K-2000s appear.
Report: count per era, and count of titles claiming two or more.
```

In a 252-listing sample for one sportswear brand, 12 percent of dated titles named two incompatible eras in the same title - things like "VTG Y2K Track Jacket ... 90s Colorblock" and "NWT Vintage Y2K 90s", where NWT means new with tags. Averaging such claims is meaningless because there is nothing to average.

Use the same check before quoting any "sellers say it is from X" conclusion.

## Step 4 - build a label comparison board

This is the deliverable. For the brand in question:

1. Open 8-15 live listings across the brand's range, not only ones resembling the user's item.
2. Pull full-resolution photos from each listing and scan them for label shots. A contact sheet of each listing's photos lets you review many at once.
3. Crop each distinct label design.
4. Present them as a grid with the user's label pinned alongside, and for each: the design, the seller's claimed era, the source link, and what contradicts the claim.

Pin the user's own label so it stays visible while scrolling. The user compares visually and decides.

## Step 5 - watch for rules that are not rules

Published guides and plausible reasoning both generate false anchors. Verify any rule against the board before relying on it:

- **Wordmark case.** A corporate logo changing from upper to lower case does not mean woven labels follow. Lower-case lettering frequently appears on labels decades before a rebrand, and a single garment can carry one case on the neck tag and the other on its care label. Check before using case as a boundary.
- **Headquarters address.** Brand addresses often go unchanged for decades, so an address confirms authenticity, not date.
- **Label templates.** The same composition-label template can appear on items decades apart. Template identity proves a shared supply chain, not a shared year.
- **Legal entity names.** Care labels print trading names. A rename in corporate history is not reliably reflected on garments.
- **Guides quoting each other.** Multiple sites can carry word-for-word identical brand sections. Compare wording before counting them as independent corroboration.

When evidence pulls both ways, say so and give a range. Two contradicting signals is a finding, not a failure.

## Step 6 - price from comparable sales

- Separate **asking prices** from **completed sales** and label which you have. Most accessible data is asking prices, which run above real sale prices.
- Report a distribution, not a single number: median and interquartile range beat an average that one outlier distorts.
- Compare platforms. The same item can differ severalfold between a local app and an international marketplace, but shipping, fees and waiting time absorb much of the gap.
- Name the factors that actually move price for the category. For sportswear, team or club insignia typically outweighs age; a blank back caps the ceiling; pale fabrics are punished for light soiling.

## Output shape

Produce a comparison board, an evidence table split into what is established and what is contested, and a price range with its basis. State the date as a window with the reasoning on both edges. Explicitly list what could not be determined and the single next photo or source that would resolve the most.

If a threshold matters to the user - many markets treat 20-plus years as "vintage" - say plainly when the window straddles it rather than picking a side.

## References

- `references/marketplace-access.md` - which resale and label sources are reachable from an automated browser, which block it, and the working routes.
