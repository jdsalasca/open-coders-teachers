# Java-teacher

Java 25 + Maven. Linters: **Checkstyle**, **Spotless**, **ArchUnit**, `-Xlint:all`.

```powershell
python tools/lint.py --fix Java-teacher   # desde la raiz
mvn -q test                               # checkstyle en validate + reglas de capas
```

## Arquitectura hexagonal

```
edu/teachers/domain/           entidades y puertos (interfaces)
edu/teachers/application/      casos de uso
edu/teachers/infrastructure/   adaptadores que implementan los puertos
edu/teachers/Main.java         composition root
```

`src/test/java/edu/teachers/ArchitectureTest.java` falla el build si el dominio
toca application/infrastructure, si application toca infrastructure o si
infrastructure usa application.

## Reglas

`UnusedImports`, `UnusedLocalVariable`, `AvoidStarImport`, `ParameterNumber`
(4), `MethodLength` (40), `CyclomaticComplexity` (8), `NestedIfDepth` (3),
`NestedForDepth` (3), `NestedTryDepth` (2), `ClassFanOutComplexity` (20),
`DeclarationOrder`, `NeedBraces`, `VisibilityModifier`, `ModifierOrder`,
`EmptyBlock`, `OneStatementPerLine`, `MultipleVariableDeclarations`,
`SimplifyBooleanExpression`, `SimplifyBooleanReturn`, `EqualsAvoidNull`,
nombres (`TypeName`, `MethodName`, `MemberName`, `ConstantName`,
`LocalVariableName`, `ParameterName`) y Javadoc en tipos y metodos publicos.

Orden que exige `DeclarationOrder`: campos estaticos, campos de instancia,
constructores, metodos. La indentacion la decide Spotless, no la edites a mano.

## Tests

`*Test.java` con JUnit 5. `mvn test` corre ademas ArchUnit y JaCoCo (60% de
lineas, excluyendo `Main`).

Ademas: `SummaryJavadoc`, `NonEmptyAtclauseDescription`, `IllegalCatch`,
`IllegalThrows`, `HiddenField`, `ParameterAssignment`, `BooleanExpressionComplexity`,
`FileLength`, `PackageName`, `StaticVariableName`.
