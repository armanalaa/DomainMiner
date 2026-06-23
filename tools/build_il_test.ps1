$ErrorActionPreference = "Stop"

function RGB($r, $g, $b) {
    return $r + ($g * 256) + ($b * 65536)
}

function Set-RichSpan($cell, [int]$start, [int]$length, [string]$fontName, [int]$color, [bool]$bold = $false) {
    if ($length -le 0) { return }
    $chars = $cell.Characters($start, $length)
    $chars.Font.Name = $fontName
    $chars.Font.Color = $color
    $chars.Font.Bold = $bold
}

function Test-Overlap($ranges, [int]$start0, [int]$end0) {
    foreach ($range in $ranges) {
        if ($start0 -lt $range.End -and $end0 -gt $range.Start) {
            return $true
        }
    }
    return $false
}

function Color-CodeBlock($cell, [string]$fullText, [string]$code) {
    $baseIndex = $fullText.IndexOf($code)
    if ($baseIndex -lt 0) { return }

    $codeStart1 = $baseIndex + 1
    Set-RichSpan $cell $codeStart1 $code.Length "Courier New" (RGB 31 41 55)

    $stringRanges = @()
    foreach ($m in [regex]::Matches($code, '"(?:[^"\\]|\\.)*"')) {
        $stringRanges += [pscustomobject]@{ Start = $m.Index; End = $m.Index + $m.Length }
        Set-RichSpan $cell ($codeStart1 + $m.Index) $m.Length "Courier New" (RGB 22 101 52)
    }

    foreach ($m in [regex]::Matches($code, '\b\d+(?:\.\d+)?\b')) {
        if (-not (Test-Overlap $stringRanges $m.Index ($m.Index + $m.Length))) {
            Set-RichSpan $cell ($codeStart1 + $m.Index) $m.Length "Courier New" (RGB 126 34 206)
        }
    }

    foreach ($m in [regex]::Matches($code, '\b(in)\b')) {
        if (-not (Test-Overlap $stringRanges $m.Index ($m.Index + $m.Length))) {
            Set-RichSpan $cell ($codeStart1 + $m.Index) $m.Length "Courier New" (RGB 190 24 93) $true
        }
    }

    foreach ($m in [regex]::Matches($code, '\b(print|len|str|append|sort)\b')) {
        if (-not (Test-Overlap $stringRanges $m.Index ($m.Index + $m.Length))) {
            Set-RichSpan $cell ($codeStart1 + $m.Index) $m.Length "Courier New" (RGB 37 99 235) $true
        }
    }

    foreach ($m in [regex]::Matches($code, '==|!=|\+|-|\*\*|\*|=|\[|\]|\{|\}|\(|\)|:|,|\.')) {
        if (-not (Test-Overlap $stringRanges $m.Index ($m.Index + $m.Length))) {
            Set-RichSpan $cell ($codeStart1 + $m.Index) $m.Length "Courier New" (RGB 185 28 28)
        }
    }
}

function Style-CodeTokens($cell, [string[]]$tokens) {
    $text = [string]$cell.Value2
    foreach ($token in $tokens) {
        $idx = $text.IndexOf($token)
        while ($idx -ge 0) {
            Set-RichSpan $cell ($idx + 1) $token.Length "Courier New" (RGB 31 41 55)
            foreach ($m in [regex]::Matches($token, '\b\d+(?:\.\d+)?\b|False|True|KeyError')) {
                Set-RichSpan $cell ($idx + 1 + $m.Index) $m.Length "Courier New" (RGB 126 34 206)
            }
            $idx = $text.IndexOf($token, $idx + $token.Length)
        }
    }
}

$template = "H:\Other computers\My PC\San Raffaele\I Corsi\Modello_Test_25-26.xls"
$outputDir = Join-Path (Get-Location) "outputs"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$output = Join-Path $outputDir "Il Test.xlsx"
if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output -Force }

$lesson = "Operatori e Applicazioni Pratiche dei Dizionari in Python"

