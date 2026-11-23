# ---------------- Slide 1: Title ----------------
$n1 = "Good morning. I am Mohamed Adnan Ali. This presentation covers my one-month Data Analyst internship at Unified Mentor and the project I built during it: the Supply Chain Route Analytics and Optimization System. I will explain the problem, how the system works, what it found, and how I tested it. One point I will repeat: the optimization results are a what-if simulation, not real savings."
$s = NewSlide "Supply Chain Route Analytics and Optimization System" "" $n1 $true
$t = $s.Shapes.Title; $t.Left=40; $t.Top=176; $t.Width=560; $t.Height=104; $t.TextFrame.TextRange.Font.Size=38
$kk = Txt $s 40 150 560 18 "INTERNSHIP PROJECT PRESENTATION" 12 $K.teal $true
$lg = Pic $s 'logo_unified_mentor_navy.png' 40 30 165 -1 'Unified Mentor Pvt. Ltd. logo'
$cc = Box $s 726 26 194 66 $K.white $null 0.12
$lg2 = Pic $s 'logo_crescent.png' 736 34 174 -1 'B.S. Abdur Rahman Crescent Institute of Science and Technology logo'
$sub = Txt $s 40 296 560 24 "Data Analyst Intern  {--}  Unified Mentor Pvt. Ltd." 16 (RGB 190 205 225)
$rl = Box $s 40 336 60 3 $K.teal $null 0
$d1 = Txt $s 40 352 570 20 "K S Mohamed Adnan Ali  {.}  RRN 240071601022" 15 $K.white $true
$d2 = Txt $s 40 378 570 18 "B.Tech Computer Science and Engineering" 12 (RGB 190 205 225)
$d3 = Txt $s 40 398 570 18 "B.S. Abdur Rahman Crescent Institute of Science and Technology" 12 (RGB 190 205 225)
$d4 = Txt $s 40 424 570 18 "Faculty guide: Dr. I. Karthiga, Assistant Professor, Department of CSE" 11.5 (RGB 150 170 198)
$d5 = Txt $s 40 444 570 18 "Industry mentor: Sham Singh, Academic Counsellor" 11.5 (RGB 150 170 198)
$d6 = Txt $s 40 474 570 18 "Internship: 25 June 2026 {-} 25 July 2026 (remote)  {.}  November 2026" 11.5 $K.teal $true
# abstract route network (decorative, editable shapes)
$rnd = New-Object System.Random 11
$fx = @(@(700,380),@(850,330),@(770,230),@(880,190),@(660,150))
$pts = @()
for($i=0;$i -lt 30;$i++){ $pts += ,@((630 + $rnd.Next(0,290)),(125 + $rnd.Next(0,340))) }
$g = 0
foreach($p in $pts){
  $f = $fx[$g % 5]; $g++
  $ln = $s.Shapes.AddLine($f[0],$f[1],$p[0],$p[1]); $ln.Line.ForeColor.RGB=$K.teal; $ln.Line.Weight=0.6; $ln.Line.Transparency=0.65
  $dot = $s.Shapes.AddShape(9,$p[0]-3,$p[1]-3,6,6); $dot.Fill.ForeColor.RGB=(RGB 120 150 190); $dot.Line.Visible=0
}
foreach($f in $fx){
  $ring = $s.Shapes.AddShape(9,$f[0]-14,$f[1]-14,28,28); $ring.Fill.ForeColor.RGB=$K.teal; $ring.Fill.Transparency=0.75; $ring.Line.Visible=0
  $core = $s.Shapes.AddShape(9,$f[0]-6,$f[1]-6,12,12); $core.Fill.ForeColor.RGB=$K.teal; $core.Line.ForeColor.RGB=$K.white; $core.Line.Weight=1.2
}

