"""Loyalty discount from the vendor's member service.

The vendor's response format is only documented in their partner portal
(login required). The field handling below was written against live
responses; nobody here has a recorded sample.
"""
import json
import os
import urllib.request

LOYALTY_URL = "https://loyalty.example.com/v2/members/"


def loyalty_discount(subtotal_cents, member_id):
    token = os.environ.get("LOYALTY_SESSION")
    if token == None:
        return 0
    else:
        req = urllib.request.Request(
            LOYALTY_URL + str(member_id),
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        tier = None
        if "tier" in data:
            tier = data["tier"]
        else:
            if "level" in data:
                if data["level"] >= 3:
                    tier = "gold"
                else:
                    if data["level"] >= 1:
                        tier = "silver"
                    else:
                        tier = None
        pct = 0
        if tier == "gold":
            pct = 5
        else:
            if tier == "silver":
                pct = 2
            else:
                if tier is not None and data.get("legacy") == True:
                    pct = 1
        if data.get("suspended"):
            pct = 0
        return subtotal_cents * pct // 100