$items = @(
    @{
        Numero = 1
        Paragrafo = "Introduzione ai Dizionari in Python"
        Difficolta = 1
        Corretta = 1
        Code = @'
tariffe = {"base": 12, "extra": 5, "base": 15}
print(len(tariffe), tariffe["base"])
'@
        Domanda = "Osserva il programma seguente e considera che un dizionario non può contenere due chiavi uguali:`n`n{0}`n`nQuale output viene prodotto:" 
        Risposte = @(
            "stampa 2 15",
            "stampa 3 12",
            "stampa 3 15",
            "genera KeyError"
        )
        Tokens = @("2 15", "3 12", "3 15", "KeyError")
    },
    @{
        Numero = 2
        Paragrafo = "Introduzione ai Dizionari in Python"
        Difficolta = 2
        Corretta = 2
        Code = @'
righe = {"prima": ["A", "B"], "seconda": ["C"]}
righe["prima"].append("D")
print(righe["prima"], len(righe))
'@
        Domanda = "Nel programma seguente un valore del dizionario è una lista modificabile:`n`n{0}`n`nQuale output viene prodotto:"
        Risposte = @(
            "stampa ['A', 'B'] 2",
            "stampa ['A', 'B', 'D'] 2",
            "stampa ['A', 'B', 'D'] 3",
            "genera KeyError"
        )
        Tokens = @("['A', 'B'] 2", "['A', 'B', 'D'] 2", "['A', 'B', 'D'] 3", "KeyError")
    },
    @{
        Numero = 3
        Paragrafo = "Valori calcolati e dizionari nidificati"
        Difficolta = 3
        Corretta = 3
        Code = @'
inizio = 4
scheda = {
    "codice": "P" + str(inizio * 3),
    "intervallo": {"min": inizio - 1, "max": inizio + 5},
    "ampiezza": (inizio + 5) - (inizio - 1)
}
inizio = 10
print(scheda["codice"], scheda["intervallo"]["max"], scheda["ampiezza"])
'@
        Domanda = "Nel programma seguente alcuni valori del dizionario sono calcolati e uno è un dizionario annidato:`n`n{0}`n`nQuale output viene prodotto:"
        Risposte = @(
            "stampa P30 15 6",
            "stampa P12 15 6",
            "stampa P12 9 6",
            "stampa P12 9 12"
        )
        Tokens = @("P30 15 6", "P12 15 6", "P12 9 6", "P12 9 12")
    },
    @{
        Numero = 4
        Paragrafo = "Operatori Principali e Accesso ai Valori nei Dizionari"
        Difficolta = 4
        Corretta = 4
        Code = @'
a = {"x": [1, 2], "y": 3}
b = {"y": 3, "x": [2, 1]}
print(a == b)
a["x"].sort(reverse=True)
print(a == b)
'@
        Domanda = "Osserva il confronto tra due dizionari: l'ordine delle chiavi non conta, ma il contenuto associato alle chiavi sì:`n`n{0}`n`nQuale output viene prodotto:"
        Risposte = @(
            "stampa True e poi True",
            "stampa True e poi False",
            "stampa False e poi False",
            "stampa False e poi True"
        )
        Tokens = @("True", "False")
    },
    @{
        Numero = 5
        Paragrafo = "Operatori Principali e Accesso ai Valori nei Dizionari"
        Difficolta = 5
        Corretta = 2
        Code = @'
agenda = {}
agenda["lun"] = ["analisi"]
agenda["mar"] = ["reti"]
agenda["lun"] = agenda["lun"] + ["python"]
print(agenda["lun"][1], "ven" in agenda, len(agenda))
'@
        Domanda = "Il programma seguente costruisce un dizionario passo dopo passo, aggiorna una chiave esistente e poi accede a un elemento della lista salvata come valore:`n`n{0}`n`nQuale output viene prodotto:"
        Risposte = @(
            "stampa analisi False 2",
            "stampa python False 2",
            "stampa python True 2",
            "stampa python False 3"
        )
        Tokens = @("analisi False 2", "python False 2", "python True 2", "python False 3")
    }
)

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    $wb = $excel.Workbooks.Open($template)
    $ws = $wb.Worksheets.Item("Modello_Test")

    $wb.SaveAs($output, 51)

    $used = $ws.Range("A1:J194")
    $used.Interior.Color = RGB 255 255 255
    $used.Font.Color = RGB 0 0 0

    $ws.Range("A2:J6").ClearContents()
    $ws.Range("A2:J6").Interior.Color = RGB 255 255 255
    $ws.Range("A2:J6").WrapText = $true
    $ws.Range("A2:J6").VerticalAlignment = -4160

    for ($i = 0; $i -lt $items.Count; $i++) {
        $row = 2 + $i
        $item = $items[$i]
        $questionText = [string]::Format($item.Domanda, $item.Code.TrimEnd())
        $values = @(
            $item.Numero,
            $questionText,
            $item.Risposte[0],
            $item.Risposte[1],
            $item.Risposte[2],
            $item.Risposte[3],
            $item.Corretta,
            $lesson,
            $item.Paragrafo,
            $item.Difficolta
        )
        for ($c = 1; $c -le 10; $c++) {
            $cell = $ws.Cells.Item($row, $c)
            if ($c -in @(1, 7, 10)) {
                $cell.Value2 = [int]$values[$c - 1]
            }
            else {
                $cell.Value2 = [string]$values[$c - 1]
            }
            $cell.Interior.Color = RGB 255 255 255
            $cell.WrapText = $true
            $cell.VerticalAlignment = -4160
        }
        Color-CodeBlock $ws.Cells.Item($row, 2) $questionText $item.Code.TrimEnd()
        for ($c = 3; $c -le 6; $c++) {
            Style-CodeTokens $ws.Cells.Item($row, $c) $item.Tokens
        }
    }

    $ws.Range("A1:J6").Borders.LineStyle = 1
    $ws.Range("A1:J6").Borders.Color = RGB 217 217 217
    $ws.Range("B2:F6").Font.Size = 10
    $ws.Range("H2:I6").Font.Size = 10
    $ws.Range("B2:B6").ColumnWidth = 65
    $ws.Range("C2:F6").ColumnWidth = 28
    $ws.Range("H:H").ColumnWidth = 38
    $ws.Range("I:I").ColumnWidth = 42
    $ws.Range("A:A").ColumnWidth = 14
    $ws.Range("G:G").ColumnWidth = 18
    $ws.Range("J:J").ColumnWidth = 14
    $ws.Range("A2:A6").HorizontalAlignment = -4108
    $ws.Range("G2:G6").HorizontalAlignment = -4108
    $ws.Range("J2:J6").HorizontalAlignment = -4108
    $ws.Range("2:6").Rows.AutoFit() | Out-Null

    foreach ($table in @($ws.ListObjects)) {
        if ($table.Name -eq "IlTest") { $table.Delete() }
    }
    $listObject = $ws.ListObjects.Add(1, $ws.Range("A1:J6"), $null, 1)
    $listObject.Name = "IlTest"
    $listObject.TableStyle = ""
    $ws.Range("A1:J6").Interior.Color = RGB 255 255 255

    $wb.Save()
}
finally {
    if ($wb) { $wb.Close($true) | Out-Null }
    $excel.Quit() | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

Write-Output $output
