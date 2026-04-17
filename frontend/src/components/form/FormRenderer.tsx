import { type ReactNode, useMemo } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { makeResolver } from "./resolver";
import { resolveFieldComponent } from "./FieldRegistry";

export interface FormRendererProps<T extends Record<string, unknown>> {
  schema: Record<string, unknown>;
  defaultValues?: Partial<T>;
  onSubmit: (values: T, helpers: { setFieldErrors: (e: Record<string, string>) => void }) => void | Promise<void>;
  children?: ReactNode;
}

export function FormRenderer<T extends Record<string, unknown>>(
  props: FormRendererProps<T>,
): JSX.Element {
  const { schema, defaultValues, onSubmit, children } = props;
  const resolver = useMemo(() => makeResolver(schema), [schema]);

  const methods = useForm<T>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- RHF Resolver generic is difficult to reconcile with our open-ended T
    resolver: resolver as any,
    defaultValues: defaultValues as any, // eslint-disable-line @typescript-eslint/no-explicit-any -- same reason
    mode: "onSubmit",
  });

  const properties = (schema.properties ?? {}) as Record<string, Record<string, unknown>>;

  const setFieldErrors = (errors: Record<string, string>) => {
    for (const [name, message] of Object.entries(errors)) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- dynamic field names
      methods.setError(name as any, { message, type: "server" });
    }
  };

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={methods.handleSubmit((values) => onSubmit(values as T, { setFieldErrors }))}
        className="flex flex-col gap-4"
      >
        {Object.entries(properties).map(([name, fieldSchema]) => {
          const Comp = resolveFieldComponent(fieldSchema);
          return (
            <Comp
              key={name}
              name={name}
              schema={fieldSchema}
              register={methods.register}
              error={methods.formState.errors[name as keyof T]?.message as string | undefined}
            />
          );
        })}
        {children}
      </form>
    </FormProvider>
  );
}
