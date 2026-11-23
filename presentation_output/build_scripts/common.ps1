$ErrorActionPreference = 'Stop'
function RGB($r,$g,$b){ return [int]($r + 256*$g + 65536*$b) }
$K = @{
  navy  = (RGB 7 23 49);   navy2 = (RGB 14 40 77);  ink = (RGB 27 42 65);  muted = (RGB 91 107 127)
  light = (RGB 243 246 250); line = (RGB 217 225 234); white = (RGB 255 255 255)
  teal  = (RGB 18 168 160); tealD = (RGB 11 124 119); tealL = (RGB 226 245 243)
  blue  = (RGB 59 111 182); blueL = (RGB 232 239 249)
  amber = (RGB 184 112 0);  amberBg = (RGB 255 244 220); amberLn = (RGB 232 176 70); amberBar = (RGB 242 180 77)
  grey  = (RGB 233 237 242); red = (RGB 194 91 86); redL = (RGB 250 232 231)
}
$FONT = 'Segoe UI'
$ASSETS = 'D:\nassau-candy-route-efficiency\presentation_output\assets'

$TOK = [ordered]@{
 '{->}'=[string][char]0x2192; '{x}'=[string][char]0xD7; '{-}'=[string][char]0x2013; '{--}'=[string][char]0x2014
 '{.}'=[string][char]0xB7; '{<=}'=[string][char]0x2264; '{>=}'=[string][char]0x2265; '{2}'=[string][char]0xB2
 '{D}'=[string][char]0x394; '{phi}'=[string][char]0x3C6; '{lam}'=[string][char]0x3BB; '{sqrt}'=[string][char]0x221A
 '{s1}'=[string][char]0x2081; '{s2}'=[string][char]0x2082; '{S}'=[string][char]0x3A3; '{~}'=[string][char]0x2248
 "{'}"=[string][char]0x2019; '{minus}'=[string][char]0x2212; '{bull}'=[string][char]0x2022; '{USD}'='$'; '{check}'=[string][char]0x2713
 '{dot}'=[string][char]0x2022; '{lq}'=[string][char]0x201C; '{rq}'=[string][char]0x201D
}
function T($s){ foreach($kk in $TOK.Keys){ $s = $s.Replace($kk,$TOK[$kk]) }; return $s }

function Box($s,$x,$y,$w,$h,$fill,$line=$null,$round=0.06,$lw=1){
  $x=[single]$x;$y=[single]$y;$w=[single]$w;$h=[single]$h
  $type = 1; if($round -gt 0){ $type = 5 }
  $sh = $s.Shapes.AddShape($type,$x,$y,$w,$h)
  if($round -gt 0){ $sh.Adjustments.Item(1) = [single]$round }
  if($fill -eq $null){ $sh.Fill.Visible = 0 } else { $sh.Fill.Visible = -1; $sh.Fill.Solid(); $sh.Fill.ForeColor.RGB = $fill }
  if($line -ne $null){ $sh.Line.Visible = -1; $sh.Line.ForeColor.RGB = $line; $sh.Line.Weight = [single]$lw } else { $sh.Line.Visible = 0 }
  $sh.Shadow.Visible = 0
  return $sh
}
# text inside an existing shape
function SText($sh,$text,$size,$color,$bold=$false,$align=2,$anchor=3,$pad=6){
  $tf = $sh.TextFrame; $tf.WordWrap = -1; $tf.AutoSize = 0
  $tf.MarginLeft=$pad; $tf.MarginRight=$pad; $tf.MarginTop=3; $tf.MarginBottom=3
  $tf.VerticalAnchor = $anchor
  $r = $tf.TextRange; $r.Text = (T $text)
  $r.Font.Name=$FONT; $r.Font.Size=[single]$size; $r.Font.Color.RGB=$color; $r.Font.Bold = $(if($bold){-1}else{0})
  $r.ParagraphFormat.Alignment = $align
  return $sh
}
function Txt($s,$x,$y,$w,$h,$text,$size=12,$color=$K.ink,$bold=$false,$align=1,$anchor=1){
  $x=[single]$x;$y=[single]$y;$w=[single]$w;$h=[single]$h
  $tb = $s.Shapes.AddTextbox(1,$x,$y,$w,$h)
  $tf = $tb.TextFrame; $tf.WordWrap = -1; $tf.AutoSize = 0
  $tf.MarginLeft=0; $tf.MarginRight=0; $tf.MarginTop=0; $tf.MarginBottom=0
  $tb.Left=$x; $tb.Top=$y; $tb.Width=$w; $tb.Height=$h
  $tf.VerticalAnchor = $anchor
  $r = $tf.TextRange; $r.Text = (T $text)
  $r.Font.Name=$FONT; $r.Font.Size=[single]$size; $r.Font.Color.RGB=$color; $r.Font.Bold = $(if($bold){-1}else{0})
  $r.ParagraphFormat.Alignment = $align
  return $tb
}
function BoldPart($tb,$sub,$color=$null){
  $f = $tb.TextFrame.TextRange.Find((T $sub))
  if($f -ne $null){ $f.Font.Bold = -1; if($color -ne $null){ $f.Font.Color.RGB = $color } }
}
function Bullets($s,$x,$y,$w,$h,$items,$size=12,$color=$K.ink,$after=4,$bcolor=$null){
  $txt = ($items | ForEach-Object { T $_ }) -join "`r"
  $tb = Txt $s $x $y $w $h $txt $size $color
  $r = $tb.TextFrame.TextRange
  $r.ParagraphFormat.Bullet.Visible = -1
  $r.ParagraphFormat.Bullet.Character = 8226
  if($bcolor -ne $null){ $r.ParagraphFormat.Bullet.UseTextColor = 0; $r.ParagraphFormat.Bullet.Font.Color.RGB = $bcolor }
  $r.ParagraphFormat.SpaceAfter = $after
  $tb.TextFrame.Ruler.Levels.Item(1).FirstMargin = 0
  $tb.TextFrame.Ruler.Levels.Item(1).LeftMargin = 13
  return $tb
}
function Arrow($s,$x1,$y1,$x2,$y2,$color=$K.muted,$w=1.5){
  $x1=[single]$x1;$y1=[single]$y1;$x2=[single]$x2;$y2=[single]$y2;$w=[single]$w
  $c = $s.Shapes.AddConnector(1,$x1,$y1,$x2,$y2)
  try { $c.Line.ForeColor.RGB = [int]$color; $c.Line.Weight = [single]$w; $c.Line.EndArrowheadStyle = 2 } catch { throw ('Arrow fail color=' + $color + ' type=' + $(if($color -ne $null){$color.GetType().Name}) + ' w=' + $w) }
  return $c
}
function Badge($s,$x,$y,$w,$text,$kind='hyp',$h=20,$size=10){
  switch($kind){
    'hyp'    { $f=$K.amberBg; $l=$K.amberLn; $t=$K.amber }
    'calc'   { $f=$K.blueL;   $l=$K.blue;    $t=$K.blue }
    'data'   { $f=$K.tealL;   $l=$K.teal;    $t=$K.tealD }
    'assume' { $f=$K.grey;    $l=$K.muted;   $t=$K.muted }
    'dark'   { $f=$K.navy2;   $l=$K.teal;    $t=$K.teal }
  }
  $b = Box $s $x $y $w $h $f $l 0.5 1
  SText $b $text $size $t $true 2 3 4 | Out-Null
  return $b
}
function Pic($s,$file,$x,$y,$w=-1,$h=-1,$alt=''){
  $x=[single]$x;$y=[single]$y;$w=[single]$w;$h=[single]$h
  $p = $s.Shapes.AddPicture((Join-Path $ASSETS $file),0,-1,$x,$y,-1,-1)
  $p.LockAspectRatio = -1
  if($w -gt 0){ $p.Width = $w } elseif($h -gt 0){ $p.Height = $h }
  $p.Left = $x; $p.Top = $y
  if($alt -ne ''){ $p.AlternativeText = $alt }
  return $p
}
function Frame($sh,$color=$null,$w=1){ if($color -eq $null){ $color=$K.line }; $sh.Line.Visible=-1; $sh.Line.ForeColor.RGB=$color; $sh.Line.Weight=$w }