# ---------------- Slide 2: Internship overview ----------------
$n = "I did a one-month remote internship as a Data Analyst Intern at Unified Mentor, from 25 June to 25 July 2026. My industry mentor was Sham Singh and my faculty guide at Crescent was Dr. Karthiga. The certificate on the right was issued on 25 July 2026. The project I will present was the single integrated project of this internship."
$s = NewSlide "Internship overview" "INTERNSHIP" $n
$tiles = @(
 @("ROLE","Data Analyst Intern"), @("ORGANISATION","Unified Mentor Pvt. Ltd."),
 @("DURATION","25 Jun 2026 {-} 25 Jul 2026 (one month)"), @("MODE","Remote internship"),
 @("INDUSTRY MENTOR","Sham Singh, Academic Counsellor"), @("FACULTY GUIDE","Dr. I. Karthiga, Assistant Professor, Dept. of CSE"))
for($i=0;$i -lt 6;$i++){
  $cx = 40 + ($i % 2)*230; $cy = 100 + [int][math]::Floor($i/2)*88
  $b = Box $s $cx $cy 220 78 $K.light $K.line 0.08
  $a = Box $s $cx ($cy+10) 3 58 $K.teal $null 0
  $l = Txt $s ($cx+14) ($cy+10) 195 14 $tiles[$i][0] 9.5 $K.muted $true
  $v = Txt $s ($cx+14) ($cy+28) 196 46 $tiles[$i][1] 13 $K.navy $true
}
$pb = Box $s 40 372 450 96 $K.navy $null 0.06
$pl = Txt $s 58 384 410 14 "PROJECT" 9.5 $K.teal $true
$pv = Txt $s 58 402 414 62 "Supply Chain Route Analytics and Optimization System {--} one integrated application built during the internship" 14 $K.white $true
$cert = Pic $s 'cert_internship.jpeg' 516 100 404 -1 'Certificate of Internship issued by Unified Mentor Pvt. Ltd. on 25 July 2026'
Frame $cert $K.line 1
$cap = Txt $s 516 ($cert.Top + $cert.Height + 8) 404 16 "Certificate of Internship, issued 25 July 2026" 10.5 $K.muted

# ---------------- Slide 3: Organisation ----------------
$n = "Unified Mentor Pvt. Ltd. is a mentorship and training organisation that offers remote internships. Its Corporate Identity Number and its ISO 9001:2015 statement are printed on my certificate. I have not stated the company's founding year or history, because I could not confirm them from an official source. The listed duties of a data analyst intern, cleaning data, analysing trends and preparing reports, match the parts of my project."
$s = NewSlide "Organisation: Unified Mentor Pvt. Ltd." "INTERNSHIP" $n
$nb = Box $s 40 100 330 250 $K.navy $null 0.05
$lg = Pic $s 'logo_unified_mentor_navy.png' 70 130 270 -1 'Unified Mentor Pvt. Ltd. logo'
$tg = Txt $s 60 258 290 20 "Your Skill, Success & Journey" 13 $K.teal $true 2
$nm = Txt $s 60 290 290 24 "Unified Mentor Pvt. Ltd." 17 $K.white $true 2
$nm2 = Txt $s 60 318 290 16 "Organisation named on the internship certificate" 10 (RGB 150 170 198) $false 2
$gn = Box $s 40 362 330 84 $K.grey $null 0.06
$gt = Txt $s 56 372 300 66 "Not stated in this report: the company{'}s founding year, history and mission {--} they were not confirmed from an official source." 11.5 $K.muted
$facts = @(
 @("CORPORATE IDENTITY NUMBER","U85500HR2023PTC115118 (as printed on the internship certificate)"),
 @("CERTIFICATION","ISO 9001:2015 certified company (as stated on the certificate)"),
 @("ORGANISATION TYPE","Mentorship and training organisation offering remote internships (public job listing)"),
 @("WEBSITE AND OFFICE","unifiedmentor.com  {.}  Gurugram, Haryana (details supplied by the intern)"))
