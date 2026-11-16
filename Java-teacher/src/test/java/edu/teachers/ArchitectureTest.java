package edu.teachers;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

/** Reglas de arquitectura hexagonal y de patrones verificadas en cada build. */
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
  static final ArchRule dominio_solo_jdk_y_dominio =
      noClasses()
          .that()
          .resideInAPackage("..domain..")
          .should()
          .dependOnClassesThat()
          .resideOutsideOfPackages("java..", "..domain..");

  @ArchTest
  static final ArchRule puertos_con_sufijo_port =
      classes()
          .that()
          .resideInAPackage("..domain..")
          .and()
          .areInterfaces()
          .should()
          .haveSimpleNameEndingWith("Port");

  @ArchTest
  static final ArchRule adaptadores_en_infraestructura =
      classes()
          .that()
          .implement(JavaClass.Predicates.simpleNameEndingWith("Port"))
          .should()
          .resideInAPackage("..infrastructure..");

  @ArchTest
  static final ArchRule adaptadores_con_nombre_de_patron =
      classes()
          .that()
          .implement(JavaClass.Predicates.simpleNameEndingWith("Port"))
          .should()
          .haveSimpleNameEndingWith("Repository");

  @ArchTest
  static final ArchRule aplicacion_sin_infraestructura =
      noClasses()
          .that()
          .resideInAPackage("..application..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("..infrastructure..");

  @ArchTest
  static final ArchRule persistencia_sin_aplicacion =
      noClasses()
          .that()
          .resideInAPackage("..infrastructure.persistence..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("..application..");

  @ArchTest
  static final ArchRule web_sin_dominio =
      noClasses()
          .that()
          .resideInAPackage("..infrastructure.web..")
          .should()
          .dependOnClassesThat()
          .resideInAPackage("..domain..");

  // Se activa solo si Spring esta en el classpath: un bean singleton no debe
  // tener estado mutable compartido entre peticiones.
  @ArchTest
  static final ArchRule beans_sin_estado =
      classes()
          .that()
          .areAnnotatedWith("org.springframework.stereotype.Service")
          .or()
          .areAnnotatedWith("org.springframework.stereotype.Component")
          .or()
          .areAnnotatedWith("org.springframework.web.bind.annotation.RestController")
          .should()
          .haveOnlyFinalFields()
          .allowEmptyShould(true);

  @ArchTest
  static final ArchRule sin_ciclos =
      slices().matching("edu.teachers.(*)..").should().beFreeOfCycles();
}
