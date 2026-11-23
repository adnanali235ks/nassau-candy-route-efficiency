function Tbl($s,$x,$y,$data,$colW,$rowH,$fs=10.5,$aligns=$null,$hdrFill=$null){
  if($hdrFill -eq $null){ $hdrFill = $K.navy }
  $nr = $data.Count; $nc = $colW.Count
  $w = 0; foreach($cw in $colW){ $w += $cw }
  $sh = $s.Shapes.AddTable($nr,$nc,$x,$y,$w,$rowH*$nr)
  $tb = $sh.Table
  for($c=1;$c -le $nc;$c++){ $tb.Columns.Item($c).Width = $colW[$c-1] }
  for($r=1;$r -le $nr;$r++){
    $tb.Rows.Item($r).Height = $rowH
    for($c=1;$c -le $nc;$c++){
      $cell = $tb.Cell($r,$c)
      $cell.Shape.Fill.Solid()
      if($r -eq 1){ $cell.Shape.Fill.ForeColor.RGB = $hdrFill } elseif($r % 2 -eq 0){ $cell.Shape.Fill.ForeColor.RGB = $K.white } else { $cell.Shape.Fill.ForeColor.RGB = $K.light }
      $tf = $cell.Shape.TextFrame
      $tf.MarginLeft = 6; $tf.MarginRight = 6; $tf.MarginTop = 2; $tf.MarginBottom = 2; $tf.VerticalAnchor = 3
      $rg = $tf.TextRange; $rg.Text = (T $data[$r-1][$c-1])
      $rg.Font.Name = $FONT; $rg.Font.Size = [single]$fs
      if($r -eq 1){ $rg.Font.Bold = -1; $rg.Font.Color.RGB = $K.white } else { $rg.Font.Bold = 0; $rg.Font.Color.RGB = $K.ink }
      if($aligns -ne $null){ $rg.ParagraphFormat.Alignment = $aligns[$c-1] }
      foreach($bd in 1,2,3,4){ $cell.Borders.Item($bd).ForeColor.RGB = $K.line; $cell.Borders.Item($bd).Weight = 0.5 }
    }
  }
  return $sh
}

# ---------------- Slide 10: Route analytics ----------------
$n = "Route analytics has two parts. First, the haversine formula gives the straight-line distance on a sphere from a factory to the centre of a state. For example, Wicked Choccy's to Texas is 971.5 miles. Second, the Route Efficiency Score is 70 percent distance score plus 30 percent ship-mode score. The weights and the ship-mode values are my assumptions, and they are editable in the dashboard. The worked example gives 71.25. Because shipping dates are unusable, this is a proxy and not a delivery-time measure."
$s = NewSlide "Route analytics: distance and efficiency score" "ROUTE ANALYTICS" $n
$a = Box $s 40 100 380 116 $K.light $K.line 0.06
$ah = Txt $s 54 108 360 16 "HAVERSINE DISTANCE" 10 $K.tealD $true
$af = Txt $s 54 126 360 52 "a = sin{2}({D}{phi}/2) + cos {phi}{s1} {.} cos {phi}{s2} {.} sin{2}({D}{lam}/2)`rd = 2 {.} R {.} atan2({sqrt}a, {sqrt}(1 {minus} a)),   R = 3,958.8 mi" 11.5 $K.navy $true
$af.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 4
$an = Txt $s 54 178 360 34 "Factory {->} state/province centroid: straight line, not road distance. Example: Wicked Choccy{'}s {->} Texas = 971.5 mi" 10.5 $K.muted
$b = Box $s 40 226 380 132 $K.light $K.line 0.06
$bh = Txt $s 54 234 360 16 "ROUTE EFFICIENCY SCORE (0{-}100, higher = better)" 10 $K.tealD $true
$bf = Txt $s 54 252 360 44 "Score = 0.70 {x} Distance Score + 0.30 {x} Ship-Mode Score`rDistance Score = 100 {x} (1 {minus} d / d_ref)" 12 $K.navy $true
$bf.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 4
$bs = Txt $s 54 300 360 54 "Ship-mode suitability (assumptions, editable): Same Day 1.00 {.} First Class 0.85 {.} Second Class 0.60 {.} Standard Class 0.40. d_ref = longest route in the dataset." 10.5 $K.muted
$c = Box $s 40 368 380 100 $K.tealL $K.teal 0.06
$ch = Txt $s 54 376 360 16 "WORKED EXAMPLE" 10 $K.tealD $true
$cb = Txt $s 54 394 360 70 "500 mi route, d_ref 2,000 mi {->} Distance Score 75`r50% Standard + 50% First {->} Ship-Mode Score 62.5`rScore = 0.7 {x} 75 + 0.3 {x} 62.5 = 71.25" 11.5 $K.ink
$cb.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 3
$pc = Pic $s 'focus_route.png' 440 100 480 -1 'Screenshot of the Route Performance page showing the top 10 and bottom 10 routes by Route Efficiency Score'
Frame $pc $K.line 1
$cy = $pc.Top + $pc.Height + 6
$pcap = Txt $s 440 $cy 340 16 "Route Performance page: top 10 and bottom 10 region routes" 10 $K.muted
$bd = Badge $s 800 $cy 120 "CALCULATED" 'calc' 18 9
$ky = $cy + 28; $kh = 468 - $ky
$k1 = Box $s 440 $ky 236 $kh $K.tealL $K.teal 0.1
$k1v = Txt $s 452 $ky 70 $kh "74.6" 22 $K.tealD $true 1 3
$k1l = Txt $s 524 $ky 146 $kh "Best: Wicked Choccy{'}s {->} Gulf (349 mi avg.)" 10.5 $K.ink $false 1 3
$k2 = Box $s 684 $ky 236 $kh $K.redL $K.red 0.1
$k2v = Txt $s 696 $ky 70 $kh "16.1" 22 $K.red $true 1 3
$k2l = Txt $s 768 $ky 146 $kh "Worst: Wicked Choccy{'}s {->} Pacific (2,145 mi avg.)" 10.5 $K.ink $false 1 3

