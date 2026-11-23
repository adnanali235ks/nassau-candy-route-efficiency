function Note($i){ return $NOTES.PSObject.Properties[[string]$i].Value }

# ---- 1 Title ----
$s = NewSlide "Supply Chain Route Analytics and Optimization System" (Note 1) $true
$t = $s.Shapes.Title; $t.Top = 176; $t.Width = 660; $t.Height = 100; $t.TextFrame.TextRange.Font.Size = [single]34
Pic $s 'logo_unified_mentor_navy.png' 40 34 150 -1 'Unified Mentor Pvt. Ltd. logo' | Out-Null
Rect $s 730 30 190 62 $K.white | Out-Null
Pic $s 'logo_crescent.png' 738 38 174 -1 'B.S. Abdur Rahman Crescent Institute of Science and Technology logo' | Out-Null
Txt $s 40 148 600 20 "Internship project presentation" 15 $K.pale | Out-Null
Txt $s 40 296 840 24 "K S Mohamed Adnan Ali, RRN 240071601022" 17 $K.white | Out-Null
$l = @("B.Tech Computer Science and Engineering","B.S. Abdur Rahman Crescent Institute of Science and Technology","Faculty guide: Dr. I. Karthiga, Assistant Professor, Department of CSE","Data Analyst Intern, Unified Mentor Pvt. Ltd. (remote), 25 June 2026 {-} 25 July 2026","Industry mentor: Sham Singh, Academic Counsellor")
$tb = Txt $s 40 328 840 130 ($l -join "`r") 14 $K.pale
$tb.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 5
Txt $s 40 480 400 20 "November 2026" 14 $K.pale | Out-Null

# ---- 2 Internship overview ----
$s = NewSlide "Internship overview" (Note 2)
$d = @(@("Role","Data Analyst Intern"),@("Organisation","Unified Mentor Pvt. Ltd."),@("Period","25 June 2026 {-} 25 July 2026 (one month, remote)"),@("Industry mentor","Sham Singh, Academic Counsellor"),@("Faculty guide","Dr. I. Karthiga, Assistant Professor, Department of CSE"),@("Certificate","Certificate of Internship, issued 25 July 2026"),@("Project","Supply Chain Route Analytics and Optimization System"))
$tbl = Tbl $s 40 100 $d @(150,380) 38 14 $null @() @() $false
for($i=1;$i -le 7;$i++){ $tbl.Table.Cell($i,1).Shape.TextFrame.TextRange.Font.Color.RGB = $K.grey }
Txt $s 40 392 530 18 "Timeline" 13 $K.grey | Out-Null
HLine $s 50 428 540 $K.grey 1.5 | Out-Null
foreach($px in 50,540){ $dot = $s.Shapes.AddShape(9,[single]($px-5),[single]423,[single]10,[single]10); $dot.Fill.ForeColor.RGB = $K.teal; $dot.Line.Visible = 0 }
Txt $s 40 442 250 40 "25 June 2026`rinternship begins" 13 $K.ink | Out-Null
Txt $s 330 442 250 40 "25 July 2026`rinternship ends, certificate issued" 13 $K.ink $false 3 | Out-Null
$cert = Pic $s 'cert_internship.jpeg' 600 100 320 -1 'Certificate of Internship issued by Unified Mentor Pvt. Ltd. on 25 July 2026'
Frame $cert $K.rule
Txt $s 600 ($cert.Top + $cert.Height + 6) 320 16 "Certificate of Internship (issued 25/07/2026)" 11 $K.grey | Out-Null

# ---- 3 Organisation ----
$s = NewSlide "Organisation: Unified Mentor Pvt. Ltd." (Note 3)
$d = @(@("Organisation","Unified Mentor Pvt. Ltd."),@("CIN","U85500HR2023PTC115118 (as printed on the certificate)"),@("Certification","ISO 9001:2015 certified company (as stated on the certificate)"),@("Type","Mentorship and training organisation offering remote internships (public job listing)"),@("Website","unifiedmentor.com"),@("Office","Gurugram, Haryana (details supplied by the intern)"))
$tbl = Tbl $s 40 100 $d @(130,400) 42 14 $null @() @() $false
for($i=1;$i -le 6;$i++){ $tbl.Table.Cell($i,1).Shape.TextFrame.TextRange.Font.Color.RGB = $K.grey }
Txt $s 40 372 530 60 "A data analyst internship of this kind involves collecting and cleaning data, analysing trends and preparing reports and visualisations (public listings). These correspond to the preprocessing, analytics and reporting parts of the project." 13.5 $K.ink | Out-Null
Txt $s 40 446 530 40 "The company{'}s founding year, history and mission are not stated because they were not confirmed from an official source." 12.5 $K.grey | Out-Null
Pic $s 'logo_unified_mentor_navy.png' 610 100 310 -1 'Unified Mentor Pvt. Ltd. logo' | Out-Null
Txt $s 610 218 310 18 "Logo as printed on the internship certificate" 11 $K.grey | Out-Null