for($i=0;$i -lt 4;$i++){
  $y = 100 + $i*60
  $b = Box $s 395 $y 525 52 $K.light $K.line 0.1
  $a = Box $s 395 ($y+8) 3 36 $K.teal $null 0
  $l = Txt $s 410 ($y+7) 500 13 $facts[$i][0] 9 $K.muted $true
  $v = Txt $s 410 ($y+22) 500 28 $facts[$i][1] 12 $K.navy $true
}
$hh = Txt $s 395 348 525 16 "HOW THE INTERNSHIP MAPS TO THE PROJECT" 9.5 $K.tealD $true
$steps = @("Collect and clean data","Analyse trends","Prepare reports and visualisations")
for($i=0;$i -lt 3;$i++){
  $x = 395 + $i*181
  $c = Box $s $x 370 163 46 $K.tealL $K.teal 0.15
  SText $c $steps[$i] 11.5 $K.tealD $true 2 3 6 | Out-Null
  if($i -lt 2){ $ar = Arrow $s ($x+163) 393 ($x+181) 393 $K.tealD 1.5 }
}
$sn = Txt $s 395 424 525 44 "Typical duties of this internship type according to public listings; they correspond to the preprocessing, analytics and reporting components of the project." 10.5 $K.muted

# ---------------- Slide 4: Problem statement ----------------
$n = "Nassau Candy makes 15 products at 5 factories and ships across the United States and Canada. The company asked three things: how good are the current routes, what looks irregular, and could a different factory allocation shorten the distance. The hard part is on the right. The data has no usable shipping times, no factory column, no customer coordinates and no cost or capacity data. So I labelled every number as dataset, calculated or assumption."
$s = NewSlide "Problem statement" "PROBLEM" $n
$ib = Box $s 40 100 520 62 $K.light $K.line 0.08
$it = Txt $s 56 108 490 48 "Nassau Candy is a confectionery distributor: 15 products, each made at one of 5 factories, shipped to customers across the United States and Canada." 12.5 $K.ink $false 1 3
$qs = @("How efficient are the existing factory-to-customer routes?","Which records and routes look irregular?","If other factories could make a product, how much shorter would total shipping distance be {--} and how sensitive is that to capacity limits?")
for($i=0;$i -lt 3;$i++){
  $y = 176 + $i*84
  $b = Box $s 40 $y 520 74 $K.white $K.line 0.08
  $c = $s.Shapes.AddShape(9,54,$y+19,36,36); $c.Fill.ForeColor.RGB=$K.teal; $c.Line.Visible=0
  SText $c ([string]($i+1)) 16 $K.white $true 2 3 0 | Out-Null
  $q = Txt $s 104 ($y+6) 440 62 $qs[$i] 13.5 $K.navy $true 1 3
}
$rb = Box $s 585 100 335 326 $K.redL $null 0.05
$rh = Txt $s 603 112 300 18 "WHAT THE DATA CANNOT TELL US" 10.5 $K.red $true
$bl = Bullets $s 603 138 302 280 @("Shipping dates are unusable: ship minus order date averages about 1,300 days for every ship mode","No factory column: the product-to-factory map is an assumption","No customer coordinates: state or province centroids are used","No transport cost, capacity or eligibility data","3,018 repeated order lines; one fixed price per product") 13 $K.ink 16 $K.red
$sb = Box $s 40 440 880 52 $K.tealL $K.teal 0.12
$st = Txt $s 58 440 846 52 "Response: every number is labelled Dataset, Calculated or Assumption {--} and the optimization is presented as a hypothetical what-if, never as achieved savings." 12.5 $K.tealD $true 1 3

