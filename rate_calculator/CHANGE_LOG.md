# Facility Rate Calculator - Approved Logic Log (STRICT)

## 1. Sheet: Equipment Depreciation (CRITICAL)
- **Non-3E Subtotal Row (Original D25):** 
  - MUST sum vertically from the first Non-3E row to the row above the subtotal.
  - MUST apply to Column D, E, F AND all instrument columns.
  - Formula: `=SUM(Col[Start]:Col[End])`.
- **Internal Total Row (Original D33):**
  - MUST sum the three subtotal rows: `=[3E Subtotal] + [Non-3E Subtotal] + [Projection Subtotal]`.

## 2. Sheet: Expenditures
- **Non-Personnel Boundary:** STRICT Rows 10 to 27. Do not touch Row 28 (Total) or Row 30 (Projections).
- **Personnel Boundary:** Starts Row 38.

## 3. Sheet: Salaries and Wages
- **Salary Column:** Column 5 (E).
- **Horizontal Split:** Formula `=$E[row] * [ColLetter]$5`.

## 4. General Logic
- **Robert Klie:** Always excluded.
- **Account Exclusions:** 142100, 153809, 186100, 211300, 211400, 211960.
- **Usage Perc Row:** Row 5 in summary tabs.
