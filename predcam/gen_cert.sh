#!/bin/bash
# Generate self-signed cert so iOS Safari allows camera access over LAN
IP=$(hostname -I | awk '{print $1}')
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=predcam" \
  -addext "subjectAltName=IP:${IP},IP:127.0.0.1"
echo ""
echo "Cert generated for IP: ${IP}"
echo "Restart the server — it will auto-detect cert.pem/key.pem and enable HTTPS."
echo "On iOS, visit https://${IP}:8000 first and accept the security warning."
