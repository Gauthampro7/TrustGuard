# Unicode confusable mappings

`confusables-17.0.0.txt` is the unmodified Unicode 17.0.0 security mapping file from
https://www.unicode.org/Public/17.0.0/security/confusables.txt .

It is distributed under the included `UNICODE-LICENSE.txt`, retrieved from
https://www.unicode.org/license.txt . See https://www.unicode.org/reports/tr39/ for
the confusable skeleton definition and its limitations.

TrustGuard uses the complete mapping file offline. Its additional risk policy
compares case-folded identifiers and identifies Latin/Cyrillic/Greek mixtures
within individual tokens. That policy is not a complete UTS #39 conformance,
restriction-level, bidirectional skeleton, or Script_Extensions implementation.
