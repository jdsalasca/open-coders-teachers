# Java-teacher

JDK 25 + Maven (bytecode 21). Linters: **Checkstyle**, **Spotless**, **ArchUnit**, `-Xlint:all`.

```powershell
python tools/lint.py --fix Java-teacher   # desde la raiz
mvn -q test                               # checkstyle en validate + reglas de capas
```

## Arquitectura hexagonal

```text
edu/teachers/domain/           entidades y puertos (interfaces)
edu/teachers/application/      casos de uso
edu/teachers/infrastructure/   adaptadores que implementan los puertos
edu/teachers/Main.java         composition root
```

`src/test/java/edu/teachers/ArchitectureTest.java` falla el build si el dominio
toca application/infrastructure, si application toca infrastructure, si
persistence usa application o si web usa domain. El adaptador de entrada
(`infrastructure.web`) sí usa application: es su trabajo.

El controller valida con Bean Validation (`@NotBlank`, `@Pattern` con
`(?sU)` y `@CodePointLength` 1..200) y devuelve `TaskView`; nunca expone
`Task`. El título se conserva sin recortar, el límite cuenta code points y un
título solo de espacios Unicode (incluido NBSP) se rechaza. El dominio repite
las invariantes (1..200, no blanco) por si se llama sin pasar por el controller.

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

El repositorio en memoria usa `synchronized`: el orden de la lista es el de
inserción y coincide con los IDs. Al llegar a `Integer.MAX_VALUE` lanza
`IllegalStateException` en vez de desbordar, y hay tests del último ID y del
agotamiento. Una entrada inválida puede consumir un ID (hueco documentado).

Ademas: `SummaryJavadoc`, `NonEmptyAtclauseDescription`, `IllegalCatch`,
`IllegalThrows`, `HiddenField`, `ParameterAssignment`, `BooleanExpressionComplexity`,
`FileLength`, `PackageName`, `StaticVariableName`.

PMD añade `SystemPrintln`, `AvoidPrintStackTrace` y
`AvoidCatchingGenericException`; `Main.java` queda excluido de PMD por ser el
composition root que imprime el ejemplo.
