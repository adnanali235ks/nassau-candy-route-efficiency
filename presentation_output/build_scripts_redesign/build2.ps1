$ErrorActionPreference='Stop'
$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$HERE\common2.ps1"
$NOTES = Get-Content "$HERE\notes_old.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$OUTDIR = 'D:\nassau-candy-route-efficiency\presentation_output'
$app = New-Object -ComObject PowerPoint.Application
$script:Pres = $app.Presentations.Add(0)
$script:Pres.PageSetup.SlideWidth = 960; $script:Pres.PageSetup.SlideHeight = 540
try {
  . "$HERE\slides_a.ps1"
  . "$HERE\slides_b.ps1"
  $bad = @()
  foreach($sl in $script:Pres.Slides){
    foreach($sh in $sl.Shapes){
      if($sh.HasTextFrame -and $sh.TextFrame.HasText){
        $tr = $sh.TextFrame.TextRange
        if($tr.BoundHeight -gt ($sh.Height + 2) -or $tr.BoundWidth -gt ($sh.Width + 2)){
          $bad += ("slide {0}: '{1}' text {2:N0}x{3:N0} > box {4:N0}x{5:N0}" -f $sl.SlideIndex, $tr.Text.Substring(0,[math]::Min(40,$tr.Text.Length)), $tr.BoundWidth,$tr.BoundHeight,$sh.Width,$sh.Height)
        }
      }
    }
  }
  if(Test-Path "$HERE\overflow2.txt"){ Remove-Item "$HERE\overflow2.txt" }
  if($bad.Count -gt 0){ $bad | Set-Content "$HERE\overflow2.txt" -Encoding UTF8 }
  "overflow items: " + $bad.Count
  $script:Pres.SaveAs("$OUTDIR\Supply_Chain_Internship_Presentation_Redesigned.pptx", 24)
  $script:Pres.SaveAs("$OUTDIR\Supply_Chain_Internship_Presentation_Redesigned.pdf", 32)
  $dir = "$HERE\r2"; if(Test-Path $dir){ Remove-Item $dir -Recurse -Force }; New-Item -ItemType Directory $dir | Out-Null
  $script:Pres.Export($dir,"PNG",1600,900)
  "slides: " + $script:Pres.Slides.Count
} catch { Write-Host ("ERR: " + $_.Exception.Message); Write-Host $_.ScriptStackTrace } finally {
  $script:Pres.Close(); $app.Quit()
}
