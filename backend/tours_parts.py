"""The single-tool tours, step by step. Each walks through the PARTS of the tool (inputs, the picture, the verdict), not just the tool as a whole.

Applied on top of the base catalogue in tours.py (which defines S, TOURS and BY_ID)."""
from __future__ import annotations

from backend.tours import BY_ID, S


def _set(tid: str, steps: list) -> None:
    BY_ID[tid]["steps"] = steps


_set("overlap", [
    S("/practice?tool=overlap", ".fundpick", "1. Pick two funds", "1. दो फ़ंड चुनिए", "Each card is a fund with its type and yearly fee. Tap two of them. Tap the star on a card to mark a fund you own so the assistant remembers it.", "हर कार्ड एक फ़ंड है, उसके प्रकार और सालाना फ़ीस के साथ। दो पर टैप कीजिए। जो फ़ंड आपके पास है उसके तारे पर टैप कीजिए ताकि सहायक उसे याद रखे।"),
    S("/practice?tool=overlap", ".ovl-grid", "2. The holdings side by side", "2. शेयर आमने-सामने", "Each fund's biggest holdings with their weights. Companies that both funds hold light up.", "हर फ़ंड के सबसे बड़े शेयर उनके हिस्से के साथ। जो कंपनियाँ दोनों फ़ंड रखते हैं वे चमकती हैं।"),
    S("/practice?tool=overlap", ".ovl-side", "3. How much they overlap", "3. कितना मिलते हैं", "The ring shows the overlap as a percentage. A high number means you are paying two fees for nearly the same stocks. The holdings are illustrative samples for each fund type.", "घेरा ओवरलैप को प्रतिशत में दिखाता है। ऊँचे अंक का मतलब है कि आप लगभग एक ही शेयरों के लिए दो फ़ीस दे रहे हैं। ये हर फ़ंड-प्रकार के नमूने हैं।")])

_set("fee", [
    S("/practice?tool=fee", ".sliders", "1. Set your numbers", "1. अपने आँकड़े डालिए", "Set the lump sum, the monthly SIP, the years, the return before fees, your fund's fee and a cheap fund's fee. Everything below re-calculates as you move a slider.", "एकमुश्त रक़म, मासिक SIP, साल, फ़ीस से पहले का रिटर्न, आपके फ़ंड की फ़ीस और सस्ते फ़ंड की फ़ीस तय कीजिए। स्लाइडर हिलाते ही नीचे सब नया हिसाब आ जाता है।"),
    S("/practice?tool=fee", ".fdwrap > div:first-child", "2. Watch the gap open", "2. अंतर बढ़ता देखिए", "Three lines grow from the same start: a cheap fund, your fund and no fee at all. The space between the lines is what the fee takes. Hover the chart to read any year.", "तीन रेखाएँ एक ही शुरुआत से बढ़ती हैं: सस्ता फ़ंड, आपका फ़ंड और बिना फ़ीस। रेखाओं के बीच की जगह वही है जो फ़ीस ले जाती है। कोई भी साल पढ़ने को चार्ट पर घुमाइए।"),
    S("/practice?tool=fee", ".fd-side", "3. The cost in rupees", "3. रुपयों में क़ीमत", "How many rupees went to the fee, what share of your growth that was, and what you end with against the cheap fund. A projection, not a promise.", "फ़ीस में कितने रुपये गए, वह आपकी बढ़त का कितना हिस्सा था, और सस्ते फ़ंड के मुक़ाबले आपके पास कितना बचा। यह अनुमान है, वादा नहीं।")])