$script:Pres = $null
function NewSlide($title,$kicker,$notes,$dark=$false){
  $idx = $script:Pres.Slides.Count + 1
  $s = $script:Pres.Slides.AddSlide($idx,$script:Pres.SlideMaster.CustomLayouts.Item(6))
  if($dark){ $s.FollowMasterBackground = 0; $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB = $K.navy }
  $t = $s.Shapes.Title
  $t.Left=40; $t.Top=40; $t.Width=880; $t.Height=44
  $tf = $t.TextFrame; $tf.WordWrap=-1; $tf.AutoSize=0; $tf.VerticalAnchor=1
  $tf.MarginLeft=0; $tf.MarginRight=0; $tf.MarginTop=0; $tf.MarginBottom=0
  $r = $tf.TextRange; $r.Text = (T $title); $r.Font.Name=$FONT; $r.Font.Size=28; $r.Font.Bold=-1
  $r.Font.Color.RGB = $(if($dark){$K.white}else{$K.navy}); $r.ParagraphFormat.Alignment = 1
  if($kicker -ne ''){
    $b = Box $s 40 22 22 4 $K.teal $null 0
    $kcol = $K.tealD; if($dark){ $kcol = $K.teal }; $kk = Txt $s 68 16 700 16 (T $kicker) 10.5 $kcol $true; $kk.TextFrame.TextRange.Font.Size = [single]10.5
    $kk.Name = 'Kicker'
  }
  if(-not $dark){
    $ln = $s.Shapes.AddLine(40,506,920,506); $ln.Line.ForeColor.RGB=$K.line; $ln.Line.Weight=0.75; $ln.Name='FooterRule'
    $f = Txt $s 40 512 700 14 "Supply Chain Route Analytics and Optimization System  {.}  K S Mohamed Adnan Ali" 9 $K.muted; $f.Name='FooterText'
    $n = Txt $s 860 512 60 14 "" 9 $K.muted $false 3; $n.Name='SlideNumber'
    $n.TextFrame.TextRange.InsertSlideNumber() | Out-Null
    $n.TextFrame.TextRange.Font.Size = 9; $n.TextFrame.TextRange.Font.Name=$FONT; $n.TextFrame.TextRange.Font.Color.RGB=$K.muted
    $n.TextFrame.TextRange.ParagraphFormat.Alignment = 3
  }
  if($notes -ne ''){ $s.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = (T $notes) }
  return $s
}
