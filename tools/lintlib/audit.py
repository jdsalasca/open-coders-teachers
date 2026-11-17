"""Auditoria de seguridad, dependencias y mutation testing."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

from lintlib.common import LANGS, ROOT, Command, Lang, root_command, run, show

AUDIT: dict[str, Command] = {
    "typescript": Command(["npm", "audit", "--audit-level=high"]),
    "react": Command(["npm", "audit", "--audit-level=high"]),
    "go": Command(["govulncheck", "./..."]),
}

MUTATION: dict[str, Command] = {
    "java": Command(
        ["mvn", "-q", "-B", "test-compile", "pitest:mutationCoverage"],
        requires="pom.xml",
    ),
    "react": Command(["stryker", "run"], requires="stryker.conf.json"),
    "typescript": Command(["stryker", "run"], requires="stryker.conf.json"),
}


def security(langs: list[str]) -> int:
    """Secretos, patrones inseguros y dependencias vulnerables."""
    status = 0

    print("\n== secretos (gitleaks) ==")
    report = Path(tempfile.gettempdir()) / f"gitleaks-{os.getpid()}.json"
    code, output = root_command(
        [
            "gitleaks",
            "detect",
            "--source",
            ".",
            "--no-git",
            "--redact",
            "--no-banner",
            "-v",
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ]
    )
    if code not in (0, None) and report.exists():
        output = f"{output}\n{report.read_text(encoding='utf-8', errors='replace')}"
    report.unlink(missing_ok=True)
    status = max(status, show(code, output, "sin secretos"))

    print("\n== patrones inseguros (semgrep p/ci) ==")
    code, output = root_command(
        [
            "semgrep",
            "--config",
            "p/ci",
            "--config",
            ".semgrep/rules.yml",
            "--error",
            "--quiet",
            "--exclude",
            "node_modules",
            "--exclude",
            "dist",
            "--exclude",
            "coverage",
            "--exclude",
            "target",
            "--exclude",
            "tools/fixtures",
            ".",
        ]
    )
    status = max(status, show(code, output, "sin hallazgos"))

    for name in langs:
        lang = next(lg for lg in LANGS if lg.name == name)
        if name == "go":
            print("\n== gosec (Go) ==")
            cmd = Command(
                [
                    "golangci-lint",
                    "run",
                    "--default=none",
                    "--enable=gosec",
                    "--output.text.print-issued-lines=false",
                ]
            )
            status = max(status, show(*run(cmd, lang, []), "sin hallazgos"))
        elif name == "java":
            print("\n== java: semgrep p/ci + IllegalCatch (sin spotbugs: no lee bytecode 25)")

    return max(status, audit(langs))


def mutation(langs: list[str]) -> int:
    """Mutation testing: mide si los tests detectan cambios en el codigo."""
    status = 0
    ran = 0
    for name in langs:
        cmd = MUTATION.get(name)
        if cmd is None:
            continue
        lang = next(lg for lg in LANGS if lg.name == name)
        ran += 1
        print(f"\n== mutacion: {name} ==")
        status = max(status, show(*run(cmd, lang, []), "mutantes cazados"))
    if not ran:
        print("Sin mutation testing configurado para el lote.")
        print("Configurados: react y typescript (stryker.conf.json).")
        return 2
    return status


def repo_slug() -> str | None:
    """owner/repo del remoto de GitHub, si existe."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],  # noqa: S607 - git en el PATH
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", result.stdout.strip())
    return match.group(1) if match else None


def parse_alerts(raw: str) -> list[dict[str, Any]] | None:
    """Aplana las paginas de gh --slurp; None si la respuesta no es JSON."""
    try:
        pages = json.loads(raw or "[]")
    except ValueError:
        return None
    if not isinstance(pages, list):
        return None
    if pages and isinstance(pages[0], list):
        return [alert for page in pages for alert in page if isinstance(alert, dict)]
    return [alert for alert in pages if isinstance(alert, dict)]


