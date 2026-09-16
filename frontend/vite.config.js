import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5174 },
  build: {
    rollupOptions: {
      output: {
        /*
         * سه اپ در یک فایل بودند.
         *
         * مشتری‌ای که مینی‌اپ را روی موبایل باز می‌کند، کلِ پنل مدیر
         * را هم دانلود می‌کرد — ۱۷۲ کیلوبایتِ فشرده برای صفحه‌ای که
         * سه کارت نشان می‌دهد. و همان مشتری، همان کسی است که
         * اینترنتش محدود است.
         *
         * حالا React و lucide در تکه‌های جدا می‌نشینند: مینی‌اپ و
         * پنل نماینده فقط چیزی را می‌گیرند که لازم دارند، و
         * تکه‌های مشترک یک‌بار کش می‌شوند و در آپدیت بعدی دوباره
         * دانلود نمی‌شوند.
         */
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("react-dom") || id.includes("/react/") ||
              id.includes("scheduler")) return "react";
          if (id.includes("lucide-react")) return "icons";
          return "vendor";
        },
      },
    },
  },
});