# ---------------- Slide 11: Linear programming ----------------
$n = "The optimization model asks one question: if other factories could make a product, how much shorter would the total distance be? Demand is grouped into 383 cells, each a state or province and a product. The model decides how many units of each cell come from each factory, to minimise units times miles. Every cell's demand must be met, and capacity and eligibility are optional limits. It is a transportation problem solved with Google OR-Tools GLOP, which uses the simplex method. Because of its structure the answer comes out in whole numbers. All of it is hypothetical, because capacities and eligibility are my assumptions."
$s = NewSlide "Optimization model: linear programming" "OPTIMIZATION" $n
$hb = Badge $s 700 54 220 "HYPOTHETICAL SIMULATION" 'hyp' 20 10
$fb = Box $s 40 100 440 188 $K.navy $null 0.05
$fh = Txt $s 56 108 400 16 "TRANSPORTATION-TYPE LP" 10 $K.teal $true
$f1 = Txt $s 56 128 410 34 "minimise   {S} d_cf {.} x_cf   (total unit-miles)" 14 $K.white $true
$f2 = Bullets $s 56 168 410 118 @("{S}_f x_cf = D_c   every cell{'}s demand is supplied","{S}_c x_cf {<=} K_f   factory capacity (hypothetical)","x_cf = 0 if E_cf = 0,  x_cf {>=} 0   eligibility") 14 $K.white 12 $K.teal
$lb = Box $s 40 298 440 74 $K.light $K.line 0.06
$lt = Txt $s 54 304 414 66 "x_cf = units of cell c shipped from factory f  {.}  c = state/province {x} product (383 cells)  {.}  f = 5 factories  {.}  D_c = units demanded  {.}  d_cf = haversine miles  {.}  E_cf = eligibility  {.}  K_f = capacity" 10.5 $K.muted $false 1 3
$mb = Box $s 40 382 440 86 $K.tealL $K.teal 0.06
$mt = Txt $s 54 388 414 76 "Solved with OR-Tools pywraplp and the GLOP simplex solver. A transportation problem is totally unimodular, so plans are whole numbers without rounding. Pre-checks explain infeasibility in plain language." 11 $K.ink $false 1 3
BoldPart $mt "totally unimodular" $K.tealD
$pc = Pic $s 'focus_optim.png' 500 100 420 -1 'Screenshot of the Optimization Center page with the hypothetical simulation banner and result KPIs'
Frame $pc $K.line 1
$cy = $pc.Top + $pc.Height + 6
$pcap = Txt $s 500 $cy 420 14 "Optimization Center page: no capacity limits (upper bound)" 10 $K.muted
$eb = Box $s 500 ($cy+24) 420 (468-$cy-24) $K.amberBg $K.amberLn 0.06
$eh = Txt $s 514 ($cy+30) 390 14 "WORKED EXAMPLE (AN AUTOMATED TEST)" 9.5 $K.amber $true
$et = Txt $s 514 ($cy+46) 395 (468-$cy-50) "Two factories, three cells: all from A = 16,500 unit-miles. No limits: 9,500 ({minus}42.4%). B capped at 40 units: 10,500 ({minus}36.4%). Capacities 20 + 30 for 60 units: infeasible, short by 10." 11.5 $K.ink

