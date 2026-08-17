// See all configuration options: https://remotion.dev/docs/config
// Each option also is available as a CLI flag: https://remotion.dev/docs/cli

// Note: When using the Node.JS APIs, the config file doesn't apply. Instead, pass options directly to the APIs

import { existsSync } from "node:fs";
import { Config } from "@remotion/cli/config";
import { enableTailwind } from '@remotion/tailwind-v4';

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.overrideBundlerConfig(enableTailwind);
// Standard limited-range yuv420p (bt709 forces "-color_range tv") instead
// of the default full-range yuvj420p: broadest compatibility with mobile
// chat-app video players (WhatsApp/Telegram/iMessage previews, older
// Android players, etc), which can fail to preview full-range video.
Config.setPixelFormat("yuv420p");
Config.setColorSpace("bt709");

// Some sandboxed environments block downloading Remotion's own headless
// Chrome and instead ship a pre-installed one. Use it when present.
const sandboxHeadlessShell =
  "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
if (existsSync(sandboxHeadlessShell)) {
  Config.setBrowserExecutable(sandboxHeadlessShell);
}