# ---------------- Slide 5: Objectives and scope ----------------
$n = "These were my six objectives, in the order of the work: prepare the data, measure distance and score routes, build the linear-programming model, detect anomalies and make recommendations, present everything in a dashboard with reports, and test it. On the right, in scope is one dataset analysed locally. Out of scope is anything about deployment, delivery-time prediction, cost modelling or machine learning."
$s = NewSlide "Objectives and scope" "OBJECTIVES" $n
$obj = @("Load, validate and prepare the dataset with documented, repeatable cleaning rules","Measure factory-to-customer distance and define a transparent Route Efficiency Score","Formulate and solve a linear-programming allocation model; compare what-if scenarios (hypothetical)","Detect irregular records and routes; generate rule-based recommendations","Present results in an interactive dashboard with PDF, Excel and CSV reports","Verify with automated tests; document method, assumptions and limitations")
for($i=0;$i -lt 6;$i++){
  $y = 100 + $i*65
  $b = Box $s 40 $y 490 56 $K.light $K.line 0.1
  $c = $s.Shapes.AddShape(9,52,$y+12,32,32); $c.Fill.ForeColor.RGB=$K.navy; $c.Line.Visible=0
  SText $c ([string]($i+1)) 13 $K.white $true 2 3 0 | Out-Null
  $o = Txt $s 98 ($y+4) 420 48 $obj[$i] 12 $K.ink $false 1 3
}
$ib = Box $s 555 100 365 196 $K.tealL $K.teal 0.06
$ih = Txt $s 571 110 330 16 "IN SCOPE" 10.5 $K.tealD $true
$ibl = Bullets $s 571 134 335 156 @("One dataset, analysed locally","Eight-page Streamlit dashboard","Distances, route scores, LP what-if, anomaly rules, recommendations, reports") 13 $K.ink 12 $K.tealD
$ob = Box $s 555 310 365 171 $K.grey $null 0.06
$oh = Txt $s 571 320 330 16 "OUT OF SCOPE" 10.5 $K.muted $true
$obl = Bullets $s 571 344 335 132 @("Production deployment or external services","Delivery-time prediction and demand forecasting","Production-cost modelling and machine learning","Operating plans {--} optimization is a what-if simulation") 12 $K.ink 7 $K.muted

# ---------------- Slide 6: Dataset overview ----------------
$n = "The data is one CSV file, Nassau Candy Distributor, with 10,194 order lines and 18 columns. There are 8,549 orders, 5,044 customers, 15 products and 59 states and provinces. The factory count of 5 comes from a product-to-factory map in the project brief, so that part is an assumption. Standard Class is the most used ship mode at 60 percent. I recomputed all these statistics from the unmodified file."
$s = NewSlide "Dataset overview" "DATA" $n
$kp = @(@("10,194","order lines",""),@("8,549","orders",""),@("5,044","customers",""),@("15","products",""),@("5","factories","via product map (assumption)"),@("59","states / provinces","US and Canada"),@("18","source columns","no null values"),@("2024{-}2025","order years","2 Jan 2024 {-} 31 Dec 2025"))
for($i=0;$i -lt 8;$i++){
  $cx = 40 + ($i % 4)*135; $cy = 100 + [int][math]::Floor($i/4)*96
  $b = Box $s $cx $cy 125 86 $K.light $K.line 0.08
  $a = Box $s $cx $cy 125 4 $K.teal $null 0
  $sz = 24; if($i -eq 7){ $sz = 19 }
  $v = Txt $s ($cx+4) ($cy+12) 117 34 $kp[$i][0] $sz $K.navy $true 2 3
  $l = Txt $s ($cx+4) ($cy+48) 117 14 $kp[$i][1] 10.5 $K.ink $false 2
  $m = Txt $s ($cx+4) ($cy+64) 117 18 $kp[$i][2] 8.5 $K.muted $false 2
}
$tb = Box $s 40 296 530 110 $K.white $K.line 0.06
$rows = @(@("Total sales / units / gross profit","{USD}141,783.63  {.}  38,654  {.}  {USD}93,442.80"),@("Rows by country","9,994 United States  {.}  200 Canada"),@("Route distance per line","mean 1,239.9 mi {.} median 1,119.5 mi {.} 61.7{-}2,978.6 mi"))
for($i=0;$i -lt 3;$i++){
  $y = 304 + $i*34
  $l = Txt $s 54 $y 190 30 $rows[$i][0] 10.5 $K.muted $true 1 3
  $v = Txt $s 246 $y 316 30 $rows[$i][1] 11.5 $K.navy $true 1 3
  if($i -lt 2){ $d = $s.Shapes.AddLine(54,$y+32,556,$y+32); $d.Line.ForeColor.RGB=$K.line; $d.Line.Weight=0.5 }
}
$cb = Box $s 600 100 320 306 $K.white $K.line 0.04
$ch = Txt $s 616 110 290 16 "ORDERS BY SHIP MODE (DATASET)" 10 $K.muted $true
$modes = @(@("Standard Class",5142,"60.1%"),@("Second Class",1653,"19.3%"),@("First Class",1312,"15.3%"),@("Same Day",442,"5.2%"))
for($i=0;$i -lt 4;$i++){
  $y = 146 + $i*62
  $ml = Txt $s 616 $y 290 14 $modes[$i][0] 11 $K.ink $true
  $bw = [int][math]::Round(215 * $modes[$i][1] / 5142)
  $bar = Box $s 616 ($y+18) $bw 22 $K.teal $null 0
  $vv = Txt $s (616+$bw+8) ($y+18) 75 22 ("{0:N0}  ({1})" -f $modes[$i][1],$modes[$i][2]) 10.5 $K.navy $true 1 3
}
$nt = Box $s 40 418 880 48 $K.tealL $K.teal 0.12
$ntt = Txt $s 56 418 850 48 "Two factories dominate: Lot{'}s O{'} Nuts ships 55% of units and Wicked Choccy{'}s 41%; together they bring 92.9% of sales. The three smaller factories ship 1,379 units in total." 11.5 $K.tealD $true 1 3
$src = Txt $s 40 474 880 26 "Source: Nassau_Candy_Distributor.csv, statistics recomputed from the unmodified file (dataset observations). The factory assignment of each product is a project assumption; it is not in the data." 9.5 $K.muted