# ---------------- Slide 12: Scenario simulation ----------------
$n = "The Scenario Simulator lets the user compare two to four what-if scenarios with the existing allocation. A scenario is a name, an eligibility rule, an optional capacity headroom and an optional cost rate. The table shows the four runs I verified. With no capacity limits the distance falls 58.8 percent, but that is an upper bound. Keeping each factory at its current volume gives 43 percent, and with 20 percent headroom 48.9 percent. The last row is a control: allowing only the current mapping gives exactly the existing 48,099,961, which shows the model is consistent. None of this is a real saving."
$s = NewSlide "Scenario simulation" "SCENARIOS" $n
$hb = Badge $s 700 54 220 "HYPOTHETICAL RESULTS" 'hyp' 20 10
$hw = Box $s 40 100 470 134 $K.light $K.line 0.06
$hh = Txt $s 54 108 440 16 "HOW A SCENARIO WORKS" 10 $K.tealD $true
$hl = Bullets $s 54 128 444 104 @("A scenario = name + eligibility (all factories, current mapping, or custom locks and exclusions) + optional capacity headroom + optional cost rate","Two to four scenarios are solved with the same model as the Optimization Center","Infeasible scenarios return a plain-language reason; unsolved values stay blank, never zero") 11.5 $K.ink 5 $K.tealD
$tdata = @(@("Scenario","Unit-miles","Reduction","Cells changed"),
 @("Existing allocation (dataset, calculated)","48,099,961","{--}","{--}"),
 @("No capacity limits (upper bound)","19,836,723","58.8%","304"),
 @("Capacity = current volume","27,394,134","43.0%","248"),
 @("Current volume + 20% headroom","24,602,248","48.9%","255"),
 @("Control: current mapping only","48,099,961","0.0%","0"))
$tt = Tbl $s 40 246 $tdata @(214,90,76,90) 30 10.5 @(1,3,3,3)
$ttn = Txt $s 40 436 470 32 "Unit-miles = units {x} straight-line miles to the state/province centroid. Reduction = existing minus scenario." 10 $K.muted
$pc = Pic $s 'focus_scen.png' 530 100 390 -1 'Screenshot of the Scenario Simulator comparison table and unit-miles chart'
Frame $pc $K.line 1
$cy = $pc.Top + $pc.Height + 6
$pcap = Txt $s 530 $cy 390 14 "Scenario Simulator page: comparison and chart" 10 $K.muted
$ab = Box $s 530 ($cy+24) 390 (468-$cy-24) $K.amberBg $K.amberLn 0.06
$at = Txt $s 544 ($cy+28) 364 (468-$cy-32) "Hypothetical: results depend on assumed eligibility and capacities. The control run reproduces the existing 48,099,961 unit-miles exactly, with 0 cells changed {--} the model and comparison are consistent." 11 $K.ink $false 1 3
BoldPart $at "Hypothetical:" $K.amber

