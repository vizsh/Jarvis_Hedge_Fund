"""Runs many everyday questions through the WhatsApp webhook and reports which ones fall back to the menu."""
import json
import sys
import urllib.parse
import urllib.request

QS = ["difference between SIP and lumpsum", "what is the difference between sip and lump sum?", "lumpsum vs sip", "sip or lumpsum which is better",
      "what is nifty", "how to start investing", "what is pe ratio", "is gold a good investment", "should i buy a house or rent",
      "compare hdfc bank and icici bank", "analyse infosys", "what is a mutual fund", "how are mutual funds taxed", "what is inflation",
      "explain compounding", "what is an emergency fund", "how much emergency fund should i keep", "someone asked for my otp",
      "is this scheme real: double your money in 6 months", "my father lost money on a whatsapp stock tip", "what is diversification",
      "what is an index fund", "how do i become rich", "what is ppf", "difference between nps and ppf", "what is an ipo",
      "is my data private", "what is fd interest tax", "sahukar 5 rupaye sainkda 50000", "what is the capital of france"]
MENU_MARKS = ("Pick from the menu", "नीचे से चुनिए", "can't help", "I can't", "Send MENU")


def send(base, q):
    body = urllib.parse.urlencode({"From": "whatsapp:+919800000099", "Body": q, "MessageSid": "B"}).encode()
    req = urllib.request.Request(f"{base}/twilio/webhook?format=json&base={base}", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(urllib.request.urlopen(req, timeout=120))["messages"]


def main(base="http://localhost:8000"):
    fails = []
    for q in QS:
        first = send(base, q)[0]
        ok = not any(m in first for m in MENU_MARKS)
        print(("OK   " if ok else "MENU ") + q + "  ->  " + first[:110].replace("\n", " | "))
        if not ok:
            fails.append(q)
    print("\nfell back to menu:", len(fails), "of", len(QS))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
