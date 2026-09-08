import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const directory = dirname(fileURLToPath(import.meta.url));
const compat = new FlatCompat({ baseDirectory: directory });
const config = [...compat.extends("next/core-web-vitals", "next/typescript")];
const eslintConfig = [{ ignores: [".next/**", "node_modules/**", "next-env.d.ts"] }, ...config];

export default eslintConfig;
