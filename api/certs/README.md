# Certificados públicos de PostgreSQL Azure

Bundle azure-postgresql-roots.pem descargado por HTTPS de los enlaces de Microsoft Learn el 11/09/2026. CA=true y firmas propias verificadas. No contiene claves privadas.

- DigiCert Global Root G2: SHA256 cb3ccbb76031e5e0138f8dd39a23f9de47ffc35e43c1144cea27d46a5ab1cb5f; caduca 15/01/2038.
- Microsoft RSA Root Certificate Authority 2017: SHA256 c741f70f4b2a8d88bf2e71c14122ef53ef10eba0cfa5e64cfa20f418853073e0; caduca 18/07/2042.

Fuentes: https://cacerts.digicert.com/DigiCertGlobalRootG2.crt y https://www.microsoft.com/pkiops/certs/Microsoft%20RSA%20Root%20Certificate%20Authority%202017.crt.

Verificar la cadena vigente en Azure antes de publicar; renovar desde los emisores cuando Microsoft cambie la confianza. No colocar certificados VPN, de servidor o claves privadas en este directorio.
