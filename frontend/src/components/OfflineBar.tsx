import { installPack, usePack } from "../lib/offline";
import { useT } from "../lib/i18n";

/** Top of the Rural page: whether the tools will still work with no network, and a button to get ready. */
export function OfflineBar() {
  const { t } = useT();
  const { state, pct, msg, online } = usePack();
  if (state === "unsupported") return null;
  return (
    <div className={`offline-bar ${state} ${online ? "" : "off"}`} role="status">
      {!online && <b>📴 {t("No internet right now.", "अभी इंटरनेट नहीं है।")} </b>}
      {state === "ready" && <span>✓ {t("These tools work without internet on this device.", "ये औज़ार इस डिवाइस पर बिना इंटरनेट भी चलते हैं।")}</span>}
      {state === "none" && (<>
        <span>{t("Village with weak signal? Save these tools on this device so they work with no internet.", "कमज़ोर सिग्नल वाला गाँव? इन औज़ारों को इस डिवाइस में सहेजिए ताकि बिना इंटरनेट भी चलें।")}</span>
        <button className="btn go" disabled={!online} onClick={() => void installPack()}>⬇ {t("Download offline pack (about 12 MB)", "ऑफ़लाइन पैक डाउनलोड करें (लगभग 12 MB)")}</button>
      </>)}
      {state === "installing" && (<>
        <span>{t("Saving for offline use… keep this page open.", "ऑफ़लाइन उपयोग के लिए सहेज रहा हूँ… यह पेज खुला रखिए।")} {msg}</span>
        <div className="offline-prog"><div style={{ width: `${pct}%` }} /></div>
      </>)}
      {state === "error" && (<>
        <span>{t("Could not finish saving: ", "सहेजना पूरा नहीं हो सका: ")}{msg}</span>
        <button className="btn" onClick={() => void installPack()}>{t("Try again", "फिर कोशिश करें")}</button>
      </>)}
    </div>
  );
}