_set("emergency", [
    S("/practice?tool=emergency", ".sliders", "1. Enter your money and costs", "1. अपना पैसा और ख़र्च डालिए", "Cash savings, monthly spending, any income that would continue, and investments you could sell if you had to.", "नक़द बचत, मासिक ख़र्च, जो आमदनी जारी रहे, और जो निवेश ज़रूरत पड़ने पर बेच सकें।"),
    S("/practice?tool=emergency", ".em-ring", "2. Months of safety", "2. सुरक्षा के महीने", "The ring is how many months you can go on. Green means you meet the six-month target; amber or red means you are short.", "घेरा बताता है कि आप कितने महीने चल सकते हैं। हरे का मतलब छह महीने का लक्ष्य पूरा; पीले या लाल का मतलब कमी।"),
    S("/practice?tool=emergency", ".em-side", "3. The target and the gap", "3. लक्ष्य और कमी", "The six-month target in rupees, and how far you are from it either way.", "रुपयों में छह महीने का लक्ष्य, और आप उससे कितना आगे या पीछे हैं।")])

_set("digest", [
    S("/practice?tool=digest", ".digest", "The digest, line by line", "सार, पंक्ति दर पंक्ति", "Each line is built from your own data: how the portfolio moved, the best and worst holding, your risk score, and one safety tip. Press Play briefing to hear it.", "हर पंक्ति आपके अपने डेटा से बनी है: पोर्टफ़ोलियो कैसे चला, सबसे अच्छा और बुरा शेयर, आपका जोखिम अंक और एक सुरक्षा सुझाव। सुनने के लिए 'ब्रीफ़िंग चलाइए' दबाइए।")])

_set("rehearsal", [
    S("/practice?tool=rehearsal", ".scgrid", "1. Choose a scam", "1. एक ठगी चुनिए", "Three real scripts: a bank KYC call, a digital-arrest call and a WhatsApp investment tip. Each shows the most you could lose and how many turns it takes.", "तीन असली स्क्रिप्ट: बैंक KYC कॉल, डिजिटल अरेस्ट कॉल और व्हाट्सऐप निवेश टिप। हर एक दिखाती है कि अधिकतम कितना खो सकते हैं और कितनी बारियाँ लगेंगी।"),
    S("/practice?tool=rehearsal", ".sccard:nth-child(1)", "2. Receive the call", "2. कॉल लीजिए", "The caller speaks with pressure, a deadline and a threat. You choose how to reply, and after each turn the coach names the tactic that was used and the safe answer.", "कॉलर दबाव, समय-सीमा और धमकी के साथ बोलता है। आप जवाब चुनते हैं और हर बारी के बाद कोच बताता है कि कौन सी चाल चली गई और सुरक्षित जवाब क्या था।")])

_set("recovery", [
    S("/protect?tool=recovery", ".rcv-pick", "1. What happened?", "1. क्या हुआ?", "Six situations: money taken, an OTP shared, a remote app installed, a fake investment, a fake police call, or a clicked link. Pick the closest.", "छह स्थितियाँ: पैसा निकला, OTP बताया, रिमोट ऐप डाली, नक़ली निवेश, नक़ली पुलिस कॉल, या क्लिक किया हुआ लिंक। सबसे क़रीब वाली चुनिए।"),
    S("/protect?tool=recovery", ".deck-stage", "2. The steps appear in order", "2. क़दम क्रम से आते हैं", "After you choose, a numbered list appears with when to do each step: now, within the hour, today. The helpline 1930 and cybercrime.gov.in are always on it.", "चुनने के बाद क्रमांकित सूची आती है जिसमें हर क़दम का समय है: अभी, एक घंटे में, आज। हेल्पलाइन 1930 और cybercrime.gov.in हमेशा उसमें रहते हैं।", click=".rcv-type:nth-child(1)")])