# ---- 4 Problem ----
$s = NewSlide "Problem statement" (Note 4)
Txt $s 40 100 540 80 "Nassau Candy is a confectionery distributor. Its 15 products are each made at one of five factories and shipped to customers across the United States and Canada. From the order records alone, the project had to answer three questions:" 15 $K.ink | Out-Null
Bullets $s 40 188 540 170 @("How efficient are the existing factory-to-customer routes?","Which records and routes look irregular?","If other factories could make a product, how much shorter would the total shipping distance be, and how sensitive is that to capacity limits?") 15 $K.ink 10 $true | Out-Null
Txt $s 620 100 300 22 "What the data does not provide" 15 $K.blue $true | Out-Null
Bullets $s 620 130 300 260 @("Usable shipping dates (ship minus order date averages about 1,300 days for every ship mode)","A factory column (the product-to-factory map is an assumption)","Customer coordinates (state and province centroids are used)","Transport cost, capacity or eligibility data") 13.5 $K.ink 8 | Out-Null
Rect $s 40 410 3 62 $K.teal | Out-Null
Txt $s 56 410 840 62 "Every figure in the project is labelled as a dataset observation, a calculated metric or an assumption. The optimization results are presented only as a hypothetical what-if, never as achieved savings." 15 $K.ink $false 1 3 | Out-Null

# ---- 5 Objectives and scope ----
$s = NewSlide "Objectives and scope" (Note 5)
Bullets $s 40 100 540 380 @("Load, validate and prepare the dataset with documented, repeatable cleaning rules.","Measure the distance between factories and customers and define a transparent Route Efficiency Score.","Formulate and solve a linear-programming allocation model and compare what-if scenarios, labelled as hypothetical.","Detect irregular records and routes and generate rule-based recommendations.","Present the results in an interactive dashboard with PDF, Excel and CSV reports.","Verify the system with automated tests and document the method, assumptions and limitations.") 15 $K.ink 12 $true | Out-Null
Txt $s 620 100 300 22 "In scope" 15 $K.blue $true | Out-Null
Bullets $s 620 128 300 120 @("One dataset, analysed locally","An eight-page Streamlit dashboard","Distance, scoring, optimization, anomaly rules, recommendations and reports") 13.5 $K.ink 6 | Out-Null
Txt $s 620 262 300 22 "Not in scope" 15 $K.blue $true | Out-Null
Bullets $s 620 290 300 190 @("Deployment or external services","Delivery-time prediction and demand forecasting","Production-cost modelling","Machine learning","Operating plans: the optimization is a what-if simulation") 13.5 $K.ink 6 | Out-Null

