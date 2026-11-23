# Investigation: why is Sugar Shack's sales total so small?

Date: 2026-11-09. Read-only analysis. The CSV and `PRODUCT_FACTORY_MAP` were not modified. Evidence tags: **[ran]** = computed by executing code on the CSV.

**Correction.** Earlier notes said Sugar Shack makes "7 products". It has **5** in the mapping. The *Sugar division* has 7 products; two of them (Everlasting Gobstopper, Hair Toffee) are mapped to other factories.

## Question
Sugar Shack shows $221 in sales; Lot's O' Nuts shows $76,340.

## Evidence [ran]

### Per factory
| Factory | Products | Sales | Units | Order lines | Orders | Customers | Gross profit | GP % |
|---|---|---|---|---|---|---|---|---|
| Lot's O' Nuts | 3 | $76,340 | 21,412 | 5,692 | 4,760 | 3,599 | $52,771 | 69.1 |
| Wicked Choccy's | 2 | $55,353 | 15,863 | 4,152 | 3,445 | 2,929 | $36,054 | 65.1 |
| Secret Factory | 3 | $8,588 | 884 | 217 | 213 | 207 | $4,345 | 50.6 |
| The Other Factory | 2 | $1,282 | 388 | 100 | 98 | 98 | $152 | 11.9 |
| **Sugar Shack** | 5 | **$221** | **107** | **33** | **33** | **32** | $121 | 54.9 |

### Sugar Shack, per product
| Product | Sales | Units | Order lines | Customers | Gross profit | Price per unit |
|---|---|---|---|---|---|---|
| Fizzy Lifting Drinks | $78.75 | 21 | 6 | 6 | $47.25 | $3.75 |
| SweeTARTS | $61.50 | 41 | 10 | 10 | $28.70 | $1.50 |
| Laffy Taffy | $53.73 | 27 | 10 | 10 | $33.48 | $1.99 |
| Nerds | $15.00 | 10 | 4 | 4 | $7.00 | $1.50 |
| Fun Dip | $12.00 | 8 | 3 | 3 | $4.80 | $1.50 |

### What the numbers show
1. **Demand, not scale.** Sugar Shack has 33 order lines out of 10,194 (0.3%). Per-line behaviour is normal: 3.2 units per line (Lot's: 3.8, Wicked: 3.8), and prices of $1.50 to $3.75 per unit are in the same range as the factories' other candy products (Wonka Gum $1.25, Wonka Bars $3.25 to $3.75). There is no sign of a unit or currency error.
2. **The whole dataset is chocolate.** The Chocolate division is 96.6% of order lines (all of it at Lot's O' Nuts and Wicked Choccy's). "Other" is 3.0% and "Sugar" is 0.4% (40 lines across the three factories that make Sugar-division products).
3. **Not a truncation or late launch.** Sugar Shack has orders in all 8 quarters from 2024-03-14 to 2025-12-23 (1 to 10 lines per quarter), and its volume rises in Q4 like the rest of the data. Its orders reach 15 states and 32 customers.
4. **Mapping is internally consistent.** All 15 product names appear in the CSV and in the mapping (no unmapped product, no unused mapping entry); product names and product IDs correspond one-to-one; every order has exactly one factory.
5. **One genuine inconsistency.** *Fizzy Lifting Drinks* (6 lines, Sugar Shack) has Product ID `OTH-FIZ-56000` but Division `Sugar`. Every other product's ID prefix (`CHO`, `SUG`, `OTH`) agrees with its division. The mapping uses the product *name*, so this doesn't change any result, but it suggests either a division or an ID mislabel in the source.
6. **Factory/division pattern is mixed, not suspicious by itself.** Secret Factory makes two "Other" products and a "Sugar" one; The Other Factory makes one "Other" and one "Sugar". The CSV has no factory column, so this pattern can't be checked against any source in the data.

## Conclusion
**Primarily a characteristic of the dataset (extreme demand concentration in chocolate), not evidence of a mapping error.** Sugar Shack's products have very few orders in every quarter, and nothing in the per-order values looks broken.

What the data **cannot** tell us:
- Whether the product→factory assignment is correct. The mapping comes from the project brief (per the original code comment) and is not in the CSV, so it can be neither confirmed nor refuted here. If the brief is wrong, the factory-level figures would change, but the evidence above gives no reason to think so.
- Whether the Fizzy Lifting Drinks ID/division mismatch is a data-entry error (minor; 6 lines).

## Implications for the optimizer
Sugar Shack and The Other Factory have tiny observed volumes (107 and 388 units over two years versus 21,412 at Lot's). A preview with a plain nearest-factory calculation (not the optimizer) showed that, with **no capacity limits**, the hypothetical shifts Sugar Shack from 107 to about 1,132 units (10×) and Secret Factory from 884 to about 6,263 (7×). Capacity assumptions therefore matter a great deal, and an uncapacitated result must be presented as an unconstrained upper bound, not a plan.