# ---------------- Slide 7: Technology stack ----------------
$n = "The system is written in Python. Pandas and NumPy handle the data, Streamlit and Plotly build the dashboard, Google OR-Tools solves the optimization with its GLOP solver, ReportLab and OpenPyXL create the PDF and Excel reports, and pytest runs the tests. These are the exact versions in the project's own virtual environment. It runs locally only; it is not deployed."
$s = NewSlide "Technology stack" "TECHNOLOGY" $n
$cols = @(
 @("LANGUAGE AND DATA",@(@("Python 3.14.6","implementation language"),@("pandas 3.1.1","loading, cleaning, aggregation"),@("NumPy 2.5.4","numerical computation"),@("pyarrow 26.0.1","columnar data support"))),
 @("DASHBOARD",@(@("Streamlit 1.67.0","multipage web dashboard"),@("Plotly 7.1.0","interactive charts and maps"))),
 @("OPTIMIZATION",@(,@("OR-Tools 9.15.6755","Google OR-Tools: pywraplp interface with the GLOP simplex solver"))),
 @("REPORTING",@(@("ReportLab 5.1.0","PDF report"),@("OpenPyXL 3.1.5","Excel workbook, nine sheets"))),
 @("TESTING",@(@("pytest 9.2.0","268 automated tests"),@("Streamlit AppTest","drives all eight pages"))))
for($i=0;$i -lt 5;$i++){
  $x = 40 + $i*178
  $b = Box $s $x 100 168 300 $K.light $K.line 0.04
  $h = Box $s $x 100 168 30 $(if($i -eq 2){$K.blue}else{$K.navy}) $null 0.1
  SText $h $cols[$i][0] 10 $K.white $true 2 3 4 | Out-Null
  $items = $cols[$i][1]
  for($j=0;$j -lt $items.Count;$j++){
    $y = 142 + $j*66
    $nm = Txt $s ($x+12) $y 146 20 $items[$j][0] 14 $K.navy $true
    $ds = Txt $s ($x+12) ($y+22) 146 48 $items[$j][1] 11.5 $K.muted
  }
}
$nb = Box $s 40 414 880 62 $K.tealL $K.teal 0.1
$nt = Txt $s 56 414 850 62 "Versions are those installed in the project{'}s own virtual environment (.venv) at final validation; the suite was also run on Python 3.12.8 and on the oldest package versions the project supports. Local use only {--} not deployed." 11.5 $K.tealD $true 1 3

