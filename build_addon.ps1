[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $projectRoot "manifest.ini"
$manifestVersionLine = Get-Content -LiteralPath $manifestPath |
	Where-Object { $_ -match '^version\s*=' } |
	Select-Object -First 1
if (-not $manifestVersionLine -or $manifestVersionLine -notmatch '^version\s*=\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)\s*$') {
	throw "Could not read a valid add-on version from manifest.ini."
}
$addonVersion = $Matches[1]
$outputPath = Join-Path $projectRoot "NetworkOptimizer-$addonVersion.nvda-addon"
$temporaryZipPath = Join-Path $projectRoot "NetworkOptimizer-$addonVersion.zip"
$translationCompiler = Join-Path $projectRoot "compile_translations.py"
$translationSource = Join-Path $projectRoot "locale\vi\LC_MESSAGES\nvda.po"
$translationBinary = Join-Path $projectRoot "locale\vi\LC_MESSAGES\nvda.mo"

$python = @(
	Get-Command python -CommandType Application -ErrorAction SilentlyContinue |
	Where-Object {
		$_.Path -and
		(Test-Path -LiteralPath $_.Path) -and
		$_.Path -notlike "*\WindowsApps\*"
	} |
	Select-Object -First 1
)
if ($python.Count -gt 0) {
	& $python[0].Path $translationCompiler
	if ($LASTEXITCODE -ne 0) {
		throw "Could not compile the Vietnamese translation."
	}
}
elseif (-not (Test-Path -LiteralPath $translationBinary) -or
	((Get-Item -LiteralPath $translationSource).LastWriteTimeUtc -gt (Get-Item -LiteralPath $translationBinary).LastWriteTimeUtc)) {
	throw "Python was not found. Install Python and run compile_translations.py before building the add-on."
}
else {
	Write-Warning "Python was not found; packaging the existing Vietnamese translation."
}

if (Test-Path -LiteralPath $outputPath) {
	Remove-Item -LiteralPath $outputPath -Force
}
if (Test-Path -LiteralPath $temporaryZipPath) {
	Remove-Item -LiteralPath $temporaryZipPath -Force
}

Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop

$manifestFile = Get-Item -LiteralPath $manifestPath
$licenseFile = Get-Item -LiteralPath (Join-Path $projectRoot "LICENSE")
$filesToArchive = @($manifestFile, $licenseFile)
foreach ($folderName in @("globalPlugins", "doc", "locale")) {
	$folderPath = Join-Path $projectRoot $folderName
	$filesToArchive += Get-ChildItem -LiteralPath $folderPath -Recurse -File |
		Where-Object {
			$_.Extension -ne ".pyc" -and
			$_.FullName -notmatch "[\\/]__pycache__[\\/]"
		}
}

$archive = [System.IO.Compression.ZipFile]::Open(
	$temporaryZipPath,
	[System.IO.Compression.ZipArchiveMode]::Create
)
try {
	foreach ($file in $filesToArchive | Sort-Object FullName) {
		$entryPath = $file.FullName.Substring($projectRoot.Length).TrimStart("\", "/").Replace("\", "/")
		[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
			$archive,
			$file.FullName,
			$entryPath,
			[System.IO.Compression.CompressionLevel]::Optimal
		) | Out-Null
	}
}
finally {
	$archive.Dispose()
}

Move-Item -LiteralPath $temporaryZipPath -Destination $outputPath

Write-Output "Created $outputPath"