# ---------------- Slide 13: Anomalies and recommendations ----------------
$n = "Anomaly detection uses simple statistics, mainly the interquartile range, plus consistency rules. It only flags records for review and never deletes or changes anything. The single outlier is a very long, low-volume route to Newfoundland and Labrador. The 3,018 repeated lines need a decision by the data owner. Recommendations are simple if-then rules. Each shows the reason, the exact rule, the supporting numbers, a basis label and a priority. There are 17: 9 high, 4 medium and 4 low. No machine learning is used. Eight of them are hypothetical."
$s = NewSlide "Anomalies and recommendations" "INSIGHTS" $n
$adata = @(@("Check (flags only, nothing deleted)","Flagged"),
 @("Route distance outliers (IQR rule)","1 of 196 routes"),
 @("Repeated order lines (396 identical)","3,018 lines"),
 @("Missing geography","0"),
 @("Unusual sales / gross-profit patterns","0"),
 @("Product ID vs Division mismatch","6 lines"),
 @("Very-low-volume factories / products","9 (2 + 7)"))
$at = Tbl $s 40 100 $adata @(300,110) 26 10.5 @(1,3)
$iq = Box $s 40 292 410 70 $K.light $K.line 0.06
$iqt = Txt $s 54 296 384 62 "IQR rule: flag values outside Q1 {minus} 1.5{x}IQR and Q3 + 1.5{x}IQR. The one outlier: Lot{'}s O{'} Nuts {->} Newfoundland and Labrador, 2,979 mi vs fence 2,720 mi, only 5 orders. Unusual means {lq}worth a look{rq}, not {lq}wrong{rq}." 10.5 $K.ink $false 1 3
$rb = Box $s 40 372 410 96 $K.navy $null 0.06
$rh = Txt $s 54 380 380 16 "17 RULE-BASED RECOMMENDATIONS" 10 $K.teal $true
$pill = @(@("9","High",$K.red),@("4","Medium",$K.amberBar),@("4","Low",$K.tealD))
for($i=0;$i -lt 3;$i++){
  $x = 54 + $i*76
  $pb = Box $s $x 402 68 24 $pill[$i][2] $null 0.4
  SText $pb ($pill[$i][0] + "  " + $pill[$i][1]) 10.5 $K.white $true 2 3 2 | Out-Null
}
$rt2 = Txt $s 54 432 384 34 "Each shows Why, Rule, Supporting Values, Basis and Priority. No machine learning." 10.5 (RGB 190 205 225)
$p1 = Pic $s 'focus_anom.png' 470 100 450 -1 'Screenshot of the Anomaly Detection summary table'
Frame $p1 $K.line 1
$c1 = Txt $s 470 ($p1.Top+$p1.Height+4) 450 14 "Anomaly Detection page: summary and reasons" 10 $K.muted
$p2y = $p1.Top + $p1.Height + 26
$p2 = Pic $s 'focus_recs.png' 470 $p2y 450 -1 'Screenshot of the Smart Recommendations page showing recommendation R01 with Why, Rule and Supporting Values'
Frame $p2 $K.line 1
$c2 = Txt $s 470 ($p2.Top+$p2.Height+4) 450 14 "Smart Recommendations page: Why, Rule, Supporting Values, Basis" 10 $K.muted

