import { z } from "zod";

const portSchema = z.number().int().min(1).max(65535);

export const serverfilesConfigSchema = z.object({
  version: z.number().int().positive(),
  serverName: z.string().min(1),
  root: z.string().min(1),
  stacks: z.array(z.string()).default([]),
  ports: z.object({
    caddyHttp: portSchema,
    caddyHttps: portSchema,
    postgres: portSchema,
    redis: portSchema,
    mongodb: portSchema,
    adminer: portSchema,
    uptimeKuma: portSchema,
    filebrowser: portSchema,
    immich: portSchema
  })
}).superRefine((config, ctx) => {
  const seen = new Map<number, string>();

  for (const [name, port] of Object.entries(config.ports)) {
    const existing = seen.get(port);
    if (existing) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["ports", name],
        message: `Port ${port} is already used by ${existing}`
      });
      continue;
    }

    seen.set(port, name);
  }
});

export type ServerfilesConfig = z.infer<typeof serverfilesConfigSchema>;