OSV_URL = "https://api.osv.dev/v1/querybatch"

MAVEN_TYPES = {"jar", "war", "pom", "ejb", "ejb-client", "test-jar", "maven-plugin"}


def parse_maven_dependencies(text: str) -> list[tuple[str, str]]:
    """Extrae (group:artifact, version) del listado de Maven."""
    packages = []
    for raw in text.splitlines():
        parts = raw.strip().split(" -- ")[0].split(":")
        if len(parts) >= 4 and parts[2] in MAVEN_TYPES and parts[3]:
            packages.append((f"{parts[0]}:{parts[1]}", parts[3]))
    return sorted(set(packages))


def maven_packages() -> list[tuple[str, str]] | None:
    """Dependencias de Java-teacher (test incluye compile y runtime)."""
    exe = shutil.which("mvn")
    if exe is None:
        return None
    output = ROOT / "Java-teacher" / "target" / "dependencies.txt"
    try:
        proc = subprocess.run(  # noqa: S603 - executable resuelto con shutil.which
            [
                exe,
                "-q",
                "-B",
                "dependency:list",
                "-DincludeScope=test",
                f"-DoutputFile={output}",
            ],
            cwd=ROOT / "Java-teacher",
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not output.exists():
        return None
    return parse_maven_dependencies(output.read_text(encoding="utf-8"))


def cargo_packages() -> list[tuple[str, str]] | None:
    """Dependencias de Cargo.lock; None si no existe o no parsea."""
    lock = ROOT / "Rust-teacher" / "Cargo.lock"
    if not lock.exists():
        return None
    try:
        return parse_cargo_lock(lock.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def parse_cargo_lock(text: str) -> list[tuple[str, str]]:
    """Extrae (crate, version) de Cargo.lock, solo de crates.io."""
    data = tomllib.loads(text)
    packages = [
        (package["name"], package["version"])
        for package in data.get("package", [])
        if str(package.get("source", "")).startswith("registry+")
    ]
    return sorted(set(packages))


def osv_queries(packages: list[tuple[str, str]], ecosystem: str = "Maven") -> dict[str, object]:
    """Cuerpo de la consulta batch a OSV."""
    return {
        "queries": [
            {"package": {"name": name, "ecosystem": ecosystem}, "version": version}
            for name, version in packages
        ]
    }


def parse_osv_response(packages: list[tuple[str, str]], data: object) -> list[str] | None:
    """Convierte una respuesta batch de OSV; None si esta incompleta."""
    if not isinstance(data, dict):
        return None
    results = data.get("results")
    if not isinstance(results, list) or len(results) != len(packages):
        return None
    rows = []
    for (name, version), result in zip(packages, results, strict=True):
        if not isinstance(result, dict):
            return None
        vulns = result.get("vulns", [])
        if not isinstance(vulns, list):
            return None
        for vuln in vulns:
            if not isinstance(vuln, dict):
                return None
            rows.append(f"  {name}@{version}: {vuln.get('id', '?')}")
    return rows


def osv_vulnerabilities(
    packages: list[tuple[str, str]], ecosystem: str = "Maven"
) -> list[str] | None:
    """Vulnerabilidades conocidas por OSV; None si no hay respuesta."""
    request = urllib.request.Request(
        OSV_URL,
        data=json.dumps(osv_queries(packages, ecosystem)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310 - URL https fija
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return parse_osv_response(packages, data)


def dependabot_alerts() -> tuple[int | None, str]:
    """Alertas abiertas de Maven via Dependabot, con paginacion."""
    slug = repo_slug()
    if slug is None:
        return 2, "[X] no encontre un remoto de GitHub para consultar alertas"
    try:
        result = subprocess.run(  # noqa: S603 - argumentos fijos
            [  # noqa: S607 - gh en el PATH
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{slug}/dependabot/alerts?state=open&per_page=100",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "[X] falta gh (GitHub CLI) o no respondio"
    if result.returncode != 0:
        message = result.stderr.strip()
        if "Resource not accessible" in message or "HTTP 403" in message:
            return 2, "[X] el token no puede leer alertas: verificacion incompleta"
        return 1, f"[X] gh no pudo consultar alertas: {message}"
    alerts = parse_alerts(result.stdout)
    if alerts is None:
        return 1, "[X] respuesta inesperada de gh"
    # Node/Go/Python ya se auditan con sus herramientas; Dependabot cubre Maven.
    maven = [
        alert
        for alert in alerts
        if str(alert.get("dependency", {}).get("manifest_path", "")).endswith("pom.xml")
    ]
    lines = [
        "  {} [{}] {}".format(
            alert.get("dependency", {}).get("package", {}).get("name", "?"),
            alert.get("security_advisory", {}).get("severity", "?"),
            alert.get("dependency", {}).get("manifest_path", ""),
        )
        for alert in maven
    ]
    return (1, "\n".join(lines)) if lines else (0, "")


def audit_maven() -> int:
    """Dependabot para Maven: complemento de OSV, no su sustituto."""
    print("\n== dependencias Java (Dependabot) ==")
    if os.environ.get("LINT_SKIP_DEPENDABOT") == "1":
        print("  omitido: el token de CI no lee alertas Dependabot (OSV ya audita Maven)")
        return 0
    code, output = dependabot_alerts()
    if code == 0 and output.strip():
        print(output)
        return 0
    return show(code, output, "sin alertas abiertas")


def audit_osv(packages: list[tuple[str, str]] | None, ecosystem: str, source: str) -> int:
    """Audita paquetes con OSV; 2 si no se pudo verificar."""
    if packages is None:
        print(f"  [X] no pude leer {source}: verificacion incompleta")
        return 2
    rows = osv_vulnerabilities(packages, ecosystem)
    if rows is None:
        print("  [X] OSV no respondio: verificacion incompleta")
        return 2
    if rows:
        print("\n".join(rows))
        return 1
    print(f"  sin vulnerabilidades conocidas (OSV, {len(packages)} deps)")
    return 0


def audit_java(_lang: Lang) -> int:
    """Dependencias Maven via OSV."""
    return audit_osv(maven_packages(), "Maven", "las dependencias Maven")


def audit_rust(_lang: Lang) -> int:
    """Dependencias de crates.io via OSV."""
    return audit_osv(cargo_packages(), "crates.io", "Cargo.lock")


def audit_python(lang: Lang) -> int:
    """Dependencias Python con pip-audit; usa el lock si existe."""
    req = ROOT / lang.folder / "requirements.lock"
    if not req.exists():
        req = ROOT / lang.folder / "requirements.txt"
    if not req.exists():
        print("  sin requirements.txt: nada que auditar")
        return 0
    return audit_command(Command(["pip-audit", "-r", req.name]), lang)


def audit_command(cmd: Command, lang: Lang) -> int:
    """Corre un scanner de dependencias y traduce su estado."""
    code, output = run(cmd, lang, [])
    if code is None:
        print(output)
        return 2
    if code != 0:
        if output:
            print(output)
        return 1
    print("  sin vulnerabilidades conocidas")
    return 0


AUDIT_HANDLERS = {
    "java": audit_java,
    "python": audit_python,
    "rust": audit_rust,
}


def audit(langs: list[str]) -> int:
    """Busca vulnerabilidades conocidas en las dependencias de cada lenguaje."""
    status = 0
    for name in langs:
        lang = next(lg for lg in LANGS if lg.name == name)
        print(f"\n== vulnerabilidades: {name} ==")
        handler = AUDIT_HANDLERS.get(name)
        if handler is not None:
            status = max(status, handler(lang))
        else:
            status = max(status, audit_command(AUDIT[name], lang))

    print("\n== vulnerabilidades: tools/node ==")
    code, output = root_command(["npm", "audit", "--prefix", "tools/node", "--audit-level=high"])
    status = max(status, show(code, output, "sin vulnerabilidades conocidas"))

    return max(status, audit_maven())
