# Reporte de calidad para un proyecto externo.
# Uso:
#   pwsh tools/quality.ps1 -Project C:\work\repo -Base develop
#   pwsh tools/quality.ps1 -Project C:\work\repo -Base develop -Fix
#   pwsh tools/quality.ps1 -Project C:\work\repo -Base develop -Json
#   pwsh tools/quality.ps1 -Project C:\work\repo          # proyecto completo
param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [string]$Base,

    [switch]$Fix,

    [switch]$Json
)

$arguments = @("--project", $Project, "--validate")
if ($Base) {
    $arguments += @("--base", $Base)
}
if ($Fix) {
    $arguments += "--fix"
}
if ($Json) {
    $arguments += "--json"
}

& python (Join-Path $PSScriptRoot "lint.py") @arguments
exit $LASTEXITCODE
