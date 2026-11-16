# Instala dependencias y activa el hook de pre-commit.
# Uso: pwsh tools/setup.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$required = "python", "ruff", "mypy", "node", "golangci-lint", "mvn"
$missing = $required | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }
if ($missing) {
    Write-Warning "Faltan herramientas: $($missing -join ', '). Revisa el README."
}

git config core.hooksPath .githooks
Write-Host "Hook activo: .githooks/pre-commit"

foreach ($folder in "typescript-teacher", "React-teacher") {
    Push-Location $folder
    npm install --no-fund --no-audit
    Pop-Location
}

Push-Location Java-teacher
mvn -q -B compile
Pop-Location

Write-Host "Listo. Siguiente paso: python tools/lint.py"