# ---------------- Slide 14: Application demonstration ----------------
$n = "These are real screenshots of the running dashboard, with no editing. It has eight pages that share one sidebar of filters: Executive Overview, Geographic Analysis, Route Performance, Optimization Center, Scenario Simulator, Smart Recommendations, Anomaly Detection and Reports. I opened every page in a real browser with no errors and checked all 23 download buttons. In the viva I can show any page live. Every hypothetical page carries a warning banner."
$s = NewSlide "Application demonstration" "DASHBOARD" $n
$g = @(@("1  Executive Overview","tile_executive.png","KPIs, ship-mode mix, sales by factory"),@("2  Geographic Analysis","tile_geographic.png","route map, distance bands, density"),@("3  Route Performance","tile_route.png","route scores, ship modes, drill-down"),@("4  Optimization Center","tile_optim.png","hypothetical LP allocation, exports"),@("5  Scenario Simulator","tile_scenario.png","compare 2{-}4 what-if scenarios"),@("6  Smart Recommendations","tile_recs.png","17 rule-based, auditable prompts"),@("7  Anomaly Detection","tile_anomaly.png","IQR and consistency flags with reasons"),@("8  Reports","tile_reports.png","PDF, Excel (9 sheets), CSV and ZIP"))
for($i=0;$i -lt 8;$i++){
  $cx = 40 + ($i % 4)*224; $cy = 96 + [int][math]::Floor($i/4)*178
  $pp = Pic $s $g[$i][1] $cx $cy 208 -1 ("Screenshot of the " + ($g[$i][0].Substring(3)) + " page")
  Frame $pp $K.line 1
  $cp = Txt $s $cx ($cy+$pp.Height+4) 208 16 $g[$i][0] 11 $K.navy $true
  $cd = Txt $s $cx ($cy+$pp.Height+21) 208 14 $g[$i][2] 9.5 $K.muted
}
$gb = Box $s 40 456 880 38 $K.tealL $K.teal 0.15
$gt = Txt $s 56 456 850 38 "Real screenshots of the running dashboard (unedited). One filter sidebar is shared by all eight pages; pages and 23 downloads were verified in a real browser." 10.5 $K.tealD $true 1 3

# ---------------- Slide 15: Results and analysis ----------------
$n = "Here are the main results. On the left is the hypothetical distance comparison. The existing allocation is about 48.1 million unit-miles. The simulation shows 43 percent less if each factory keeps its current volume, 48.9 percent with 20 percent headroom, and 58.8 percent with no limits. The last one is an upper bound and not a plan, because it would load the three small factories 7 to 16 times more than today, as shown on the right. On the right top are calculated route scores: the best route is 74.6 and the worst is 16.1. I want to stress that no allocation was implemented and no saving has been realised."
$s = NewSlide "Results and analysis" "RESULTS" $n
$hb = Badge $s 660 54 260 "DISTANCE RESULTS ARE HYPOTHETICAL" 'hyp' 20 10
$cb = Box $s 40 100 470 336 $K.white $K.line 0.03
$ch = Txt $s 56 108 440 16 "TOTAL SHIPPING DISTANCE (UNIT-MILES, MILLIONS)" 10 $K.muted $true
$base = 372; $maxH = 200
$bars = @(@("Existing`r(dataset)",48.10,"",$true),@("Current`rvolume",27.39,"{minus}43.0%",$false),@("+20%`rheadroom",24.60,"{minus}48.9%",$false),@("No limits`r(upper bound)",19.84,"{minus}58.8%",$false))
for($i=0;$i -lt 4;$i++){
  $x = 72 + $i*108; $h = [int][math]::Round($bars[$i][1]/48.1*$maxH)
  if($bars[$i][3]){ $bar = Box $s $x ($base-$h) 80 $h $K.navy $null 0 } else { $bar = Box $s $x ($base-$h) 80 $h $K.amberBar $K.amber 0 1.25; $bar.Line.DashStyle = 4 }
  $vl = Txt $s ($x-10) ($base-$h-20) 100 18 ("{0:N2} M" -f $bars[$i][1]) 12.5 $K.navy $true 2
  if($bars[$i][2] -ne ""){ $rl = Txt $s $x ($base-$h+8) 80 18 $bars[$i][2] 13 $K.ink $true 2 }
  $cl = Txt $s ($x-14) ($base+6) 108 34 $bars[$i][0] 10.5 $K.ink $false 2
}
$ax = $s.Shapes.AddLine(56,$base,496,$base); $ax.Line.ForeColor.RGB=$K.muted; $ax.Line.Weight=1
$l1 = Box $s 64 414 10 10 $K.navy $null 0; $l1t = Txt $s 80 411 150 16 "Calculated (dataset)" 10 $K.ink
$l2 = Box $s 250 414 10 10 $K.amberBar $K.amber 0; $l2t = Txt $s 266 411 230 16 "Hypothetical (simulation)" 10 $K.ink
$rcard = Box $s 530 100 390 170 $K.white $K.line 0.04
$rh = Txt $s 544 108 360 16 "ROUTE EFFICIENCY SCORE (CALCULATED)" 10 $K.muted $true
$rr = @(@("Wicked Choccy{'}s {->} Gulf",74.6,$true),@("Secret Factory {->} Interior",73.7,$true),@("The Other Factory {->} Gulf",73.6,$true),@("Lot{'}s O{'} Nuts {->} Gulf",31.7,$false),@("Lot{'}s O{'} Nuts {->} Atlantic",20.4,$false),@("Wicked Choccy{'}s {->} Pacific",16.1,$false))
for($i=0;$i -lt 6;$i++){
  $y = 132 + $i*22
  $lt = Txt $s 544 $y 178 18 $rr[$i][0] 10 $K.ink $false 1 3
  $bw = [int][math]::Round(120*$rr[$i][1]/100)
  $colr = $K.red; if($rr[$i][2]){ $colr = $K.teal }
  $bb = Box $s 726 ($y+2) $bw 14 $colr $null 0
  $vt = Txt $s (726+$bw+6) $y 40 18 ("{0:N1}" -f $rr[$i][1]) 10 $K.navy $true 1 3
}
$ob = Box $s 530 280 390 156 $K.amberBg $K.amberLn 0.04
$oh = Txt $s 544 288 360 16 "WHY {lq}NO LIMITS{rq} IS AN UPPER BOUND, NOT A PLAN" 10 $K.amber $true
$ov = @(@("Secret Factory","884","6,263","about 7{x}"),@("Sugar Shack","107","1,132","about 11{x}"),@("The Other Factory","388","6,048","about 16{x}"))
for($i=0;$i -lt 3;$i++){
  $y = 312 + $i*28
  $a1 = Txt $s 544 $y 130 24 $ov[$i][0] 11 $K.ink $true 1 3
  $a2 = Txt $s 676 $y 130 24 ($ov[$i][1] + " {->} " + $ov[$i][2] + " units") 11 $K.ink $false 1 3
  $a3 = Txt $s 828 $y 86 24 $ov[$i][3] 11 $K.amber $true 3 3
}
$on = Txt $s 544 398 362 34 "Capacity-limited scenarios keep the change within the assumed headroom." 10 $K.muted
$fb = Box $s 40 446 880 46 $K.navy $null 0.12
$ft = Txt $s 56 446 850 46 "No allocation was implemented, nothing was measured in operation and no saving has been realised. Operational outcomes: none." 12 $K.white $true 1 3

