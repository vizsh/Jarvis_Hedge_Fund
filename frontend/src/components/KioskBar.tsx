import { useEffect, useRef, useState } from "react";

import { useT } from "../lib/i18n";
import { useKiosk } from "../lib/kiosk";

const WARN_SEC = 20;

/** The strip at the top while the device is shared: says nothing is saved, wipes for the next person. */
export function KioskBar() {
  const { t } = useT();
  const { on, idleSec, nextPerson, disable, people } = useKiosk();
  const last = useRef(Date.now());
  const [left, setLeft] = useState<number | null>(null);

  useEffect(() => {
    if (!on) return;
    last.current = Date.now();
    const poke = () => { last.current = Date.now(); setLeft(null); };
    const evs = ["pointerdown", "keydown", "touchstart", "wheel"] as const;
    evs.forEach((e) => window.addEventListener(e, poke, { passive: true }));
    const id = window.setInterval(() => {
      const idle = (Date.now() - last.current) / 1000;
      if (idle >= idleSec) {
        const remain = Math.ceil(idleSec + WARN_SEC - idle);
        if (remain <= 0) { last.current = Date.now(); setLeft(null); void nextPerson(); }
        else setLeft(remain);
      }
    }, 1000);
    return () => { evs.forEach((e) => window.removeEventListener(e, poke)); window.clearInterval(id); };
  }, [on, idleSec, nextPerson]);

  if (!on) return null;
  return (
    <div className={`kiosk-bar ${left !== null ? "warn" : ""}`} role="region" aria-label="Shared device mode">
      <span className="kiosk-msg">
        {left !== null
          ? t(`Clearing for the next person in ${left}s. Touch the screen to keep going.`, `${left} सेकंड में अगले व्यक्ति के लिए साफ़ हो जाएगा। जारी रखने के लिए स्क्रीन छूइए।`)
          : t("Shared device: nothing you enter is saved.", "साझा डिवाइस: आप जो भी भरेंगे वह सहेजा नहीं जाएगा।")}
      </span>
      <button className="kiosk-print" onClick={() => window.print()}>🖨 {t("Print my results", "मेरे नतीजे छापें")}</button>
      <button className="kiosk-next" onClick={() => void nextPerson()}>👤 {t("Next person", "अगला व्यक्ति")}{people ? ` · ${people}` : ""}</button>
      <button className="kiosk-exit" onClick={disable} aria-label="exit shared device mode">✕</button>
    </div>
  );
}

export function KioskToggle() {
  const { t } = useT();
  const { on, enable } = useKiosk();
  if (on) return null;
  return <button className="kiosk-toggle" onClick={enable} title={t("Use this device for many people: nothing is saved", "कई लोगों के लिए इस डिवाइस का उपयोग: कुछ भी सहेजा नहीं जाएगा")}>👥 {t("Shared", "साझा")}</button>;
}
