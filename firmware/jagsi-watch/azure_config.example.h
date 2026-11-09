// Azure IoT Hub settings for the JagSi watch (issue #8).
//
// Copy this file to azure_config.h (same folder) and fill it in, or let
// infra/azure/deploy.sh generate azure_config.h for you. azure_config.h is in
// .gitignore because it holds the device's PRIVATE KEY: never commit it, and
// never paste it into a public Wokwi project.
//
// When azure_config.h is absent, sketch.ino builds the Week 6 firmware that
// talks to the public HiveMQ broker, so nothing changes for anyone who has not
// set up Azure yet.
#pragma once

#define JAGSI_AZURE 1

// Host name of the IoT hub, e.g. "jagsi-abal-hub.azure-devices.net"
#define AZURE_IOTHUB_HOST "<your-hub>.azure-devices.net"

// X.509 self-signed device certificate, registered in IoT Hub by thumbprint.
// PEM text, one line per string, each ending in \n.
static const char AZURE_DEVICE_CERT[] =
"-----BEGIN CERTIFICATE-----\n"
"...\n"
"-----END CERTIFICATE-----\n";

static const char AZURE_DEVICE_KEY[] =
"-----BEGIN EC PRIVATE KEY-----\n"
"...\n"
"-----END EC PRIVATE KEY-----\n";
