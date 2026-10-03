import { useEffect, useState } from "react";

import * as v from "../lib/speak";
import { useT } from "../lib/i18n";

const MUTE_OPTIONS = [1, 5, 15, 60];

/** Voice transport: stop, mute for a span, and pace.
 *
 *  Stop exists because the most common thing a listener wants is "yes, I have got it,
 *  be quiet" — and before this the only way to get that was to let it finish.
 */
export function VoiceBar() {
  const { t } = useT();
  const [state, setState] = useState<v.VoiceState>("idle");
  const [meta, setMeta] = useState({ sentence: 0, total: 0, text: "", mutedUntil: null as number | null });
  const [rate, setRate] = useState(v.getRate());
  const [pickMute, setPickMute] = useState(false);
  const [remaining, setRemaining] = useState("");

  useEffect(() => v.onVoice((s, m) => { setState(s); setMeta(m); }), []);

  // Count the mute down so "muted" is never an unexplained dead state.
  useEffect(() => {
    const t = setInterval(() => {
      const until = v.mutedUntilTs();
      if (!until || Date.now() > until) { setRemaining(""); return; }
      const secs = Math.ceil((until - Date.now()) / 1000);
      setRemaining(secs >= 60 ? `${Math.ceil(secs / 60)}m` : `${secs}s`);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const speaking = state === "speaking";
  const muted = state === "muted" || !!remaining;
  const stopped = state === "stopped";

  return (
    <div className={`voicebar ${speaking ? "live" : ""} ${muted || stopped ? "muted" : ""}`}>
      <div className="vb-state">
        <span className={`vb-dot ${state}`} />
        {muted ? `${t("MUTED", "म्यूट")} ${remaining}` : speaking ? t("SPEAKING", "बोल रहा है")
          : stopped ? t("STOPPED", "रुका हुआ") : t("IDLE", "तैयार")}
      </div>

      {speaking && meta.total > 1 && (
        <div className="vb-progress" title={t(`Sentence ${meta.sentence + 1} of ${meta.total}`, `वाक्य ${meta.sentence + 1} / ${meta.total}`)}>
          {Array.from({ length: meta.total }).map((_, i) => (
            <span key={i} className={i <= meta.sentence ? "on" : ""} />
          ))}
        </div>
      )}

      {stopped ? (
        <button className="btn vb-btn go" onClick={() => v.allowSpeech()}
                title={t("Let JARVIS speak again", "जार्विस को फिर बोलने दीजिए")}>
          ▶ {t("Resume", "फिर शुरू")}
        </button>
      ) : (
        <button className="btn vb-btn" onClick={() => v.stop()}
                title={t("Stop now and stay quiet until you ask something new", "अभी रोकिए और नया सवाल पूछने तक चुप रखिए")}>
          ■ {t("Stop", "रोकें")}
        </button>
      )}

      {muted ? (
        <button className="btn vb-btn go" onClick={() => v.unmute()}>{t("Unmute", "अनम्यूट")}</button>
      ) : (
        <div className="vb-mute">
          <button className="btn vb-btn" onClick={() => setPickMute(!pickMute)}
                  title={t("Silence for a while", "कुछ देर के लिए चुप")}>
            {t("Quiet for", "चुप रहें")} ▾
          </button>
          {pickMute && (
            <div className="vb-menu">
              {MUTE_OPTIONS.map((m) => (
                <div key={m} onClick={() => { v.muteFor(m); setPickMute(false); }}>
                  {m >= 60 ? t("1 hour", "1 घंटा") : t(`${m} min`, `${m} मिनट`)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="vb-rate" title={t("Speaking pace", "बोलने की गति")}>
        <span className="tiny">{t("pace", "गति")}</span>
        <input type="range" min={0.7} max={1.5} step={0.05} value={rate}
               onChange={(e) => { const r = Number(e.target.value); setRate(r); v.setRate(r); }} />
        <span className="num">{rate.toFixed(2)}x</span>
      </div>
    </div>
  );
}
