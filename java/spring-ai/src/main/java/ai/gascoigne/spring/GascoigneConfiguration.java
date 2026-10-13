package ai.gascoigne.spring;

import ai.gascoigne.Gascoigne;
import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.ai.model.tool.ToolCallingManager;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.ImportAware;
import org.springframework.core.annotation.AnnotationAttributes;
import org.springframework.core.type.AnnotationMetadata;

/** Wraps the application's {@link ToolCallingManager} when {@link EnableGascoigne} is present. */
@Configuration(proxyBeanMethods = false)
class GascoigneConfiguration implements ImportAware {
    private static final String DEFAULT_AGENT = "spring-ai";

    private String agent = DEFAULT_AGENT;
    private Set<String> skip = Set.of();
    private int minChars = 800;

    @Override
    public void setImportMetadata(AnnotationMetadata importMetadata) {
        Map<String, Object> raw =
                importMetadata.getAnnotationAttributes(EnableGascoigne.class.getName());
        AnnotationAttributes attributes = AnnotationAttributes.fromMap(raw);
        if (attributes == null) {
            return;
        }
        String named = attributes.getString("agent");
        agent = named.isEmpty() ? DEFAULT_AGENT : named;
        skip = Arrays.stream(attributes.getStringArray("skip")).collect(Collectors.toSet());
        minChars = attributes.getNumber("minChars").intValue();
    }

    /** The application's own {@link Gascoigne} bean if it has one, else a default client. */
    private Gascoigne client(ObjectProvider<Gascoigne> own) {
        return own.getIfAvailable(() -> Gascoigne.builder().agent(agent).build());
    }

    @Bean
    static BeanPostProcessor gascoigneToolCalling(
            ObjectProvider<Gascoigne> gascoigne, GascoigneConfiguration settings) {
        return new BeanPostProcessor() {
            @Override
            public Object postProcessAfterInitialization(Object bean, String beanName) {
                if (bean instanceof ToolCallingManager manager
                        && !(bean instanceof GascoigneToolCallingManager)) {
                    return new GascoigneToolCallingManager(
                            manager, settings.client(gascoigne), settings.skip, settings.minChars);
                }
                return bean;
            }
        };
    }
}
