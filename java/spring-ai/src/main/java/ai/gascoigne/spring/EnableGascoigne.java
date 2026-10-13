package ai.gascoigne.spring;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import org.springframework.context.annotation.Import;

/**
 * Opts in to gascoigne for every Spring AI tool call: {@code @Tool} methods, function callbacks
 * and MCP tools alike. Without this annotation, nothing is decorated.
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Import(GascoigneConfiguration.class)
public @interface EnableGascoigne {

    /** Agent name for per-agent stats; empty uses "spring-ai". */
    String agent() default "";

    /** Names of tools whose results are never touched. */
    String[] skip() default {};

    /** Results shorter than this are not sent to gascoigne at all. */
    int minChars() default 800;
}
