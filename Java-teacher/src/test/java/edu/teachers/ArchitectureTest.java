package edu.teachers;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

/** Reglas de arquitectura hexagonal verificadas en cada build. */
@AnalyzeClasses(packages = "edu.teachers", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureTest {

  @ArchTest
  static final ArchRule dominio_aislado =
      noClasses()
          .that()
          .resideInAPackage("..domain..")
          .should()
          .dependOnClassesThat()
          .resideInAnyPackage("..application..", "..infrastructure..");

  @ArchTest
  static final ArchRule aplicacion_sin_infraestructura =
      noClasses()
          .that()
          .resideInAPackage("..application..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("..infrastructure..");

  @ArchTest
  static final ArchRule infraestructura_sin_aplicacion =
      noClasses()
          .that()
          .resideInAPackage("..infrastructure..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("..application..");
}