# ---------------- Slide 16: Testing and validation ----------------
$n = "I treated testing as part of the design. There are 268 automated tests in 15 files, and all 268 passed in each of four environments, including one with the oldest package versions the project supports. I also opened all eight pages in a real browser and checked 23 downloads. The tests protect the original data file, the product map and the worked examples. To be honest about limits: the continuous-integration file has never been run, the Excel file was checked by reading it back and not by opening it in Excel, and I did not measure coverage or run a user survey."
$s = NewSlide "Testing and validation" "VERIFICATION" $n
$kp = @(@("268","automated tests in 15 files"),@("4","environments, 268 passed in each (87{-}122 s)"),@("8 + 23","pages and downloads checked in a real browser"),@("17","functional requirements, all implemented and tested"))
for($i=0;$i -lt 4;$i++){
  $x = 40 + $i*224
  $b = Box $s $x 100 208 74 $K.light $K.line 0.08
  $a = Box $s $x 100 208 4 $K.teal $null 0
  $v = Txt $s ($x+12) 110 184 32 $kp[$i][0] 24 $K.navy $true 1 3
  $l = Txt $s ($x+12) 144 188 28 $kp[$i][1] 10.5 $K.ink
}
$cb = Box $s 40 186 410 196 $K.white $K.line 0.04
$ch = Txt $s 54 194 380 16 "TESTS BY AREA (TOTAL 268)" 10 $K.muted $true
$tb = @(@("Calculations",149),@("Robustness",53),@("Report files",26),@("Interface (8 pages)",25),@("Launch and environment",15))
for($i=0;$i -lt 5;$i++){
  $y = 218 + $i*32
  $l = Txt $s 54 $y 140 24 $tb[$i][0] 10.5 $K.ink $false 1 3
  $bw = [int][math]::Round(190*$tb[$i][1]/149)
  $bb = Box $s 198 ($y+3) $bw 18 $K.teal $null 0
  $vv = Txt $s (198+$bw+6) $y 40 24 ([string]$tb[$i][1]) 10.5 $K.navy $true 1 3
}
$edata = @(@("Environment","Python","Result"),@("Development (.venv)","3.14.6","268 passed, 116 s"),@("Fresh install","3.14.6","268 passed, 122 s"),@("Fresh install","3.12.8","268 passed, 106 s"),@("Oldest supported versions","3.12.8","268 passed, 87 s"))
$et = Tbl $s 470 186 $edata @(170,70,210) 28 10.5 @(1,2,1)
$en = Txt $s 470 332 450 50 "Oldest versions: Streamlit 1.50.0, pandas 2.1.1, NumPy 1.26.0, Plotly 5.18.0, OR-Tools 9.9.3963 {--} the declared lower bounds are tested, not assumed." 10 $K.muted
$gb = Box $s 40 394 430 98 $K.tealL $K.teal 0.06
$gh = Txt $s 54 400 400 16 "WHAT THE TESTS PROTECT" 10 $K.tealD $true
$gt = Txt $s 54 418 404 70 "CSV unchanged (SHA-256) and product map unchanged; worked examples (haversine NY{-}LA about 2,445 mi; LP 16,500 / 9,500 / 10,500); every page renders even when filters match nothing." 10.5 $K.ink
$nb = Box $s 490 394 430 98 $K.amberBg $K.amberLn 0.06
$nh = Txt $s 504 400 400 16 "NOT VERIFIED" 10 $K.amber $true
$nt = Txt $s 504 418 404 70 "CI workflow written but never run  {.}  Excel output read back with OpenPyXL, not opened in Excel  {.}  no coverage figure, no benchmark, no user survey." 10.5 $K.ink