# ---- 6 Dataset ----
$s = NewSlide "Dataset" (Note 6)
$d = @(@("Item","Value"),@("Order lines","10,194 (18 columns, no null values)"),@("Orders","8,549"),@("Customers","5,044"),@("Products","15"),@("Factories","5 (assumed product-to-factory map)"),@("States and provinces","59 (9,994 US rows, 200 Canada rows)"),@("Order dates","2 Jan 2024 {-} 31 Dec 2025"),@("Total sales","{USD}141,783.63"),@("Units","38,654"),@("Gross profit","{USD}93,442.80"),@("Distance per line (calc.)","mean 1,239.9 mi; median 1,119.5; range 61.7{-}2,978.6"))
Tbl $s 40 96 $d @(180,330) 30 12.5 | Out-Null
Txt $s 40 470 500 30 "Dataset observations unless marked. Source: Nassau_Candy_Distributor.csv, statistics recomputed from the unmodified file." 11.5 $K.grey | Out-Null
Txt $s 560 100 360 20 "Orders by ship mode (dataset observation)" 14 $K.blue $true | Out-Null
$modes = @(@("Standard Class",5142,"60.1%"),@("Second Class",1653,"19.3%"),@("First Class",1312,"15.3%"),@("Same Day",442,"5.2%"))
for($i=0;$i -lt 4;$i++){
  $y = 140 + $i*56
  Txt $s 560 $y 200 18 $modes[$i][0] 13 $K.ink | Out-Null
  $bw = [int][math]::Round(240*$modes[$i][1]/5142)
  Rect $s 560 ($y+22) $bw 18 $K.data | Out-Null
  Txt $s (560+$bw+8) ($y+21) 110 20 ("{0:N0} ({1})" -f $modes[$i][1],$modes[$i][2]) 12.5 $K.ink $false 1 3 | Out-Null
}
Txt $s 560 372 360 90 "Two factories dominate the volume: Lot{'}s O{'} Nuts ships 55% of all units and Wicked Choccy{'}s 41%. Together they account for 92.9% of sales; the three smaller factories ship 1,379 units in total." 13.5 $K.ink | Out-Null

# ---- 7 Technology ----
$s = NewSlide "Technology stack" (Note 7)
$d = @(@("Function","Tool","Version","Role"),
 @("Language and data","Python","3.14.6","Implementation language"),@("","pandas","3.1.1","Loading, cleaning, aggregation"),@("","NumPy","2.5.4","Numerical computation"),@("","pyarrow","26.0.1","Columnar data support"),
 @("Dashboard","Streamlit","1.67.0","Multipage web interface"),@("","Plotly","7.1.0","Interactive charts and maps"),
 @("Optimization","Google OR-Tools (GLOP)","9.15.6755","Linear-programming solver"),
 @("Reporting","ReportLab","5.1.0","PDF report"),@("","OpenPyXL","3.1.5","Excel workbook"),
 @("Testing","pytest","9.2.0","268 automated tests, with Streamlit AppTest"))
Tbl $s 40 92 $d @(170,230,110,370) 31 14 | Out-Null
Txt $s 40 444 880 44 "Versions are those installed in the project{'}s own virtual environment (.venv) at final validation. The tests were also run on Python 3.12.8 and on the oldest supported package versions. The system runs locally and is not deployed." 12.5 $K.grey | Out-Null

# ---- 8 Architecture ----
$s = NewSlide "System architecture" (Note 8)
function Node($s,$x,$y,$w,$h,$title,$sub,$line=$K.blue,$lw=1.25){
  $b = Rect $s $x $y $w $h $K.white $line $lw
  $b.TextFrame.WordWrap = -1; $b.TextFrame.MarginLeft = 5; $b.TextFrame.MarginRight = 5; $b.TextFrame.VerticalAnchor = 3
  $txt = $title; if($sub -ne ''){ $txt = $title + "`r" + $sub }
  SetText $b.TextFrame.TextRange $txt 12 $K.ink $false
  $b.TextFrame.TextRange.ParagraphFormat.Alignment = 2
  $b.TextFrame.TextRange.Paragraphs(1).Font.Bold = -1
  if($sub -ne ''){ $b.TextFrame.TextRange.Paragraphs(2).Font.Size = [single]11 }
  return $b
}
Txt $s 40 82 130 16 "Data" 12 $K.grey | Out-Null
Node $s 40 102 140 62 "Nassau_Candy_ Distributor.csv" "10,194 rows, read-only" $K.grey | Out-Null
Node $s 40 196 140 62 "config.py" "score weights, ship-mode suitability" $K.grey | Out-Null
Txt $s 205 82 160 16 "Loading and reference data" 12 $K.grey | Out-Null
Node $s 205 102 160 156 "route_core.py" "load_and_clean, validation, factories, product map, centroids, haversine" | Out-Null
Arrow $s 180 133 205 133 | Out-Null
Arrow $s 180 227 205 227 | Out-Null
Txt $s 395 82 200 16 "Calculation modules (modules/)" 12 $K.grey | Out-Null
$grp = Rect $s 395 102 200 316 $null $K.rule 1
$mods = @(@("scoring","route score"),@("route_analysis","route tables, KPIs"),@("optimization","LP with GLOP"),@("scenarios","what-if runs"),@("anomaly_detection","IQR and rules"),@("recommendations","rule-based"),@("reporting","report data"))
for($i=0;$i -lt 7;$i++){
  $ln = $K.blue; $lw2 = 1; $hyp = ($i -eq 2 -or $i -eq 3); if($hyp){ $ln = $K.amber; $lw2 = 1.75 }
  Node $s 405 (110+$i*43) 180 38 $mods[$i][0] $mods[$i][1] $ln $lw2 | Out-Null
}
Arrow $s 365 180 395 180 | Out-Null
Txt $s 625 82 160 16 "Interface" 12 $K.grey | Out-Null
$ifs = @(@("app.py","navigation, environment check"),@("ui/","filters, cached data, charts"),@("views/","eight Streamlit pages"))
for($i=0;$i -lt 3;$i++){ Node $s 625 (102+$i*70) 150 62 $ifs[$i][0] $ifs[$i][1] | Out-Null }
Arrow $s 595 180 625 150 | Out-Null
Txt $s 805 82 115 16 "User" 12 $K.grey | Out-Null
Node $s 805 172 115 62 "Web browser" "localhost" $K.grey | Out-Null
Arrow $s 775 205 805 205 | Out-Null
Node $s 625 340 295 56 "utils/report_generator.py" "PDF, Excel (9 sheets), CSV, ZIP" $K.teal | Out-Null
Arrow $s 585 380 625 370 | Out-Null
Txt $s 625 306 295 18 "Output" 12 $K.grey | Out-Null
$lg = Rect $s 40 432 22 10 $K.white $K.amber 1.75
Txt $s 70 428 400 18 "Amber outline: hypothetical simulation modules" 12 $K.amber | Out-Null
Txt $s 40 452 880 44 "Streamlit code appears only in app.py, ui/ and views/. All calculations are in route_core.py and modules/, so they can be tested without a browser." 13 $K.ink | Out-Null

