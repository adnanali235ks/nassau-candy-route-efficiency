# ---- 10 Route analytics ----
$s = NewSlide "Route analytics" (Note 10)
Txt $s 40 92 440 20 "Haversine distance" 15 $K.blue $true | Out-Null
$f = Txt $s 40 118 450 62 "a = sin{sq}({D}{phi}/2) + cos {phi}_{1} {.} cos {phi}_{2} {.} sin{sq}({D}{lam}/2)`rd = 2R {.} atan2({sqrt}a, {sqrt}(1 {minus} a)),   R = 3,958.8 mi" 16 $K.ink $false 1 1 $MATH
$f.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 6
Txt $s 40 186 450 60 "Straight-line distance from the factory to the state or province centroid, not road distance. Example: Wicked Choccy{'}s {->} Texas = 971.5 mi." 13 $K.ink | Out-Null
Txt $s 40 258 440 20 "Route Efficiency Score (0{-}100)" 15 $K.blue $true | Out-Null
$f2 = Txt $s 40 284 450 62 "Score = 0.70 {x} Distance Score + 0.30 {x} Ship-Mode Score`rDistance Score = 100 {x} (1 {minus} d / d_{ref})" 16 $K.ink $false 1 1 $MATH
$f2.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 6
Txt $s 40 352 450 54 "d is the route{'}s average distance and d_ref the longest route in the dataset. Ship-mode suitability (assumptions, editable): Same Day 1.00, First Class 0.85, Second Class 0.60, Standard Class 0.40." 13 $K.ink | Out-Null
Rect $s 40 414 3 72 $K.teal | Out-Null
Txt $s 54 414 436 72 "Worked example: d = 500 mi, d_ref = 2,000 mi gives Distance Score 75. A mix of 50% Standard and 50% First Class gives Ship-Mode Score 62.5. Score = 0.7 {x} 75 + 0.3 {x} 62.5 = 71.25." 13 $K.ink $false 1 3 | Out-Null
Txt $s 520 92 400 36 "Route Efficiency Score of region routes (calculated; weights are assumptions)" 14 $K.blue $true | Out-Null
$rows = @(@("Wicked Choccy{'}s {->} Gulf",74.6),@("Secret Factory {->} Interior",73.7),@("The Other Factory {->} Gulf",73.6),@("The Other Factory {->} Interior",69.7),@("Lot{'}s O{'} Nuts {->} Pacific",66.4),@("Sugar Shack {->} Gulf",36.2),@("The Other Factory {->} Pacific",34.5),@("Lot{'}s O{'} Nuts {->} Gulf",31.7),@("Lot{'}s O{'} Nuts {->} Atlantic",20.4),@("Wicked Choccy{'}s {->} Pacific",16.1))
for($i=0;$i -lt 10;$i++){
  $y = 140 + $i*28 + $(if($i -ge 5){14}else{0})
  Txt $s 520 $y 190 22 $rows[$i][0] 12 $K.ink $false 1 3 | Out-Null
  $bw = [int][math]::Round(1.55*$rows[$i][1])
  Rect $s 715 ($y+3) $bw 16 $K.blue | Out-Null
  Txt $s (715+$bw+6) $y 40 22 ("{0:N1}" -f $rows[$i][1]) 12 $K.ink $false 1 3 | Out-Null
}
Txt $s 520 440 400 44 "Best five and worst five of the 20 factory-to-region routes. No delivery-time claim is made because the shipping dates are unusable." 12 $K.grey | Out-Null

