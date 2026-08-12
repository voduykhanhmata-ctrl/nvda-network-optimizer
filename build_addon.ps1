[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputPath = Join-Path $projectRoot "NetworkOptimizer-1.1.1.nvda-addon"
$temporaryZipPath = Join-Path $projectRoot "NetworkOptimizer-1.1.1.zip"

if (Test-Path -LiteralPath $outputPath) {
	Remove-Item -LiteralPath $outputPath -Force
}
if (Test-Path -LiteralPath $temporaryZipPath) {
	Remove-Item -LiteralPath $temporaryZipPath -Force
}

Compress-Archive -Path @(
	(Join-Path $projectRoot "manifest.ini"),
	(Join-Path $projectRoot "globalPlugins"),
	(Join-Path $projectRoot "doc")
) -DestinationPath $temporaryZipPath -CompressionLevel Optimal -ErrorAction Stop

Move-Item -LiteralPath $temporaryZipPath -Destination $outputPath

Write-Output "Created $outputPath"