# ---------------- Slide 17: Learning outcomes and challenges ----------------
$n = "From this project I learned the full chain from raw data to decision support. On the left are the skills, each backed by a part of the system. On the right are the main challenges and how I handled them. The biggest lesson is that the data decides what you can honestly claim. Because the shipping dates were unusable, I built a clearly labelled proxy score instead of inventing a delivery-time metric."
$s = NewSlide "Learning outcomes and challenges" "REFLECTION" $n
$sk = @(@("Data analysis with Python","pandas pipeline, 10,194 lines"),@("Geospatial calculation","haversine to 59 states/provinces"),@("Metric design","configurable Route Efficiency Score"),@("Mathematical optimization","transportation LP, OR-Tools GLOP"),@("Statistical screening","IQR rule and consistency checks"),@("Dashboard development","eight-page Streamlit app"),@("Reporting automation","PDF, Excel and CSV outputs"),@("Software testing","268 pytest tests, four environments"))
$sh0 = Txt $s 40 98 420 16 "SKILLS GAINED, WITH EVIDENCE" 10 $K.tealD $true
for($i=0;$i -lt 8;$i++){
  $cx = 40 + ($i % 2)*212; $cy = 120 + [int][math]::Floor($i/2)*74
  $b = Box $s $cx $cy 204 66 $K.light $K.line 0.08
  $a = Box $s $cx ($cy+10) 3 46 $K.teal $null 0
  $h = Txt $s ($cx+14) ($cy+8) 184 32 $sk[$i][0] 12 $K.navy $true 1 3
  $d = Txt $s ($cx+14) ($cy+40) 184 22 $sk[$i][1] 10 $K.muted
}
$ch0 = Txt $s 480 98 440 16 "CHALLENGES AND HOW THEY WERE HANDLED" 10 $K.tealD $true
$chs = @(@("Unusable shipping dates","labelled proxy score; no delivery-time claim"),@("No Canadian coordinates","provisional centroids with a sensitivity check"),@("No factory, capacity or cost data","every optimization result is an editable assumption"),@("Unknown must never become zero","explicit handling and tests in scoring, distance, LP"),@("Keeping environments consistent","start-up check and project-specific launch scripts"))
for($i=0;$i -lt 5;$i++){
  $y = 120 + $i*59
  $b = Box $s 480 $y 440 52 $K.white $K.line 0.1
  $a = Box $s 480 ($y+8) 3 36 $K.amberBar $null 0
  $h = Txt $s 496 ($y+5) 416 18 $chs[$i][0] 11.5 $K.navy $true
  $d = Txt $s 496 ($y+25) 416 24 $chs[$i][1] 10.5 $K.muted
}
$lb = Box $s 40 424 880 68 $K.navy $null 0.1
$lt = Txt $s 58 424 846 68 "Lessons:  data limits decide what can honestly be claimed  {.}  an optimization is only as meaningful as its assumptions  {.}  model structure can guarantee properties such as whole-number plans  {.}  tests make a numerical system trustworthy" 11.5 $K.white $true 1 3