# ---- 11 Optimization ----
$s = NewSlide "Optimization model" (Note 11)
Tag $s "Hypothetical model: capacities and eligibility are assumptions" 440 480
$f = Txt $s 40 96 560 190 "minimise    {S}_{c{in}C} {S}_{f{in}F}  d_{cf} x_{cf}`rsubject to`r{S}_{f} x_{cf} = D_{c}        for every demand cell c`r{S}_{c} x_{cf} {<=} K_{f}        for every capacity-limited factory f`rx_{cf} = 0 if E_{cf} = 0,    x_{cf} {>=} 0" 18 $K.ink $false 1 1 $MATH
$f.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 9
$f.TextFrame.TextRange.Paragraphs(2).Font.Name = $FONT; $f.TextFrame.TextRange.Paragraphs(2).Font.Size = [single]13; $f.TextFrame.TextRange.Paragraphs(2).Font.Color.RGB = $K.grey
$v = @(@("c {in} C","demand cell (state or province {x} product); 383 cells"),@("f {in} F","factory; 5 factories"),@("D_{c}","units demanded in cell c"),@("d_{cf}","haversine distance (mi) from factory f to cell c"),@("E_{cf}","1 if factory f may supply the product of c, else 0"),@("K_{f}","capacity of factory f (hypothetical, optional)"),@("x_{cf}","units of cell c shipped from factory f"))
Tbl $s 620 96 $v @(60,240) 34 12 $null @(1) @() $false | Out-Null
Txt $s 40 296 560 100 "The objective is total unit-miles (distance {x} units). The model is solved with Google OR-Tools (pywraplp) using GLOP, which applies the simplex method. Each variable appears in exactly one demand constraint and at most one capacity constraint, so the matrix is totally unimodular and whole-number demands and capacities give whole-number plans. Before solving, the code checks and explains infeasibility." 13.5 $K.ink | Out-Null
Rect $s 40 410 3 76 $K.amber | Out-Null
Txt $s 54 410 866 76 "Worked example (an automated test): two factories A and B, cells X, Y, Z with 10, 20 and 30 units. All from A: 16,500 unit-miles. No limits: 9,500 ({minus}42.4%). B capped at 40 units: 10,500 ({minus}36.4%). Capacities of 20 and 30 for 60 units: infeasible, short by 10 units." 13.5 $K.ink $false 1 3 | Out-Null

# ---- 12 Scenario simulation ----
$s = NewSlide "Scenario simulation" (Note 12)
Tag $s "All scenario results are hypothetical"
Txt $s 40 92 420 20 "Total distance (millions of unit-miles)" 14 $K.blue $true | Out-Null
$bars = @(@("Existing allocation",48.10,$true,"dataset, calculated"),@("Current volume",27.39,$false,"{minus}43.0%"),@("+20% headroom",24.60,$false,"{minus}48.9%"),@("No limits (upper bound)",19.84,$false,"{minus}58.8%"))
for($i=0;$i -lt 4;$i++){
  $y = 128 + $i*62
  Txt $s 40 $y 300 18 $bars[$i][0] 13 $K.ink | Out-Null
  $bw = [int][math]::Round(230*$bars[$i][1]/48.1)
  if($bars[$i][2]){ $b = Rect $s 40 ($y+22) $bw 22 $K.navy } else { $b = Rect $s 40 ($y+22) $bw 22 $K.amberFill $K.amber 1.25; $b.Line.DashStyle = 4 }
  Txt $s (40+$bw+8) ($y+22) 150 22 (("{0:N2}" -f $bars[$i][1]) + "   " + $bars[$i][3]) 12.5 $K.ink $false 1 3 | Out-Null
}
$lg1 = Rect $s 40 384 14 10 $K.navy; Txt $s 60 380 160 18 "Calculated from the dataset" 12 $K.ink | Out-Null
$lg2 = Rect $s 240 384 14 10 $K.amberFill $K.amber 1.25; $lg2.Line.DashStyle = 4; Txt $s 260 380 180 18 "Hypothetical simulation" 12 $K.amber | Out-Null
Txt $s 40 410 420 80 "A scenario sets the eligibility rule, an optional capacity headroom and an optional cost rate. Two to four scenarios are compared with the existing allocation. An infeasible scenario returns a reason, never a zero." 13 $K.ink | Out-Null
$d = @(@("Scenario","Unit-miles","Reduction","Cells changed"),@("Existing allocation","48,099,961","{--}","{--}"),@("No capacity limits (upper bound)","19,836,723","58.8%","304"),@("Capacity = current volume","27,394,134","43.0%","248"),@("Current volume + 20% headroom","24,602,248","48.9%","255"),@("Control: current mapping only","48,099,961","0.0%","0"))
Tbl $s 490 96 $d @(180,100,70,80) 40 12.5 @(1,3,3,3) | Out-Null
Txt $s 490 350 430 140 "Existing is calculated from the dataset; every other row is a simulation under assumed eligibility and capacities. The control run, which allows only the current mapping, reproduces 48,099,961 unit-miles with no cells changed, so the model and the comparison are consistent." 13 $K.amber | Out-Null