# ---------------- Slide 8: System architecture ----------------
$n = "This is the architecture, in four layers. The data layer is the read-only CSV, loaded and cleaned by route_core.py, with my editable assumptions in config.py. The calculation layer is seven modules with no Streamlit code, so they can be tested without a browser. The amber ones, optimization and scenarios, are the hypothetical simulation modules. The interface layer is the app shell, shared helpers and the eight pages, and the report generator writes the PDF, Excel and CSV files. The key rule: Streamlit code lives only in app.py, ui and views."
$s = NewSlide "System architecture" "ARCHITECTURE" $n
$leg = Badge $s 700 54 220 "Amber = hypothetical simulation modules" 'hyp' 20 9.5
$layers = @(@("DATA",96,66),@("CALCULATION modules/",186,74),@("INTERFACE AND OUTPUT",284,80),@("USER",388,44))
foreach($L in $layers){
  $tg = Box $s 40 $L[1] 100 $L[2] $K.navy $null 0.08
  SText $tg $L[0] 10 $K.white $true 2 3 4 | Out-Null
}
# row 1
$b1 = Box $s 150 96 230 66 $K.grey $K.muted 0.08; SText $b1 "Nassau_Candy_Distributor.csv`r10,194 rows {x} 18 columns (read-only)" 10 $K.ink $false 2 3 6 | Out-Null
$b1.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $b1.TextFrame.TextRange.Paragraphs(1).Font.Size = 11.5
$b2 = Box $s 405 96 330 66 $K.blueL $K.blue 0.08; SText $b2 "route_core.py`rload_and_clean {.} validation {.} reference tables (factories, product map, centroids) {.} haversine" 10 $K.ink $false 2 3 6 | Out-Null
$b2.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $b2.TextFrame.TextRange.Paragraphs(1).Font.Size = 12
$b3 = Box $s 760 96 160 66 $K.amberBg $K.amberLn 0.08; SText $b3 "config.py`rscore weights, ship-mode suitability" 10 $K.ink $false 2 3 6 | Out-Null
$b3.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $b3.TextFrame.TextRange.Paragraphs(1).Font.Size = 11.5
Arrow $s 380 129 405 129 $K.muted | Out-Null
Arrow $s 760 129 735 129 $K.muted | Out-Null
Arrow $s 535 162 535 186 $K.tealD 2 | Out-Null
# row 2
$mods = @(@("scoring","70/30 route score",$false),@("route_analysis","route tables, KPIs",$false),@("optimization","LP via OR-Tools GLOP",$true),@("scenarios","2{-}4 what-if runs",$true),@("anomaly_detection","IQR and rules",$false),@("recommendations","17 rule-based",$false),@("reporting","report data dictionary",$false))
for($i=0;$i -lt 7;$i++){
  $x = 150 + $i*111
  $f = $K.blueL; $l = $K.blue; if($mods[$i][2]){ $f=$K.amberBg; $l=$K.amberLn }
  $m = Box $s $x 186 104 74 $f $l 0.08
  SText $m ($mods[$i][0] + "`r" + $mods[$i][1]) 9.5 $K.ink $false 2 3 3 | Out-Null
  $m.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $m.TextFrame.TextRange.Paragraphs(1).Font.Size = 10
}
Arrow $s 535 260 535 284 $K.tealD 2 | Out-Null
# row 3
$r3 = @(@("app.py","navigation shell and start-up environment check"),@("ui/","filters, cached data, tables, charts, scenario form"),@("views/","eight Streamlit pages sharing one filter sidebar"),@("utils/report_generator.py","PDF {.} Excel (9 sheets) {.} CSV and ZIP"))
for($i=0;$i -lt 4;$i++){
  $x = 150 + $i*196
  $m = Box $s $x 284 182 80 $K.white $K.navy 0.08 1.25
  SText $m ($r3[$i][0] + "`r" + $r3[$i][1]) 10 $K.ink $false 2 3 6 | Out-Null
  $m.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1; $m.TextFrame.TextRange.Paragraphs(1).Font.Size = 11.5
}
Arrow $s 535 364 535 388 $K.tealD 2 | Out-Null
$u = Box $s 150 388 770 44 $K.grey $K.muted 0.12; SText $u "Analyst in a web browser (localhost) {--} sets filters and scenario assumptions, reads the dashboards, downloads reports" 11 $K.ink $true 2 3 8 | Out-Null
$rule = Box $s 40 444 880 48 $K.tealL $K.teal 0.12
$rt = Txt $s 56 444 850 48 "Dependency rule: Streamlit code appears only in app.py, ui/ and views/. Every calculation lives in route_core.py and modules/, so it can be tested without a browser." 11.5 $K.tealD $true 1 3