# ---- 9 Preprocessing ----
$s = NewSlide "Data preprocessing" (Note 9)
$st = @("Locate and validate the CSV","Coerce Sales and Units to numbers","Drop invalid rows (duplicate Row ID, missing fields, value {<=} 0)","Trim text fields","Parse dates (day, month, year)","Keep raw lead time for display only (unreliable)","Map product to factory and state to centroid","Compute haversine distance; unknown location stays missing","Flag repeated Order ID + Product ID lines (kept)")
for($i=0;$i -lt 9;$i++){
  if($i -lt 5){ $x = 40 + $i*181; $y = 100 } else { $x = 40 + (8-$i+1)*181; $y = 206 }
  $b = Rect $s $x $y 156 78 $K.white $K.blue 1
  $b.TextFrame.WordWrap = -1; $b.TextFrame.MarginLeft = 8; $b.TextFrame.MarginRight = 6; $b.TextFrame.VerticalAnchor = 3
  SetText $b.TextFrame.TextRange (([string]($i+1)) + ".  " + $st[$i]) 12 $K.ink $false
  $b.TextFrame.TextRange.ParagraphFormat.Alignment = 1
  $b.TextFrame.TextRange.Characters(1,2).Font.Bold = -1; $b.TextFrame.TextRange.Characters(1,2).Font.Color.RGB = $K.teal
}
$ob = Rect $s 40 206 156 78 $K.white $K.teal 1.5; SText $ob "Cleaned order lines (one DataFrame)" 12 $K.ink $true 2 3 6
for($i=0;$i -lt 4;$i++){ Arrow $s (40+$i*181+156) 139 (40+($i+1)*181) 139 | Out-Null }
Arrow $s 842 178 842 206 | Out-Null
for($i=5;$i -lt 9;$i++){ $x = 40 + (8-$i+1)*181; Arrow $s $x 245 ($x-25) 245 | Out-Null }
Txt $s 40 316 880 50 "On the supplied file the pipeline reads 10,194 rows and returns 10,194 rows. None was removed, no location was unknown, and 3,018 repeated order-product lines were flagged." 15 $K.ink | Out-Null
Bullets $s 40 384 880 100 @("Flag, never delete: repeated lines and anomalies are marked, not removed.","Unknown is never zero: a missing location gives a missing distance and a Missing Geo flag.","The source CSV is never modified; a test compares it with its recorded SHA-256 hash.") 14 $K.ink 6 | Out-Null