# ---- 13 Anomalies and recommendations ----
$s = NewSlide "Anomalies and recommendations" (Note 13)
$d = @(@("Check","Flagged"),@("Route distance outliers (IQR)","1 of 196 routes"),@("Repeated order lines","3,018 (396 identical)"),@("Missing geography","0"),@("Unusual sales or profit patterns","0"),@("Product ID and Division mismatch","6 lines"),@("Very-low-volume factories or products","9 (2 factories, 7 products)"))
Tbl $s 40 92 $d @(250,200) 30 13 | Out-Null
Txt $s 520 92 400 20 "IQR method" 15 $K.blue $true | Out-Null
Txt $s 520 118 400 130 "Q1 and Q3 are the 25th and 75th percentiles and IQR = Q3 {minus} Q1. A value outside Q1 {minus} 1.5 {x} IQR to Q3 + 1.5 {x} IQR is flagged. The one outlier is Lot{'}s O{'} Nuts {->} Newfoundland and Labrador: 2,979 mi against an upper fence of 2,720 mi, with only 5 orders. Unusual means worth a look, not wrong; no record is deleted or changed." 13 $K.ink | Out-Null
Txt $s 40 318 880 40 "17 rule-based recommendations (9 High, 4 Medium, 4 Low). Each states Why, Rule, Supporting Values, Basis and Priority. No machine learning is used." 14 $K.ink | Out-Null
$d = @(@("Category","Number","Priority","Basis"),@("Alternative factory allocation","5","High","Hypothetical"),@("Factory capacity","3","High","Hypothetical"),@("Long-distance route","3","2 Medium, 1 Low","Calculated"),@("Data quality","6","1 High, 2 Medium, 3 Low","Dataset or calculated"))
Tbl $s 40 362 $d @(300,100,260,220) 27 13 | Out-Null

# ---- 14-17 Demonstration ----
function Demo($title,$note,$a,$ta,$da,$b,$tb2,$db){
  $s = NewSlide $title $note
  $p1 = Pic $s $a 40 96 430 -1 ("Screenshot of the " + $ta)
  Frame $p1; $p2 = Pic $s $b 490 96 430 -1 ("Screenshot of the " + $tb2)
  Frame $p2
  $y = $p1.Top + $p1.Height + 10
  Txt $s 40 $y 430 20 $ta 14 $K.head $true | Out-Null
  Txt $s 40 ($y+22) 430 50 $da 13 $K.ink | Out-Null
  Txt $s 490 $y 430 20 $tb2 14 $K.head $true | Out-Null
  Txt $s 490 ($y+22) 430 50 $db 13 $K.ink | Out-Null
  return $s
}
$s = Demo "Application demonstration (1 of 4)" (Note 14) 'demo_exec.png' "Executive Overview" "Six KPIs, ship-mode distribution and sales by factory. A banner states that the shipping dates are unusable." 'demo_geo.png' "Geographic Analysis" "Factories and state or province centroids on a map; distance comparison and shipment density in other tabs."
Txt $s 40 480 880 20 "Real screenshots of the running application, unedited. One filter sidebar is shared by all eight pages." 12 $K.grey | Out-Null
$s = Demo "Application demonstration (2 of 4)" "Route Performance ranks routes by the Route Efficiency Score and shows the distance and ship-mode components next to each score. The Optimization Center runs the linear-programming model; note the banner stating that it is a hypothetical simulation. The KPI row shows 48,099,961 unit-miles for the existing allocation against 19,836,723 with no capacity limits." 'demo_route.png' "Route Performance" "Top 10 and bottom 10 routes by Route Efficiency Score (calculated)." 'demo_optim.png' "Optimization Center" "Hypothetical simulation with no capacity limits, so the result is an upper bound."
$s = Demo "Application demonstration (3 of 4)" "The Scenario Simulator compares up to four scenarios in one table and chart; here are two. Smart Recommendations shows recommendation R01 expanded, so you can see the reason, the rule, the supporting values and the basis label. Every recommendation can be audited this way." 'demo_scen.png' "Scenario Simulator" "Comparison of the existing allocation with two hypothetical scenarios." 'demo_recs.png' "Smart Recommendations" "Each recommendation shows its Why, Rule, Supporting Values and Basis (Dataset, Calculated or Hypothetical)."
$s = Demo "Application demonstration (4 of 4)" "Anomaly Detection lists what each check flagged, with the reason in plain language. The Reports page generates the PDF, the nine-sheet Excel workbook and the CSV files from one shared data dictionary. In the browser check all 23 download buttons produced valid files." 'demo_anom.png' "Anomaly Detection" "Summary of the five checks. Flags are prompts for review; nothing is deleted." 'demo_reports.png' "Reports" "Generates the PDF, Excel and CSV outputs for the selected scenario."

