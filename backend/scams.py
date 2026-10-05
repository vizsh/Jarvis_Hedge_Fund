"""The common scam scripts, each with what the caller says, what is actually true, and what to do about THAT one.

A bank-OTP call, a 'digital arrest', a courier-parcel threat and a task-job offer are different scams with different
tells and different first steps, so the answer is chosen from what the person described, not from the word "scam".
Written by hand in English and Hindi; the helpline 1930 and cybercrime.gov.in are the national reporting routes.
"""
from __future__ import annotations

import re
from typing import Any

_I = re.I


def _s(sid: str, rx: str, head: tuple[str, str], says: tuple[list[str], list[str]], truth: tuple[list[str], list[str]], now: tuple[list[str], list[str]],
       never: tuple[str, str], rehearse: str) -> dict[str, Any]:
    return {"id": sid, "rx": re.compile(rx, _I), "head": {"en": head[0], "hi": head[1]}, "says": {"en": says[0], "hi": says[1]},
            "truth": {"en": truth[0], "hi": truth[1]}, "now": {"en": now[0], "hi": now[1]}, "never": {"en": never[0], "hi": never[1]}, "rehearse": rehearse}


SCAMS: list[dict[str, Any]] = [
    _s("digital_arrest", r"\b(digital arrest|arrest|cbi|police|ed officer|enforcement directorate|narcotics|court|warrant|money laundering|customs officer|video call.{0,20}(police|officer|cbi)|stay on (the )?(video|call))\b",
       ("This is the 'digital arrest' scam. There is no such thing as a digital arrest: no police, CBI, court or customs officer arrests or investigates anyone over a phone or video call.",
        "यह 'डिजिटल अरेस्ट' ठगी है। डिजिटल अरेस्ट जैसी कोई चीज़ नहीं होती: कोई पुलिस, CBI, अदालत या कस्टम अधिकारी फ़ोन या वीडियो कॉल पर किसी को गिरफ़्तार या उसकी जाँच नहीं करता।"),
       (["Your number or Aadhaar is linked to a crime, a parcel with drugs or money laundering.", "Do not tell anyone; stay on the video call; you will be arrested.", "Move your money to a 'safe' or 'RBI' account to be verified."],
        ["आपका नंबर या आधार किसी अपराध, नशीले पदार्थ के पार्सल या मनी लॉन्ड्रिंग से जुड़ा है।", "किसी को न बताइए; वीडियो कॉल पर बने रहिए; वरना गिरफ़्तारी होगी।", "जाँच के लिए अपना पैसा किसी 'सुरक्षित' या 'RBI' खाते में डालिए।"]),
       (["No agency asks you to stay on a video call, to keep it secret, or to transfer money to prove innocence.", "There is no 'RBI safe account'. Real notices come in writing and in person.", "The fear and the secrecy are the trick: they work only if you cannot check with anyone."],
        ["कोई एजेंसी आपको वीडियो कॉल पर रुकने, गुप्त रखने या निर्दोषता साबित करने को पैसे भेजने को नहीं कहती।", "'RBI सुरक्षित खाता' नाम की कोई चीज़ नहीं। असली नोटिस लिखित में और व्यक्तिगत रूप से आते हैं।", "डर और गोपनीयता ही चाल है: यह तभी चलती है जब आप किसी से पूछ न सकें।"]),
       (["Hang up. Do not stay on the video call.", "Tell a family member or friend right now. Nothing needs to be decided today.", "Report on 1930 and cybercrime.gov.in, and take a screenshot of the number."],
        ["फ़ोन काट दीजिए। वीडियो कॉल पर न रुकिए।", "अभी किसी घरवाले या दोस्त को बताइए। आज कुछ तय करने की ज़रूरत नहीं।", "1930 और cybercrime.gov.in पर शिकायत कीजिए और नंबर का स्क्रीनशॉट रखिए।"]),
       ("Do not transfer money 'for verification', and do not share your Aadhaar, PAN or bank details.", "'सत्यापन' के नाम पर पैसा न भेजिए, और आधार, पैन या बैंक की जानकारी साझा न कीजिए।"), "police"),

    _s("bank_otp", r"\b(otp|cvv|pin|bank|sbi|hdfc|icici|axis|kotak|pnb|canara|credit card|debit card|card (block\w*|expir\w*)|account (block\w*|suspend\w*|freez\w*|will be)|kyc|pan (update|link|expire)|aadhaar (update|link)|net ?banking|verification code)\b",
       ("A caller or message asking for an OTP, PIN or CVV is a scam. No bank, however official it sounds, ever asks for these, and it never asks you to 'verify' or 'update KYC' over a call or a link.",
        "OTP, पिन या CVV माँगने वाला कॉल या संदेश ठगी है। कोई भी बैंक, चाहे कितना भी आधिकारिक लगे, ये कभी नहीं माँगता, और कॉल या लिंक से 'सत्यापन' या 'KYC अपडेट' करने को कभी नहीं कहता।"),
       (["Your account or card will be blocked in a few minutes unless you verify now.", "Read out the OTP so we can stop a fraud on your account.", "Your KYC or PAN has expired: click this link to update."],
        ["कुछ मिनटों में आपका खाता या कार्ड बंद हो जाएगा, अभी सत्यापित कीजिए।", "आपके खाते पर ठगी रोकने के लिए OTP बताइए।", "आपका KYC या पैन ख़त्म हो गया: अपडेट के लिए इस लिंक पर क्लिक कीजिए।"]),
       (["The OTP exists to approve a payment: reading it out is approving the thief's payment.", "Banks never create urgency over a call; the deadline of minutes is the pressure tactic.", "Real KYC updates are done in the bank branch or the bank's own app, never through a link in an SMS."],
        ["OTP भुगतान मंज़ूर करने के लिए होता है: उसे बताने का मतलब चोर के भुगतान को मंज़ूरी देना है।", "बैंक कॉल पर कभी जल्दबाज़ी नहीं करते; मिनटों की समय-सीमा ही दबाव की चाल है।", "असली KYC अपडेट बैंक शाखा या बैंक के अपने ऐप में होता है, SMS के लिंक से कभी नहीं।"]),
       (["Hang up without saying anything more.", "Call the number printed on the back of your card, or the bank's official site, to check.", "If you shared anything, block the card or UPI at once through the bank's app and report on 1930."],
        ["बिना कुछ और कहे फ़ोन काट दीजिए।", "जाँच के लिए कार्ड के पीछे छपे नंबर या बैंक की आधिकारिक साइट के नंबर पर ख़ुद फ़ोन कीजिए।", "कुछ भी बताया हो तो बैंक के ऐप से तुरंत कार्ड या UPI बंद कीजिए और 1930 पर शिकायत कीजिए।"]),
       ("Never click the link, and never read out or type an OTP, PIN or CVV for anyone who contacted you first.", "लिंक पर कभी क्लिक न कीजिए, और जिसने आपसे पहले संपर्क किया उसके लिए OTP, पिन या CVV कभी न बोलिए, न लिखिए।"), "kyc"),

    _s("courier", r"\b(courier|parcel|fedex|dhl|blue ?dart|customs|package|consignment|shipment|held at|delivery (fee|failed))\b",
       ("A call or message about a 'parcel in your name' with drugs, fake passports or a customs fee is a scam. Couriers and customs do not demand payment or threaten arrest over the phone.",
        "आपके नाम के किसी 'पार्सल' में नशे, नक़ली पासपोर्ट या कस्टम शुल्क की बात करने वाला कॉल या संदेश ठगी है। कूरियर और कस्टम फ़ोन पर भुगतान नहीं माँगते या गिरफ़्तारी की धमकी नहीं देते।"),
       (["A parcel in your name has been seized or held.", "Pay a small customs or redelivery fee through this link.", "Press 1 to talk to the customs or police officer."],
        ["आपके नाम का पार्सल पकड़ा गया है या रोका गया है।", "इस लिंक से छोटा कस्टम या दोबारा डिलीवरी शुल्क दीजिए।", "कस्टम या पुलिस अधिकारी से बात करने के लिए 1 दबाइए।"]),
       (["If you did not send or order a parcel, there is nothing to pay.", "A real courier sends tracking details you can check on the company's own site.", "The 'press 1' step moves you to a second scammer posing as police, which is how it turns into a digital arrest."],
        ["आपने कोई पार्सल भेजा या मँगाया नहीं तो चुकाने को कुछ नहीं।", "असली कूरियर ट्रैकिंग देता है जिसे आप कंपनी की अपनी साइट पर जाँच सकते हैं।", "'1 दबाइए' आपको पुलिस बनकर बैठे दूसरे ठग तक ले जाता है, इसी तरह यह डिजिटल अरेस्ट बन जाता है।"]),
       (["Do not press any key and do not click the link.", "Check any real order on the courier's own website or app.", "Report the number on the Sanchar Saathi portal and on 1930."],
        ["कोई बटन न दबाइए और लिंक पर क्लिक न कीजिए।", "कोई असली ऑर्डर हो तो कूरियर की अपनी साइट या ऐप पर जाँचिए।", "नंबर की शिकायत संचार साथी पोर्टल और 1930 पर कीजिए।"]),
       ("Never pay a 'release fee' or share your Aadhaar for a parcel you did not expect.", "जिस पार्सल की आपने उम्मीद नहीं की उसके लिए 'रिलीज़ शुल्क' न दीजिए और आधार साझा न कीजिए।"), "police"),

    _s("remote_app", r"\b(anydesk|any desk|quicksupport|quick support|teamviewer|team viewer|rustdesk|screen ?shar\w*|remote (access|control|support|app)|install (an? )?app|download (an? )?app|apk)\b",
       ("Anyone who asks you to install AnyDesk, TeamViewer, QuickSupport or any 'support' app is trying to take over your phone. Installing it lets them see your screen, your OTPs and your banking apps.",
        "जो भी आपसे AnyDesk, TeamViewer, QuickSupport या कोई 'सपोर्ट' ऐप इंस्टॉल करने को कहे, वह आपका फ़ोन अपने क़ब्ज़े में लेना चाहता है। इंस्टॉल करने पर वह आपकी स्क्रीन, OTP और बैंकिंग ऐप देख सकता है।"),
       (["Install this app so we can fix the problem, refund your money or update your account.", "Read us the 9-digit code the app shows.", "Keep the app open while we process your refund."],
        ["यह ऐप इंस्टॉल कीजिए ताकि हम दिक़्क़त ठीक करें, रिफ़ंड दें या खाता अपडेट करें।", "ऐप जो 9 अंकों का कोड दिखाए वह बताइए।", "रिफ़ंड प्रोसेस होने तक ऐप खुला रखिए।"]),
       (["Genuine refunds and fixes never need control of your phone.", "The 9-digit code is the key that gives them access.", "With your screen visible, they can read your OTPs the moment they arrive."],
        ["असली रिफ़ंड और मरम्मत के लिए आपके फ़ोन का नियंत्रण कभी नहीं चाहिए होता।", "9 अंकों का कोड ही वह चाबी है जो उन्हें पहुँच देती है।", "आपकी स्क्रीन दिखने पर वे OTP आते ही पढ़ लेते हैं।"]),
       (["Do not install it. If you already did, uninstall it and switch the phone to airplane mode.", "From another device, change your banking passwords and block your cards and UPI.", "Report on 1930 within the hour: speed is what lets banks freeze the money."],
        ["इंस्टॉल मत कीजिए। कर चुके हों तो अनइंस्टॉल कीजिए और फ़ोन को एयरप्लेन मोड पर कीजिए।", "दूसरे उपकरण से बैंकिंग पासवर्ड बदलिए और अपने कार्ड व UPI बंद कीजिए।", "एक घंटे के भीतर 1930 पर शिकायत कीजिए: गति से ही बैंक पैसा रोक पाते हैं।"]),
       ("Never share the code the app shows, and never install an app from a link or from a caller's instruction.", "ऐप जो कोड दिखाए वह कभी साझा न कीजिए, और किसी लिंक या कॉलर के कहने पर कोई ऐप इंस्टॉल न कीजिए।"), "kyc"),

    _s("task_job", r"\b(part[- ]?time job|work from home|task|like (and )?(subscribe|videos?)|rate (hotels?|products?|apps?)|review (hotels?|products?)|earn (rs|₹)? ?\d+.{0,12}(daily|a day|per day)|youtube (likes|channel)|prepaid task|recharge (to|for) (task|earn)|data entry|online job)\b",
       ("A 'part-time job' that pays you to like videos, rate hotels or complete small tasks, and then asks you to pay to unlock bigger tasks, is a scam. The first small payouts are bait.",
        "ऐसी 'पार्ट-टाइम नौकरी' जो वीडियो लाइक करने, होटल रेट करने या छोटे काम करने के पैसे दे और फिर बड़े काम खोलने के लिए आपसे पैसे माँगे, ठगी है। शुरू के छोटे भुगतान चारा हैं।"),
       (["Earn a few thousand rupees a day from home with simple tasks.", "You received your first small payment, now deposit money to unlock a higher-paying task.", "Your tasks are stuck: pay a fee or more to withdraw the profit."],
        ["घर बैठे सरल कामों से रोज़ कुछ हज़ार रुपये कमाइए।", "आपको पहला छोटा भुगतान मिल गया, अब ज़्यादा कमाई वाला काम खोलने के लिए पैसे जमा कीजिए।", "आपके काम अटके हैं: मुनाफ़ा निकालने के लिए शुल्क या और पैसा दीजिए।"]),
       (["A real employer never asks you to pay to work.", "The small early payouts are paid out of the next victim's money, so that you trust and pay more.", "The 'tasks' have no real customer behind them."],
        ["असली नियोक्ता काम करने के लिए आपसे पैसे नहीं माँगता।", "शुरू के छोटे भुगतान अगले शिकार के पैसे से दिए जाते हैं, ताकि आप भरोसा करके और पैसा दें।", "इन 'कामों' के पीछे कोई असली ग्राहक नहीं होता।"]),
       (["Stop paying immediately: the next 'unlock' payment will not be the last.", "Save the chats, payment receipts and the UPI IDs you paid.", "Report on 1930 and cybercrime.gov.in with those details."],
        ["तुरंत भुगतान रोकिए: अगला 'अनलॉक' भुगतान आख़िरी नहीं होगा।", "चैट, भुगतान की रसीदें और जिन UPI ID में पैसा दिया वे सहेज लीजिए।", "इन ब्योरों के साथ 1930 और cybercrime.gov.in पर शिकायत कीजिए।"]),
       ("Never deposit money to 'unlock' or 'withdraw' earnings from a job or investment app.", "किसी नौकरी या निवेश ऐप की कमाई 'अनलॉक' या 'निकालने' के लिए कभी पैसा जमा न कीजिए।"), "invest"),

    _s("invest_group", r"\b(whatsapp|telegram|instagram|youtube|facebook)\b.{0,50}\b(group|channel|tips?|signals?|guaranteed|sure|returns?|profit|trading|invest\w*|stocks?)\b|\b(guaranteed|assured|sure[- ]?shot|fixed) (returns?|profit|income)\b|\b(double|triple) (my |your |the )?money\b|\b(vip|premium) (group|tips?|channel)\b|\b(trading|investment) (app|platform|group)\b|\b(ipo|stock) (allotment|tip)\b.{0,20}\b(guarantee\w*|sure)\b|\bfake (trading|investment|stock) (app|platform|website)\b",
       ("A group or app promising fixed or guaranteed returns on shares, IPOs or crypto is a classic investment scam. Nobody can guarantee a return, and a real adviser is registered with SEBI and never takes money into a personal account.",
        "शेयर, IPO या क्रिप्टो पर तय या गारंटीशुदा रिटर्न का वादा करने वाला ग्रुप या ऐप क्लासिक निवेश ठगी है। कोई रिटर्न की गारंटी नहीं दे सकता, और असली सलाहकार SEBI में पंजीकृत होता है और निजी खाते में पैसा कभी नहीं लेता।"),
       (["Join our VIP group for guaranteed 10 to 30% returns or a sure-shot IPO allotment.", "Our app shows your profit growing: deposit more to keep it growing or to withdraw.", "Only a few seats are left: pay today."],
        ["हमारे VIP ग्रुप से जुड़िए, 10 से 30% का पक्का रिटर्न या पक्का IPO आवंटन।", "हमारा ऐप आपका मुनाफ़ा बढ़ता दिखाता है: बढ़ाते रहने या निकालने के लिए और जमा कीजिए।", "कुछ ही सीटें बची हैं: आज ही भुगतान कीजिए।"]),
       (["The profit on the screen is a number the app makes up; there is no real trade behind it.", "Withdrawals are blocked with 'tax', 'fee' or 'verification' charges until you stop paying.", "Check any adviser or broker on SEBI's website before paying anyone."],
        ["स्क्रीन का मुनाफ़ा ऐप की गढ़ी हुई संख्या है; उसके पीछे कोई असली ट्रेड नहीं।", "आप भुगतान बंद करें तब तक निकासी 'टैक्स', 'फ़ीस' या 'सत्यापन' के शुल्क से रोकी जाती है।", "किसी को भी पैसा देने से पहले उसके सलाहकार या ब्रोकर होने की जाँच SEBI की वेबसाइट पर कीजिए।"]),
       (["Stop sending money, even to 'recover' what you put in: that is the second scam.", "Keep screenshots of the chats, the app, the bank transfers and the account numbers.", "Report on 1930 and cybercrime.gov.in, and tell your bank at once."],
        ["पैसा भेजना बंद कीजिए, लगाया हुआ 'वापस पाने' के नाम पर भी नहीं: वह दूसरी ठगी है।", "चैट, ऐप, बैंक ट्रांसफ़र और खाता संख्याओं के स्क्रीनशॉट रखिए।", "1930 और cybercrime.gov.in पर शिकायत कीजिए और तुरंत अपने बैंक को बताइए।"]),
       ("Never pay to join a group, and never move money to a personal account or UPI ID for 'investing'.", "ग्रुप से जुड़ने के लिए कभी पैसा न दीजिए, और 'निवेश' के लिए किसी निजी खाते या UPI ID में पैसा न भेजिए।"), "invest"),

    _s("prize", r"\b(lottery|prize|kbc|lucky draw|you (have )?won|winner|gift (card|voucher)?|reward|cashback offer|congratulations|claim (your )?(prize|reward|gift))\b",
       ("A message saying you have won a lottery, prize or reward you never entered for is a scam. Real prizes never ask you to pay a fee, tax or 'processing charge' first.",
        "जिस लॉटरी, इनाम या रिवॉर्ड में आपने हिस्सा नहीं लिया उसे जीतने का संदेश ठगी है। असली इनाम पहले शुल्क, टैक्स या 'प्रोसेसिंग चार्ज' नहीं माँगते।"),
       (["You have won a large prize or a gift.", "Pay a small tax or processing fee to release it.", "Send your bank details to receive the money."],
        ["आपने बड़ा इनाम या उपहार जीता है।", "उसे छुड़ाने के लिए छोटा टैक्स या प्रोसेसिंग शुल्क दीजिए।", "पैसा पाने के लिए अपने बैंक का ब्योरा भेजिए।"]),
       (["You cannot win a draw you did not enter.", "Real winners are never asked to pay to receive a prize.", "Once you pay one fee, new 'charges' keep arriving."],
        ["जिस ड्रॉ में आप शामिल ही नहीं हुए उसे आप जीत नहीं सकते।", "असली विजेताओं से इनाम पाने के लिए पैसा नहीं माँगा जाता।", "एक शुल्क देते ही नए 'चार्ज' आते रहते हैं।"]),
       (["Ignore and delete it. Do not reply or click.", "Block the sender.", "If you paid, report on 1930 and tell your bank."],
        ["अनदेखा करके मिटा दीजिए। जवाब न दीजिए, क्लिक न कीजिए।", "भेजने वाले को ब्लॉक कीजिए।", "भुगतान कर दिया हो तो 1930 पर शिकायत कीजिए और अपने बैंक को बताइए।"]),
       ("Never pay money to receive money.", "पैसा पाने के लिए कभी पैसा न दीजिए।"), "kyc"),

    _s("loan_app", r"\b(loan app|instant loan|quick loan|loan.{0,15}(harass\w*|threat\w*|morph\w*|contacts?|photos?)|recovery agent|app (accessed|has access|took) my (contacts?|photos?|gallery)|pre[- ]?approved loan.{0,30}(fee|processing|insurance))\b",
       ("A loan app that demands a fee before disbursing, asks for access to your contacts and photos, or threatens you with morphed pictures is a predatory or illegal lender. Many are not registered with the RBI.",
        "जो लोन ऐप रक़म देने से पहले शुल्क माँगे, आपके कॉन्टैक्ट और फ़ोटो की पहुँच माँगे, या मॉर्फ़्ड तस्वीरों की धमकी दे, वह शोषणकारी या अवैध ऋणदाता है। इनमें से कई RBI में पंजीकृत नहीं हैं।"),
       (["Instant loan with no documents, but pay a processing or insurance fee first.", "Allow access to contacts, gallery and SMS to continue.", "Repay today or we will message your contacts with your photo."],
        ["बिना काग़ज़ के तुरंत लोन, पर पहले प्रोसेसिंग या बीमा शुल्क दीजिए।", "आगे बढ़ने के लिए कॉन्टैक्ट, गैलरी और SMS की अनुमति दीजिए।", "आज चुकाइए वरना आपकी फ़ोटो के साथ आपके कॉन्टैक्ट्स को संदेश भेजेंगे।"]),
       (["A genuine lender deducts fees from the loan amount and is on the RBI's list of registered digital lenders.", "Threatening your contacts is a crime, not a recovery method.", "The interest and charges are often hidden until after you have borrowed."],
        ["असली ऋणदाता शुल्क क़र्ज़ की रक़म से काटता है और RBI की पंजीकृत डिजिटल ऋणदाताओं की सूची में होता है।", "आपके कॉन्टैक्ट्स को धमकाना अपराध है, वसूली का तरीक़ा नहीं।", "ब्याज और शुल्क अक्सर उधार लेने के बाद ही पता चलते हैं।"]),
       (["Uninstall the app and revoke its permissions in your phone settings.", "Do not pay under threat; keep screenshots of every message.", "Report on 1930 and the cybercrime portal, and tell your contacts that any message from that number is fake."],
        ["ऐप अनइंस्टॉल कीजिए और फ़ोन की सेटिंग में उसकी अनुमतियाँ हटाइए।", "धमकी में आकर भुगतान न कीजिए; हर संदेश का स्क्रीनशॉट रखिए।", "1930 और साइबर क्राइम पोर्टल पर शिकायत कीजिए, और अपने कॉन्टैक्ट्स को बता दीजिए कि उस नंबर का हर संदेश नक़ली है।"]),
       ("Never give a lending app access to your contacts or gallery.", "किसी लोन ऐप को अपने कॉन्टैक्ट या गैलरी की पहुँच कभी न दीजिए।"), "kyc"),

    _s("sim_utility", r"\b((electricity|power|gas|water)\b.{0,30}\b(cut|disconnect\w*|off|stopped|supply)\b|(cut|disconnect\w*) (tonight|today)|sim (card )?(will be |is )?(block\w*|deactivat\w*|disconnect\w*|suspend\w*)|trai|mobile number (will be|is) (block\w*|disconnect\w*)|electricity (bill|connection)|power (cut|disconnect\w*)|gas (connection|subsidy)|disconnect(ed)? (tonight|today))\b",
       ("A message that your SIM, electricity or gas connection will be cut tonight unless you call a number or pay immediately is a scam. Utilities and TRAI do not threaten disconnection through personal numbers.",
        "यह संदेश कि आज रात आपका SIM, बिजली या गैस कनेक्शन कट जाएगा जब तक आप किसी नंबर पर फ़ोन न करें या तुरंत भुगतान न करें, ठगी है। बिजली कंपनी और TRAI निजी नंबरों से कनेक्शन काटने की धमकी नहीं देते।"),
       (["Your connection will be disconnected tonight unless you update your details or pay now.", "Call this mobile number or install the support app.", "Pay a small amount to avoid disconnection."],
        ["अपना ब्योरा अपडेट या भुगतान अभी न किया तो आज रात कनेक्शन कट जाएगा।", "इस मोबाइल नंबर पर फ़ोन कीजिए या सपोर्ट ऐप इंस्टॉल कीजिए।", "कनेक्शन बचाने के लिए छोटी रक़म भरिए।"]),
       (["Real notices come from the official company sender, with your consumer number, and the bill is on its own app or site.", "Disconnection takes notice in writing and a date, not a text for tonight.", "The mobile number to call is the scammer's."],
        ["असली नोटिस कंपनी के आधिकारिक प्रेषक से आते हैं, आपके उपभोक्ता नंबर के साथ, और बिल उसके अपने ऐप या साइट पर होता है।", "कनेक्शन कटने के लिए लिखित नोटिस और तारीख़ चाहिए, आज रात का संदेश नहीं।", "फ़ोन करने को दिया गया मोबाइल नंबर ठग का है।"]),
       (["Do not call the number or install anything.", "Check the bill on the provider's own app or website, or call the number on your bill.", "Report the message to 1930 or to the Sanchar Saathi portal."],
        ["उस नंबर पर फ़ोन न कीजिए और कुछ इंस्टॉल न कीजिए।", "बिल कंपनी के अपने ऐप या वेबसाइट पर देखिए, या बिल पर छपे नंबर पर फ़ोन कीजिए।", "संदेश की शिकायत 1930 या संचार साथी पोर्टल पर कीजिए।"]),
       ("Never pay or share details with the number in a message that threatens disconnection.", "कनेक्शन कटने की धमकी वाले संदेश के नंबर को कभी भुगतान न कीजिए, न ब्योरा दीजिए।"), "kyc"),
]

