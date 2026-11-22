#pragma once
struct Client {};
struct WiFiClientSecure : Client { void setCACert(const char*) {} void setCertificate(const char*) {} void setPrivateKey(const char*) {} };