# ---- 18 Results ----
$s = NewSlide "Results" (Note 15)
Tag $s "Distance reductions are hypothetical"
Txt $s 40 92 440 20 "Total distance (millions of unit-miles)" 14 $K.blue $true | Out-Null
$base = 360; $maxH = 220
$bars = @(@("Existing`r(calculated)",48.10,$true,""),@("Current`rvolume",27.39,$false,"{minus}43.0%"),@("+20%`rheadroom",24.60,$false,"{minus}48.9%"),@("No limits`r(upper bound)",19.84,$false,"{minus}58.8%"))
for($i=0;$i -lt 4;$i++){
  $x = 56 + $i*108; $h = [int][math]::Round($bars[$i][1]/48.1*$maxH)
  if($bars[$i][2]){ $b = Rect $s $x ($base-$h) 80 $h $K.navy } else { $b = Rect $s $x ($base-$h) 80 $h $K.amberFill $K.amber 1.25; $b.Line.DashStyle = 4 }
  Txt $s ($x-14) ($base-$h-22) 108 18 ("{0:N2}" -f $bars[$i][1]) 13 $K.ink $false 2 | Out-Null
  Txt $s ($x-14) ($base+6) 108 36 $bars[$i][0] 12 $K.ink $false 2 | Out-Null
  if($bars[$i][3] -ne ""){ Txt $s ($x-14) ($base+44) 108 18 $bars[$i][3] 13 $K.amber $false 2 | Out-Null }
}
HLine $s 40 $base 470 $K.grey 1 | Out-Null
Txt $s 40 440 440 50 "Existing allocation: 1,244 miles per unit. Hypothetical: 709, 636 and 513 miles per unit." 12.5 $K.grey | Out-Null
$p = Txt $s 510 96 410 300 "Existing (calculated from the dataset): 48,099,961 unit-miles.`rHypothetical: holding each factory at its current volume reduces the simulated distance by 43.0%; with 20% headroom, by 48.9%.`rThe no-limit result (58.8%) is an upper bound, not a plan. It would raise Secret Factory from 884 to 6,263 units (about 7 times), Sugar Shack from 107 to 1,132 (about 11 times) and The Other Factory from 388 to 6,048 (about 16 times).`rRoute scores (calculated): best Wicked Choccy{'}s {->} Gulf, 74.6; worst Wicked Choccy{'}s {->} Pacific, 16.1." 14 $K.ink
$p.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 10
$p.TextFrame.TextRange.Paragraphs(2).Font.Color.RGB = $K.amber; $p.TextFrame.TextRange.Paragraphs(3).Font.Color.RGB = $K.amber
Rect $s 510 410 3 76 $K.amber | Out-Null
Txt $s 524 410 396 76 "These are simulation outputs under stated assumptions. No allocation was implemented, nothing was measured in operation and no saving has been realised." 14 $K.ink $false 1 3 | Out-Null

# ---- 19 Testing ----
$s = NewSlide "Testing and validation" (Note 16)
Txt $s 40 96 300 80 "268" 64 $K.head $true | Out-Null
Txt $s 40 172 300 44 "automated tests in 15 files, all passed in each of four environments" 14 $K.ink | Out-Null
Bullets $s 40 232 310 200 @("All eight pages and 23 downloads checked in a real browser","17 functional requirements implemented and tested","Guard tests: the CSV and the product-to-factory map must not change","The worked examples of the methodology are tests") 13 $K.ink 8 | Out-Null
$d = @(@("Area","Tests"),@("Calculations","149"),@("Robustness","53"),@("Report files","26"),@("Interface (eight pages)","25"),@("Launch and environment","15"),@("Total","268"))
Tbl $s 390 92 $d @(330,100) 26 13 @(1,3) @() @(7) | Out-Null
$d = @(@("Environment","Python","Result"),@("Development (.venv)","3.14.6","268 passed, 116 s"),@("Fresh install","3.14.6","268 passed, 122 s"),@("Fresh install","3.12.8","268 passed, 106 s"),@("Oldest supported versions","3.12.8","268 passed, 87 s"))
Tbl $s 390 290 $d @(210,80,240) 26 13 | Out-Null
Txt $s 390 424 530 70 "Not verified: the CI workflow has never been run; the Excel output was read back with OpenPyXL but not opened in Excel; no coverage figure, benchmark or user survey." 12.5 $K.grey | Out-Null

