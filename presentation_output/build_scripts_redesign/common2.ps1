$ErrorActionPreference = 'Stop'
function RGB($r,$g,$b){ return [int]($r + 256*$g + 65536*$b) }
$K = @{
  ink=(RGB 43 47 54); navy=(RGB 7 23 49); head=(RGB 20 38 66); blue=(RGB 61 90 128); teal=(RGB 27 138 138)
  grey=(RGB 110 117 128); rule=(RGB 205 210 216); white=(RGB 255 255 255); pale=(RGB 150 168 192)
  amber=(RGB 170 100 0); amberFill=(RGB 244 214 150); data=(RGB 120 134 152)
}
$FONT = 'Segoe UI'; $MATH = 'Cambria Math'
$ASSETS = 'D:\nassau-candy-route-efficiency\presentation_output\assets'
$TOK = [ordered]@{
 '{->}'=[string][char]0x2192; '{x}'=[string][char]0xD7; '{-}'=[string][char]0x2013; '{--}'=[string][char]0x2014
 '{.}'=[string][char]0xB7; '{<=}'=[string][char]0x2264; '{>=}'=[string][char]0x2265; '{sq}'=[string][char]0xB2
 '{D}'=[string][char]0x394; '{phi}'=[string][char]0x3C6; '{lam}'=[string][char]0x3BB; '{sqrt}'=[string][char]0x221A
 '{S}'=[string][char]0x3A3; "{'}"=[string][char]0x2019; '{minus}'=[string][char]0x2212; '{USD}'='$'
 '{in}'=[string][char]0x2208; '{lq}'=[string][char]0x201C; '{rq}'=[string][char]0x201D
}
function T($s){ foreach($kk in $TOK.Keys){ $s = $s.Replace($kk,$TOK[$kk]) }; return $s }
# parse _{sub} and ^{sup} markers (after token replacement)
function ParseSub($t){
  $clean = New-Object System.Text.StringBuilder; $marks = @(); $i = 0
  while($i -lt $t.Length){
    $ch = $t[$i]
    if(($ch -eq '_' -or $ch -eq '^') -and ($i+1) -lt $t.Length -and $t[$i+1] -eq '{'){
      $j = $t.IndexOf('}',$i); $inner = $t.Substring($i+2,$j-$i-2)
      $marks += ,@($clean.Length,$inner.Length,[string]$ch); [void]$clean.Append($inner); $i = $j + 1
    } else { [void]$clean.Append($ch); $i++ }
  }
  return @{ text = $clean.ToString(); marks = $marks }
}
function SetText($tr,$raw,$size,$color,$bold=$false,$font=$FONT){
  $p = ParseSub (T $raw)
  $tr.Text = $p.text
  $tr.Font.Name = $font; $tr.Font.Size = [single]$size; $tr.Font.Color.RGB = [int]$color
  $tr.Font.Bold = $(if($bold){-1}else{0})
  foreach($m in $p.marks){
    $r = $tr.Characters([int]($m[0]+1),[int]$m[1])
    if($m[2] -eq '_'){ $r.Font.Subscript = -1 } else { $r.Font.Superscript = -1 }
  }
}
function Txt($s,$x,$y,$w,$h,$text,$size=14,$color=$K.ink,$bold=$false,$align=1,$anchor=1,$font=$FONT){
  $tb = $s.Shapes.AddTextbox(1,[single]$x,[single]$y,[single]$w,[single]$h)
  $tf = $tb.TextFrame; $tf.WordWrap = -1; $tf.AutoSize = 0
  $tf.MarginLeft=0; $tf.MarginRight=0; $tf.MarginTop=0; $tf.MarginBottom=0
  $tb.Left=[single]$x; $tb.Top=[single]$y; $tb.Width=[single]$w; $tb.Height=[single]$h
  $tf.VerticalAnchor = $anchor
  SetText $tf.TextRange $text $size $color $bold $font
  $tf.TextRange.ParagraphFormat.Alignment = $align
  return $tb
}
function Bullets($s,$x,$y,$w,$h,$items,$size=14,$color=$K.ink,$after=6,$numbered=$false){
  $txt = ($items | ForEach-Object { $_ }) -join "`r"
  $tb = Txt $s $x $y $w $h $txt $size $color
  $r = $tb.TextFrame.TextRange
  $r.ParagraphFormat.Bullet.Visible = -1
  if($numbered){ $r.ParagraphFormat.Bullet.Type = 2; $r.ParagraphFormat.Bullet.Style = 3; $r.ParagraphFormat.Bullet.StartValue = 1 }
  else { $r.ParagraphFormat.Bullet.Character = 8226 }
  $r.ParagraphFormat.Bullet.UseTextColor = 0; $r.ParagraphFormat.Bullet.Font.Color.RGB = $K.teal
  $r.ParagraphFormat.SpaceAfter = [single]$after
  $tb.TextFrame.Ruler.Levels.Item(1).FirstMargin = 0
  $tb.TextFrame.Ruler.Levels.Item(1).LeftMargin = $(if($numbered){22}else{16})
  return $tb
}
function Rect($s,$x,$y,$w,$h,$fill,$line=$null,$lw=1){
  $sh = $s.Shapes.AddShape(1,[single]$x,[single]$y,[single]$w,[single]$h)
  if($fill -eq $null){ $sh.Fill.Visible = 0 } else { $sh.Fill.Visible = -1; $sh.Fill.Solid(); $sh.Fill.ForeColor.RGB = [int]$fill }
  if($line -ne $null){ $sh.Line.Visible = -1; $sh.Line.ForeColor.RGB = [int]$line; $sh.Line.Weight = [single]$lw } else { $sh.Line.Visible = 0 }
  $sh.Shadow.Visible = 0
  return $sh
}
function SText($sh,$text,$size,$color,$bold=$false,$align=2,$anchor=3,$pad=6){
  $tf = $sh.TextFrame; $tf.WordWrap = -1; $tf.AutoSize = 0
  $tf.MarginLeft=$pad; $tf.MarginRight=$pad; $tf.MarginTop=3; $tf.MarginBottom=3; $tf.VerticalAnchor = $anchor
  SetText $tf.TextRange $text $size $color $bold
  $tf.TextRange.ParagraphFormat.Alignment = $align
}
function Arrow($s,$x1,$y1,$x2,$y2,$color=$K.grey,$w=1.25){
  $c1 = $s.Shapes.AddConnector(1,[single]$x1,[single]$y1,[single]$x2,[single]$y2)
  $c1.Line.ForeColor.RGB = [int]$color; $c1.Line.Weight = [single]$w; $c1.Line.EndArrowheadStyle = 2
  return $c1
}
function HLine($s,$x1,$y,$x2,$color=$K.rule,$w=0.75){
  $l = $s.Shapes.AddLine([single]$x1,[single]$y,[single]$x2,[single]$y); $l.Line.ForeColor.RGB = [int]$color; $l.Line.Weight = [single]$w; return $l
}
function Pic($s,$file,$x,$y,$w=-1,$h=-1,$alt=''){
  $p = $s.Shapes.AddPicture((Join-Path $ASSETS $file),0,-1,[single]$x,[single]$y,-1,-1)
  $p.LockAspectRatio = -1
  if($w -gt 0){ $p.Width = [single]$w } elseif($h -gt 0){ $p.Height = [single]$h }
  $p.Left = [single]$x; $p.Top = [single]$y
  if($alt -ne ''){ $p.AlternativeText = $alt }
  return $p
}
function Frame($sh,$color=$null,$w=0.75){ if($color -eq $null){ $color=$K.rule }; $sh.Line.Visible=-1; $sh.Line.ForeColor.RGB=[int]$color; $sh.Line.Weight=[single]$w }
function Tbl($s,$x,$y,$data,$colW,$rowH,$fs=13,$aligns=$null,$mathCols=@(),$boldRows=@(),$hdr=$true){
  $nr = $data.Count; $nc = $colW.Count; $w = 0; foreach($cw in $colW){ $w += $cw }
  $sh = $s.Shapes.AddTable($nr,$nc,[single]$x,[single]$y,[single]$w,[single]($rowH*$nr))
  $tb = $sh.Table
  $tb.ApplyStyle('{2D5ABB26-0587-4C30-8999-92F81FD0307C}')
  for($c2=1;$c2 -le $nc;$c2++){ $tb.Columns.Item($c2).Width = [single]$colW[$c2-1] }
  for($r2=1;$r2 -le $nr;$r2++){
    $tb.Rows.Item($r2).Height = [single]$rowH
    for($c2=1;$c2 -le $nc;$c2++){
      $cell = $tb.Cell($r2,$c2)
      $cell.Shape.Fill.Visible = 0
      $tf = $cell.Shape.TextFrame; $tf.MarginLeft = 4; $tf.MarginRight = 6; $tf.MarginTop = 2; $tf.MarginBottom = 2; $tf.VerticalAnchor = 3
      $isH = ($hdr -and $r2 -eq 1); $fnt = $FONT; if($mathCols -contains $c2 -and -not $isH){ $fnt = $MATH }
      $col = $K.ink; if($isH){ $col = $K.blue }
      SetText $tf.TextRange $data[$r2-1][$c2-1] $fs $col ($isH -or ($boldRows -contains $r2)) $fnt
      if($aligns -ne $null){ $tf.TextRange.ParagraphFormat.Alignment = $aligns[$c2-1] }
      foreach($bd in 1,2,4){ try { $cell.Borders.Item($bd).Visible = 0 } catch {} }
      $bb = $cell.Borders.Item(3); $bb.Visible = -1; $bb.ForeColor.RGB = $(if($isH){$K.grey}else{$K.rule}); $bb.Weight = $(if($isH){[single]1.25}else{[single]0.5})
    }
  }
  return $sh
}
$script:Pres = $null
function NewSlide($title,$notes,$dark=$false){
  $idx = $script:Pres.Slides.Count + 1
  $s = $script:Pres.Slides.AddSlide($idx,$script:Pres.SlideMaster.CustomLayouts.Item(6))
  if($dark){ $s.FollowMasterBackground = 0; $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB = $K.navy }
  $t = $s.Shapes.Title
  $t.Left=40; $t.Top=28; $t.Width=880; $t.Height=40
  $tf = $t.TextFrame; $tf.WordWrap=-1; $tf.AutoSize=0; $tf.VerticalAnchor=1
  $tf.MarginLeft=0; $tf.MarginRight=0; $tf.MarginTop=0; $tf.MarginBottom=0
  SetText $tf.TextRange $title 28 $(if($dark){$K.white}else{$K.head}) $true
  $tf.TextRange.ParagraphFormat.Alignment = 1
  if(-not $dark){
    $n = Txt $s 860 514 60 14 "" 10 $K.grey $false 3; $n.Name = 'SlideNumber'
    $n.TextFrame.TextRange.InsertSlideNumber() | Out-Null
    $n.TextFrame.TextRange.Font.Size = [single]10; $n.TextFrame.TextRange.Font.Name = $FONT; $n.TextFrame.TextRange.Font.Color.RGB = $K.grey
    $n.TextFrame.TextRange.ParagraphFormat.Alignment = 3
  }
  if($notes -ne ''){ $s.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = $notes }
  return $s
}
function Tag($s,$text,$x=560,$w=360){ $t = Txt $s $x 38 $w 18 $text 13 $K.amber $false 3; return $t }