# ---------------- Slide 18: Conclusion and future scope ----------------
$n = "To conclude: in one month I built a single integrated system that cleans the data, measures distances, scores routes, solves an optimization model, compares scenarios, flags anomalies, makes explainable recommendations and generates reports, with 268 tests. The optimization results are hypothetical, there are no operational outcomes, and the limitations are stated in the report. For future work, the most valuable step is to replace my assumptions with real eligibility, capacity and cost data. Thank you. I am happy to take questions."
$s = NewSlide "Conclusion and future scope" "CONCLUSION" $n $true
$lh = Txt $s 40 100 420 16 "WHAT WAS ACHIEVED (IMPLEMENTED FUNCTIONALITY)" 10 $K.teal $true
$lbl = Bullets $s 40 124 420 190 @("Integrated eight-page dashboard: preprocessing, haversine distances, route scoring","Linear-programming allocation model and scenario simulator (OR-Tools GLOP)","Rule-based anomaly detection and 17 explainable recommendations","PDF, Excel and CSV reports; 268 tests in four environments") 13 $K.white 16 $K.teal
$op = Box $s 40 320 420 70 $K.navy2 $K.amberLn 0.08
$opt = Txt $s 56 320 390 70 "Operational outcomes: none.`rThe optimization results are hypothetical. The report states 8 limitations that apply to every result." 12 $K.white $false 1 3
$opt.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $opt.TextFrame.TextRange.Paragraphs(1).Font.Color.RGB = $K.amberBar
$rh2 = Txt $s 500 100 420 16 "FUTURE SCOPE" 10 $K.teal $true
$fu = @("Obtain real eligibility and capacity data","Add shipping costs and road distances","Verify the Canadian province centroids","Investigate the 396 likely duplicate lines","Run the CI workflow; add a coverage report","Move reference tables into their own module","Add saved scenarios per user")
for($i=0;$i -lt 7;$i++){
  $y = 124 + $i*38
  $c = $s.Shapes.AddShape(9,500,$y,26,26); $c.Fill.ForeColor.RGB=$K.teal; $c.Line.Visible=0
  SText $c ([string]($i+1)) 11 $K.navy $true 2 3 0 | Out-Null
  $ft = Txt $s 538 $y 382 26 $fu[$i] 12.5 $K.white $false 1 3
}
$ln = Box $s 40 414 880 2 $K.teal $null 0
$ty = Txt $s 40 428 560 40 "Thank you" 30 $K.white $true 1 3
$tq = Txt $s 40 470 560 20 "Questions are welcome." 13 (RGB 190 205 225)
$tn = Txt $s 560 440 360 40 "K S Mohamed Adnan Ali  {.}  RRN 240071601022`rSupply Chain Route Analytics and Optimization System" 10.5 (RGB 150 170 198) $false 3
$num = Txt $s 860 512 60 14 "" 9 (RGB 150 170 198) $false 3
$num.Name = 'SlideNumber'
$num.TextFrame.TextRange.InsertSlideNumber() | Out-Null
$num.TextFrame.TextRange.Font.Size = 9; $num.TextFrame.TextRange.Font.Name = $FONT; $num.TextFrame.TextRange.Font.Color.RGB = (RGB 150 170 198); $num.TextFrame.TextRange.ParagraphFormat.Alignment = 3