# ---- 20 Learning ----
$s = NewSlide "Learning outcomes" (Note 17)
$d = @(@("Area","What I implemented","What it showed me"),
 @("Unreliable data","A distance and ship-mode score instead of a delivery-time metric; lead time kept only as an unreliable column","What can honestly be claimed depends on what the data contains"),
 @("Geospatial calculation","Haversine distances from 5 factories to 59 states and provinces; a test checks New York to Los Angeles at about 2,445 mi","Straight-line distance to a centroid is an approximation"),
 @("Optimization","A 383-cell transportation model in OR-Tools GLOP with pre-checks for infeasibility","A result is only as meaningful as its visible assumptions; the model structure guarantees whole-number plans"),
 @("Statistical screening","The IQR rule and consistency checks that flag but never delete","Unusual is not the same as wrong"),
 @("Testing","268 tests; regression tests for an empty-input crash in scoring and an error when comparing identical plans","Tests are what make the numbers trustworthy"))
Tbl $s 40 92 $d @(140,400,340) 52 12.5 | Out-Null
Txt $s 40 428 880 60 "Challenges: Canadian province coordinates were not available, so I used provisional centroids and checked their sensitivity (a 100-mile shift changed no score by more than 1.4 points). Keeping the pages, cached data and installed packages consistent required a start-up environment check and launch scripts that use only the project{'}s .venv." 12.5 $K.ink | Out-Null

# ---- 21 Conclusion ----
$s = NewSlide "Conclusion" (Note 18)
Txt $s 40 96 500 20 "What was built" 15 $K.blue $true | Out-Null
Txt $s 40 120 520 90 "One Python application: an eight-page Streamlit dashboard with data preprocessing, haversine distances, a Route Efficiency Score, a linear-programming allocation model, a scenario simulator, rule-based anomaly detection and recommendations, and PDF, Excel and CSV reports." 13.5 $K.ink | Out-Null
Txt $s 40 224 500 20 "What was demonstrated" 15 $K.blue $true | Out-Null
Txt $s 40 248 520 80 "268 automated tests passed in four environments. All eight pages and 23 downloads worked in a real browser. The optimization control run reproduces the existing allocation exactly." 13.5 $K.ink | Out-Null
Txt $s 40 342 500 20 "What remains limited" 15 $K.blue $true | Out-Null
Txt $s 40 366 520 120 "The optimization results are hypothetical: capacities and eligibility are assumptions and distances are straight lines to centroids. No allocation was implemented, so there are no operational outcomes. The report states eight limitations." 13.5 $K.ink | Out-Null
Txt $s 610 96 310 20 "Future work" 15 $K.blue $true | Out-Null
Bullets $s 610 122 310 360 @("Obtain real eligibility and capacity data","Add shipping costs and road distances","Verify the Canadian province centroids","Investigate the 396 likely duplicate lines with the data owner","Run the CI workflow and add a coverage report","Move the reference tables into their own module","Add saved scenarios per user") 13.5 $K.ink 8 $true | Out-Null

# ---- 22 Thank you ----
$s = NewSlide "Thank you" "Thank you. I am happy to take questions about the project, the method or the results." $true
$s.Shapes.Title.Top = 190; $s.Shapes.Title.Height = 60; $s.Shapes.Title.TextFrame.TextRange.Font.Size = [single]40
Txt $s 40 250 600 28 "Questions are welcome." 20 $K.pale | Out-Null
Txt $s 40 440 880 44 "Supply Chain Route Analytics and Optimization System`rK S Mohamed Adnan Ali  {.}  RRN 240071601022" 13 $K.pale | Out-Null