# ---------------- Slide 9: Data preprocessing ----------------
$n = "The loader, load and clean, is the first step for every page. It has nine ordered steps: check the file, convert Sales and Units to numbers, drop invalid rows, trim text, parse the dates, compute a raw lead time for display only, map each product to its factory and each state to its centroid, compute the haversine distance, and flag repeated order lines. On this dataset 10,194 rows go in and 10,194 come out. Nothing is deleted, and an unknown value is never turned into zero."
$s = NewSlide "Data preprocessing: the nine-step pipeline" "DATA PIPELINE" $n
$st = @("1  Locate and validate the CSV (friendly error if bad)","2  Coerce Sales and Units to numbers","3  Drop invalid rows (duplicate Row ID, missing fields, {<=} 0)","4  Trim text fields","5  Parse dates (day / month / year)","6  Raw lead time (display only, flagged unreliable)","7  Map product to factory; state to centroid","8  Haversine distance; unknown location = missing","9  Flag repeated Order ID + Product ID lines (kept)")
for($i=0;$i -lt 9;$i++){
  if($i -lt 5){ $x = 40 + $i*180; $y = 100 } else { $x = 40 + (9-$i)*180; $y = 208 }
  $fill = $K.blueL; $ln = $K.blue; if($i -eq 6 -or $i -eq 7){ $fill=$K.tealL; $ln=$K.teal }
  $b = Box $s $x $y 160 84 $fill $ln 0.08 1.25
  SText $b $st[$i] 11 $K.ink $false 1 3 8 | Out-Null
  $b.TextFrame.TextRange.Characters(1,1).Font.Bold = -1; $b.TextFrame.TextRange.Characters(1,1).Font.Size = 16; $b.TextFrame.TextRange.Characters(1,1).Font.Color.RGB = $K.tealD
}
$out = Box $s 40 208 160 84 $K.tealD $null 0.08; SText $out "Cleaned order lines`r(one DataFrame)" 11.5 $K.white $true 2 3 8 | Out-Null
for($i=0;$i -lt 4;$i++){ Arrow $s (40+$i*180+160) 142 (40+($i+1)*180) 142 $K.muted | Out-Null }
Arrow $s 840 184 840 208 $K.muted | Out-Null
for($i=5;$i -lt 9;$i++){ $x=40+(9-$i)*180; Arrow $s $x 250 ($x-20) 250 $K.muted | Out-Null }
$res = Box $s 40 308 880 44 $K.blueL $K.blue 0.12
$rt = Txt $s 56 308 850 44 "Result on the supplied file: 10,194 rows in {->} 10,194 rows out (none removed)  {.}  0 unknown locations  {.}  3,018 repeated order-product lines flagged" 12 $K.blue $true 1 3
$pr = @(@("Flag, never delete","Repeated lines and anomalies are marked; no record is removed or altered."),@("Unknown is never zero","A missing location gives a missing distance and a Missing Geo flag, never 0."),@("Source file is read-only","The CSV is never modified; a test compares it with its recorded SHA-256 hash."))
for($i=0;$i -lt 3;$i++){
  $x = 40 + $i*298
  $b = Box $s $x 368 284 100 $K.light $K.line 0.08
  $a = Box $s $x 380 3 76 $K.teal $null 0
  $h = Txt $s ($x+16) 378 256 20 $pr[$i][0] 13 $K.navy $true
  $d = Txt $s ($x+16) 404 256 58 $pr[$i][1] 11.5 $K.ink
}
