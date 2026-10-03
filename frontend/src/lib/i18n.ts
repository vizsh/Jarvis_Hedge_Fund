import { useEffect, useRef, useState } from "react";

import { useLang } from "./lang";

/** Pick the string for the language the person chose. English stays English; Hindi is shown only
 *  when Hindi is selected, so the choice is theirs. */
const cache = new Map<string, string>();

/** `t(en, hi)` picks a fixed string. `d(text)` is for sentences the backend wrote in English
 *  (verdicts, explanations, rule labels): in Hindi mode it shows the Hindi from /translate when it
 *  has arrived (exact rules first, guarded model after; unchanged English if neither is sure). */
export function useT() {
  const hi = useLang((s) => s.lang) === "hi";
  const [, bump] = useState(0);
  const wanted = useRef(new Set<string>());
  const d = (text: string | null | undefined): string => {
    if (!text || !hi) return text ?? "";
    const c = cache.get(text);
    if (c !== undefined) return c;
    wanted.current.add(text);
    return text;
  };
  const mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);
  useEffect(() => {
    if (!wanted.current.size) return;
    const need = [...wanted.current];
    wanted.current.clear();
    (async () => {
      for (let i = 0; i < need.length; i += 40) {
        const chunk = need.slice(i, i + 40);
        try {
          const r = await fetch("/translate", { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ lines: chunk }) });
          const j = await r.json();
          chunk.forEach((l, k) => cache.set(l, j.hindi?.[k] ?? l));
        } catch { chunk.forEach((l) => cache.set(l, l)); }
      }
      if (mounted.current) bump((n) => n + 1);
    })();
  });
  return { hi, t: (en: string, hindi: string) => (hi ? hindi : en), d };
}

// Known microphone / transcription messages (they are produced in English by the voice code).
const ERRORS: [RegExp, string][] = [
  [/did not hear anything/i, "कुछ सुनाई नहीं दिया। माइक दबाइए और \"सुन रहा हूँ\" दिखने के बाद बोलिए।"],
  [/could not be started/i, "माइक शुरू नहीं हो सका।"],
  [/could not make that out/i, "समझ नहीं आया। माइक दबाकर फिर कोशिश कीजिए।"],
  [/too short to catch/i, "यह बहुत छोटा था। माइक दबाइए, बोलिए और रुकिए।"],
  [/could not hear any speech/i, "कोई आवाज़ नहीं सुनाई दी। जाँचिए कि सही माइक चुना है और थोड़ा क़रीब से बोलिए।"],
  [/came out empty/i, "रिकॉर्डिंग ख़ाली आई। माइक दबाकर फिर कोशिश कीजिए।"],
  [/not confident enough/i, "मैंने सुना तो, पर इतना पक्का नहीं कि उस पर कुछ करूँ।"],
  [/transcription is not installed/i, "स्थानीय ट्रांसक्रिप्शन इंस्टॉल नहीं है।"],
  [/could not reach the transcriber/i, "ट्रांसक्राइबर तक नहीं पहुँच सका।"],
  [/permission was denied|permission denied/i, "माइक की अनुमति नहीं मिली। एड्रेस बार में अनुमति दीजिए और फिर कोशिश कीजिए।"],
];

/** The message in Hindi when we know it, otherwise unchanged. */
export function hiError(msg: string | null, hi: boolean): string | null {
  if (!msg || !hi) return msg;
  return ERRORS.find(([rx]) => rx.test(msg))?.[1] ?? msg;
}

// The guided jobs come from the backend in English; Hindi wording by id.
export const JOBS_HI: Record<string, { title: string; subtitle: string }> = {
  health_check: { title: "मेरे पोर्टफ़ोलियो की सेहत जाँचिए", subtitle: "तीन मिनट में: आपके पास क्या है और उसमें क्या गड़बड़ हो सकती है" },
  fix_finding: { title: "बताई गई समस्या ठीक कीजिए", subtitle: "एक ख़ामी को ठोस, लागत सहित सौदों में बदलिए" },
  should_i_buy: { title: "तय कीजिए कि कुछ ख़रीदना चाहिए या नहीं", subtitle: "किसी नाम को विश्लेषकों, सीमाओं और आपके अपने पोर्टफ़ोलियो से परखिए" },
  tax_plan: { title: "टैक्स के मौसम की तैयारी", subtitle: "बेचने पर कितना ख़र्च होगा और रुकने पर कितना बचेगा" },
  stress_test: { title: "देखिए, गड़बड़ हुई तो क्या होगा", subtitle: "असली गिरावटें, आपके अपने शेयरों पर दोहराई हुई" },
  deploy_cash: { title: "बेकार पड़े नक़द को काम पर लगाइए", subtitle: "नया पैसा कहाँ जा सकता है, बिना मौजूदा समस्या बढ़ाए" },
  rebalance: { title: "पूरे पोर्टफ़ोलियो का संतुलन", subtitle: "कम से कम सौदे जो सब कुछ सीमा के भीतर ले आएँ" },
  add_basis: { title: "बताइए आपने कितने में ख़रीदा", subtitle: "ख़रीद भाव से हर टैक्स आँकड़ा खुलता है" },
  onboarding: { title: "इसे मेरे पैसे के लिए तैयार कीजिए", subtitle: "तीन सवाल, फिर यहाँ सब कुछ आपके पोर्टफ़ोलियो के बारे में" },
};
