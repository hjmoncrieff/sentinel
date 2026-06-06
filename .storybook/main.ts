import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { StorybookConfig } from "@storybook/react-vite";

const rootDir = fileURLToPath(new URL("..", import.meta.url));

const config: StorybookConfig = {
  stories: ["../apps/analyst-console/src/stories/**/*.stories.@(ts|tsx)"],
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-a11y",
    "@storybook/addon-interactions",
  ],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  viteFinal: async (viteConfig) => {
    viteConfig.resolve ??= {};
    viteConfig.resolve.alias = {
      ...(viteConfig.resolve.alias ?? {}),
      "@": resolve(rootDir, "apps/analyst-console/src"),
    };

    return viteConfig;
  },
};

export default config;
