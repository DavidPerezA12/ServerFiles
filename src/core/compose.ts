import fs from "fs-extra";
import YAML from "yaml";
import type { ServerfilesConfig } from "../utils/validators.js";
import { paths, templatePath } from "./paths.js";

type ComposeDocument = {
  name?: string;
  services?: Record<string, ComposeService>;
  volumes?: Record<string, unknown>;
  networks?: Record<string, unknown>;
};

type ComposeService = {
  ports?: string[];
  [key: string]: unknown;
};

const servicePortKeys = {
  caddy: [
    ["caddyHttp", 80, undefined],
    ["caddyHttps", 443, undefined]
  ],
  postgres: [["postgres", 5432, "127.0.0.1"]],
  redis: [["redis", 6379, "127.0.0.1"]],
  mongodb: [["mongodb", 27017, "127.0.0.1"]],
  adminer: [["adminer", 8080, "127.0.0.1"]],
  "uptime-kuma": [["uptimeKuma", 3001, "127.0.0.1"]],
  filebrowser: [["filebrowser", 80, "127.0.0.1"]],
  "immich-server": [["immich", 2283, "127.0.0.1"]]
} as const;

export async function readCompose(filePath = paths.compose): Promise<ComposeDocument> {
  if (!(await fs.pathExists(filePath))) {
    return {};
  }

  const raw = await fs.readFile(filePath, "utf8");
  return (YAML.parse(raw) ?? {}) as ComposeDocument;
}

export async function writeCompose(compose: ComposeDocument, filePath = paths.compose) {
  await fs.writeFile(filePath, YAML.stringify(compose), "utf8");
}

export function applyConfigToCompose(compose: ComposeDocument, config: ServerfilesConfig) {
  for (const [serviceName, portKeys] of Object.entries(servicePortKeys)) {
    const service = compose.services?.[serviceName];
    if (!service) {
      continue;
    }

    service.ports = portKeys.map(([portKey, containerPort, host]) => {
      const port = config.ports[portKey];
      return host ? `${host}:${port}:${containerPort}` : `${port}:${containerPort}`;
    });
  }

  return compose;
}

export async function mergeComposeTemplate(templateName: string, config?: ServerfilesConfig) {
  const current = await readCompose();
  const addition = YAML.parse(await fs.readFile(templatePath(templateName), "utf8")) as ComposeDocument;

  const merged: ComposeDocument = {
    ...current,
    ...addition,
    services: {
      ...(current.services ?? {}),
      ...(addition.services ?? {})
    },
    volumes: {
      ...(current.volumes ?? {}),
      ...(addition.volumes ?? {})
    },
    networks: {
      ...(current.networks ?? {}),
      ...(addition.networks ?? {})
    }
  };

  await writeCompose(config ? applyConfigToCompose(merged, config) : merged);
  return {
    addedServices: Object.keys(addition.services ?? {}).filter(
      (service) => !(current.services ?? {})[service]
    ),
    existingServices: Object.keys(addition.services ?? {}).filter(
      (service) => Boolean((current.services ?? {})[service])
    )
  };
}