# the bank/OTP script is the broadest, so it is tried last: a tie goes to the more specific scam
SCAMS.sort(key=lambda s: s["id"] == "bank_otp")

GENERIC = {
    "head": {"en": "Any call, message or link that rushes you, claims to be an official, or asks for money, a code or an app is a red flag. Slow down: the rush is the trick.",
             "hi": "कोई भी कॉल, संदेश या लिंक जो आपको जल्दी में डाले, अधिकारी होने का दावा करे, या पैसा, कोड या ऐप माँगे, ख़तरे की निशानी है। धीमे पड़िए: जल्दबाज़ी ही चाल है।"},
    "says": {"en": ["It is urgent: act in minutes.", "Do not tell anyone.", "Pay, share a code or install an app to fix it."], "hi": ["यह ज़रूरी है: मिनटों में कीजिए।", "किसी को न बताइए।", "ठीक करने के लिए पैसा दीजिए, कोड बताइए या ऐप इंस्टॉल कीजिए।"]},
    "truth": {"en": ["Real institutions give written notice and time.", "Secrecy exists so nobody can tell you it is a scam.", "No official needs an OTP, a PIN or control of your phone."], "hi": ["असली संस्थाएँ लिखित नोटिस और समय देती हैं।", "गोपनीयता इसलिए है कि कोई आपको न बता दे कि यह ठगी है।", "किसी अधिकारी को OTP, पिन या आपके फ़ोन का नियंत्रण नहीं चाहिए।"]},
    "now": {"en": ["Stop and do not act on it.", "Check by calling the official number you find yourself, not one they give you.", "Talk to someone you trust, then report on 1930 if money or codes were involved."], "hi": ["रुकिए और उस पर कुछ मत कीजिए।", "जाँच के लिए ख़ुद ढूँढा आधिकारिक नंबर मिलाइए, उनका दिया नहीं।", "किसी भरोसेमंद से बात कीजिए, और पैसा या कोड गया हो तो 1930 पर शिकायत कीजिए।"]},
    "never": {"en": "Never share an OTP, PIN or CVV, and never install an app or pay because a caller asked.", "hi": "OTP, पिन या CVV कभी साझा न कीजिए, और किसी कॉलर के कहने पर ऐप इंस्टॉल या भुगतान न कीजिए।"},
    "rehearse": "kyc",
}


def pick(text: str) -> dict[str, Any]:
    """The script that best fits what was described (most distinct tells matched), else the general one."""
    best, score = None, 0
    for s in SCAMS:
        hits = {m.group(0).lower() for m in s["rx"].finditer(text)}
        if len(hits) > score:
            best, score = s, len(hits)
    return best if best else {"id": "general", **GENERIC}
