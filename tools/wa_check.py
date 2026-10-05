"""Sends sample WhatsApp messages through the running backend and prints the replies. Run: python -m tools.wa_check"""
import json
import urllib.parse
import urllib.request

QS = ["hi", "analyse TCS", "what is the difference between SIP and lumpsum", "help me understand the fee slider",
      "my sahukar charges 5 rupees per hundred per month on 50000", "someone asked for my OTP on a call",
      "is this tip good: buy Infosys now, target 1500", "3", "xyzzy plugh"]


def main(base: str = "http://localhost:8000") -> None:
    for q in QS:
        body = urllib.parse.urlencode({"From": "whatsapp:+919800000001", "Body": q, "MessageSid": "T"}).encode()
        req = urllib.request.Request(f"{base}/twilio/webhook?format=json&base={base}", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        msgs = json.load(urllib.request.urlopen(req, timeout=120))["messages"]
        print("Q:", q)
        for m in msgs:
            print("  ", m[:200].replace("\n", " | "))


if __name__ == "__main__":
    main()