_set("tip", [
    S("/protect?tool=tip", ".tip-box", "1. Paste the message", "1. संदेश चिपकाइए", "Paste the whole tip: the claim, the promise and any names or numbers. Or press one of the examples under it.", "पूरी टिप चिपकाइए: दावा, वादा और कोई नाम या संख्या। या उसके नीचे का कोई उदाहरण दबाइए।"),
    S("/protect?tool=tip", ".deck-stage", "2. Read the findings", "2. निष्कर्ष पढ़िए", "After checking you get a risk score, the scam tactics found (guaranteed returns, urgency, secrecy, paying to join) and any claim about the company that does not match the dated data on this machine.", "जाँच के बाद आपको जोखिम अंक, मिली ठगी की चालें (पक्का रिटर्न, जल्दबाज़ी, गोपनीयता, जुड़ने के पैसे) और कंपनी के बारे में ऐसा कोई दावा मिलता है जो इस मशीन के तारीख़ वाले डेटा से नहीं मिलता।")])

_set("tax", [
    S("/protect?tool=tax", ".bigstat", "1. What waiting could save", "1. रुकने से क्या बच सकता है", "The headline number is the tax you could save by waiting on holdings that are close to the one-year mark.", "सबसे ऊपर की संख्या वह टैक्स है जो एक साल के निशान के क़रीब वाले शेयरों पर रुकने से बच सकता है।"),
    S("/protect?tool=tax", ".tablewrap", "2. Each holding", "2. हर शेयर", "How long you have held it, the gain, the tax if you sold today, and a plain instruction such as 'wait 134 more days' or 'already long term'.", "कितने दिन रखा, लाभ, आज बेचने पर टैक्स और सीधा निर्देश, जैसे '134 दिन और रुकिए' या 'पहले से दीर्घकालिक'।"),
    S("/protect?tool=tax", ".addlot", "3. Add your real purchase price", "3. अपना असली ख़रीद भाव जोड़िए", "The sample dates are examples. Your cost price is something only you know, so it is never guessed: add it here for your own holdings.", "नमूने की तारीख़ें उदाहरण हैं। आपका ख़रीद भाव सिर्फ़ आप जानते हैं, इसलिए उसका अंदाज़ा नहीं लगाया जाता: अपने शेयरों के लिए यहाँ जोड़िए।")])

_set("panic", [
    S("/protect?tool=panic", ".deck-stage svg", "1. A real crash", "1. एक असली गिरावट", "The line is the real value of your holdings through the crash. The ring marks the lowest point. Drag along it to choose the day you would have sold.", "रेखा गिरावट के दौरान आपके शेयरों का असली मूल्य है। घेरा सबसे निचला बिंदु दिखाता है। बेचने का दिन चुनने के लिए उस पर खींचिए।"),
    S("/protect?tool=panic", ".sim", "2. What selling cost you", "2. बेचने की क़ीमत", "Left: what you locked in by selling. Right: what you would have had by waiting. The difference is the price of panic. Some crashes keep falling, and the note says so.", "बाएँ: बेचकर आपने क्या पक्का किया। दाएँ: रुकने पर क्या मिलता। अंतर ही घबराहट की क़ीमत है। कुछ गिरावटें लगातार जारी रहती हैं, और नोट यह भी कहता है।")])

_set("watch", [
    S("/protect?tool=watch", ".watchlist", "Standing rules", "स्थायी नियम", "Add a rule in words, for example 'tell me if technology goes above 35%'. It is checked every time your portfolio moves and speaks up only when it flips.", "शब्दों में नियम जोड़िए, जैसे 'बताइए अगर टेक्नोलॉजी 35% से ऊपर जाए'। आपका पोर्टफ़ोलियो हिलने पर हर बार जाँचा जाता है और पलटने पर ही बोलता है।")])

