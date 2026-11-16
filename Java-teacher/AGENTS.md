# Java-teacher

Java 25 + Maven. Linter: **Checkstyle** 10.26 (`config/checkstyle/checkstyle.xml`)
y formato **Spotless + google-java-format** (`pom.xml`).

```powershell
python tools/lint.py --fix Java-teacher/  # desde la raiz
mvn -q compile                            # checkstyle corre en validate
```

Checkstyle: `UnusedImports`, `UnusedLocalVariable`, `AvoidStarImport`,
`ParameterNumber` (4), `MethodLength` (40), `CyclomaticComplexity` (8),
`DeclarationOrder`, `NeedBraces`, nombres (`TypeName`, `MethodName`,
`MemberName`, `ConstantName`, `LocalVariableName`, `ParameterName`) y Javadoc
en tipos y metodos publicos.

Orden que exige `DeclarationOrder`: campos estaticos, campos de instancia,
constructores, metodos. La indentacion la decide Spotless, no la edites a mano.
