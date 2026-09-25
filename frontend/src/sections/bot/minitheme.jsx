/**
 * ربات: پوسته‌ی مینی‌اپِ خودِ مالک.
 *
 * تا ۱.۱۰۹ استودیوی پوسته فقط در پرتالِ نماینده بود؛ مینی‌اپِ مالک همیشه
 * «پیش‌فرض» می‌ماند و راهی برای عوض‌کردنش نبود. استودیوی دومی ساخته نشد:
 * همان `ThemeBox`، با `ownerThemeApi` که به مسیرهای مدیرِ ربات (پوسته، برند، لوگو) می‌رود.
 */
import React, { useMemo, useState } from "react";
import { ownerThemeApi, ThemeBox } from "../../portal/studio.jsx";
import { Msg, SectionHead } from "../../ui/index";

export function BotMiniThemeSection({ password }) {
  const A = useMemo(() => ownerThemeApi(password), [password]);
  const [note, setNote] = useState("");
  return (
    <div>
      <SectionHead title="پوسته‌ی مینی‌اپ"
        desc="رنگ، قالب، لوگو و صفحه‌ی آغاز — همان چیزی که مشتری با بازکردنِ مینی‌اپِ ربات می‌بیند." />
      <Msg msg={note ? { t: "ok", m: note } : null} />
      <ThemeBox inline themeApi={A} onNote={setNote} />
    </div>
  );
}