_set("trade_check", [
    S("/govern", ".seg button:nth-child(1)", "1. Open Check a trade", "1. 'ट्रेड जाँचिए' खोलिए", "This tab holds the risk firewall: plain arithmetic that no AI can talk around.", "इस टैब में जोखिम की दीवार है: सीधा गणित जिसे कोई AI मना नहीं सकता।", click=".seg button:nth-child(1)"),
    S("/govern", ".card:has(#fw-ticker) .row", "2. Say what you want to do", "2. बताइए क्या करना है", "Choose buy or sell, how many shares and which company, then press Check. The firewall tests the trade against your limit per stock, per industry and for cash.", "ख़रीदें या बेचें, कितने शेयर और कौन सी कंपनी चुनिए, फिर 'जाँचें' दबाइए। फ़ायरवॉल ट्रेड को प्रति शेयर, प्रति उद्योग और नक़द की आपकी सीमा से परखता है।"),
    S("/govern", ".card:has(#fw-ticker) .row:nth-of-type(2)", "3. Or try a ready example", "3. या तैयार उदाहरण आज़माइए", "These examples are chosen to show different outcomes: one passes, one is blocked by the industry limit, one tries to sell more than you own. Tap one and read the verdict and the largest size that would be allowed.", "ये उदाहरण अलग नतीजे दिखाने के लिए हैं: एक पास होता है, एक उद्योग की सीमा से रुकता है, एक आपके पास से ज़्यादा बेचना चाहता है। एक दबाइए और निष्कर्ष तथा सबसे बड़ी अनुमत मात्रा पढ़िए।")])

_set("rebalance", [
    S("/govern", ".seg button:nth-child(2)", "1. Open Rebalance", "1. 'पुनर्संतुलन' खोलिए", "When an industry is over your limit, this builds the fix.", "जब कोई उद्योग आपकी सीमा से ऊपर हो, यह उसका सुधार बनाता है।", click=".seg button:nth-child(2)"),
    S("/govern", ".seg ~ .grid", "2. The smallest set of trades", "2. सबसे छोटे ट्रेड का समूह", "Press 'Build the smallest fix', or 'Only sell, don't buy'. You see each trade, and your limits before and after. Nothing is executed until you approve it.", "'सबसे छोटा सुधार बनाइए' दबाइए, या 'सिर्फ़ बेचिए, ख़रीदिए नहीं'। आपको हर ट्रेड और पहले-बाद की सीमाएँ दिखती हैं। आपकी मंज़ूरी तक कुछ नहीं होता।")])

_set("audit", [
    S("/govern", ".seg button:nth-child(3)", "1. Open the Audit record", "1. 'ऑडिट रिकॉर्ड' खोलिए", "Every decision the system has made goes here, approved or blocked.", "सिस्टम का लिया हर फ़ैसला यहाँ आता है, मंज़ूर या रोका गया।", click=".seg button:nth-child(3)"),
    S("/govern", ".seg ~ .grid", "2. A chain of decisions", "2. फ़ैसलों की कड़ी", "Each row says what was asked, whether it was allowed and why, and carries a fingerprint of the row before it. Change one old row and every fingerprint after it stops matching.", "हर पंक्ति बताती है कि क्या माँगा गया, अनुमति मिली या नहीं और क्यों, और पिछली पंक्ति का फ़िंगरप्रिंट रखती है। कोई पुरानी पंक्ति बदलिए तो उसके बाद का हर फ़िंगरप्रिंट मेल खाना बंद कर देता है।")])

_set("tamper", [
    S("/govern", ".seg button:nth-child(4)", "1. Open the Tamper test", "1. 'छेड़छाड़ परीक्षण' खोलिए", "A live proof that the record cannot be quietly edited.", "इस बात का सीधा सबूत कि रिकॉर्ड को चुपके से बदला नहीं जा सकता।", click=".seg button:nth-child(4)"),
    S("/govern", ".seg ~ .grid .btn", "2. Press the button", "2. बटन दबाइए", "It edits one old entry in a copy of the record. The check then points at the exact entry that no longer matches, so a quiet change is impossible to hide.", "यह रिकॉर्ड की प्रति में एक पुरानी प्रविष्टि बदलता है। जाँच फिर ठीक उस प्रविष्टि की ओर इशारा करती है जो अब मेल नहीं खाती, इसलिए चुपचाप किया बदलाव छिपाना असंभव है।")])
