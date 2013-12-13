#!/usr/bin/env python
# coding=utf-8

import gflags
import time
import unittest
import sys
from ct.crypto import cert, error
from ct.crypto.asn1 import oid
from ct.crypto.asn1 import x509_extension as x509_ext
from ct.crypto.asn1 import x509_name

FLAGS = gflags.FLAGS
gflags.DEFINE_string("testdata_dir", "ct/crypto/testdata",
                     "Location of test certs")

class CertificateTest(unittest.TestCase):
    _PEM_FILE = "google_cert.pem"

    # Contains 3 certificates
    # C=US/ST=California/L=Mountain View/O=Google Inc/CN=www.google.com
    # C=US/O=Google Inc/CN=Google Internet Authority
    # C=US/O=Equifax/OU=Equifax Secure Certificate Authority
    _PEM_CHAIN_FILE = "google_chain.pem"
    _DER_FILE = "google_cert.der"
    # An X509v1 certificate
    _V1_PEM_FILE = "v1_cert.pem"

    # A old but common (0.5% of all certs as of 2013-10-01) SSL
    # cert that uses a different or older DER format for Boolean
    # values.
    _PEM_MATRIXSSL = "matrixssl_sample.pem"

    # Self-signed cert by marchnetworks.com for embedded systems
    # and uses start date in form of "0001010000Z" (no seconds)
    _PEM_MARCHNETWORKS = "marchnetworks_com.pem"

    # Self-signed cert by subrigo.net for embedded systems
    # and uses a start date in the form of 121214093107+0000
    _PEM_SUBRIGONET = "subrigo_net.pem"

    # Self-signed cert by promise.com (as of 2013-10-16) that
    # is in use by embedded systems.
    #
    # * has a start date in the format of 120703092726-1200
    # * uses a 512-key RSA key
    _PEM_PROMISECOM = "promise_com.pem"

    # This self-signed cert was used to test proper (or
    # improper) handling of UTF-8 characters in CN
    # See  CVE 2009-2408 for more details
    #
    # Mozilla bug480509
    # https://bugzilla.mozilla.org/show_bug.cgi?id=480509
    # Mozilla bug484111
    # https://bugzilla.mozilla.org/show_bug.cgi?id=484111
    # RedHat bug510251
    # https://bugzilla.redhat.com/show_bug.cgi?id=510251
    _PEM_CN_UTF8 = "cn_utf8.pem"

    # A self-signed cert with null characters in various names
    # Misparsing was involved in CVE 2009-2408 (above) and
    # CVE-2013-4248
    _PEM_NULL_CHARS = "null_chars.pem"

    # A certificate with a negative serial number, and, for more fun,
    # an extra leading ff-octet therein.
    _PEM_NEGATIVE_SERIAL = "negative_serial.pem"

    # A certificate with an ECDSA key and signature.
    _PEM_ECDSA = "ecdsa_cert.pem"

    # A certificate with multiple EKU extensions.
    _PEM_MULTIPLE_EKU = "multiple_eku.pem"

    # A certificate with multiple "interesting" SANs.
    _PEM_MULTIPLE_AN = "multiple_an.pem"

    # A certificate with multiple CN attributes.
    _PEM_MULTIPLE_CN = "multiple_cn.pem"

    # A certificate with authority cert issuer and authority cert serial.
    _PEM_AKID = "authority_keyid.pem"

    @property
    def pem_file(self):
        return FLAGS.testdata_dir + "/" + self._PEM_FILE

    def get_file(self, filename):
        return FLAGS.testdata_dir + "/" + filename

    def cert_from_pem_file(self, filename, strict=True):
        return cert.Certificate.from_pem_file(
            self.get_file(filename), strict_der=strict)

    def test_from_pem_file(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        self.assertTrue(isinstance(c, cert.Certificate))

    def test_certs_from_pem_file(self):
        certs = list(cert.certs_from_pem_file(self.get_file(
            self._PEM_CHAIN_FILE)))
        self.assertEqual(3, len(certs))
        self.assertTrue(all(map(lambda x: isinstance(x, cert.Certificate),
                                certs)))
        self.assertTrue("google.com" in certs[0].print_subject_name())
        self.assertTrue("Google Inc" in certs[1].print_subject_name())
        self.assertTrue("Equifax" in certs[2].print_subject_name())

    def test_from_pem(self):
        with open(self.get_file(self._PEM_FILE)) as f:
            c = cert.Certificate.from_pem(f.read())
        self.assertTrue(isinstance(c, cert.Certificate))

    def test_all_from_pem(self):
        with open(self.get_file(self._PEM_CHAIN_FILE)) as f:
            certs = list(cert.certs_from_pem(f.read()))
        self.assertEqual(3, len(certs))
        self.assertTrue(all(map(lambda x: isinstance(x, cert.Certificate),
                                certs)))
        self.assertTrue("google.com" in certs[0].print_subject_name())
        self.assertTrue("Google Inc" in certs[1].print_subject_name())
        self.assertTrue("Equifax" in certs[2].print_subject_name())

    def test_from_der_file(self):
        c = cert.Certificate.from_der_file(self.get_file(self._DER_FILE))
        self.assertTrue(isinstance(c, cert.Certificate))

    def test_from_der(self):
        with open(self.get_file(self._DER_FILE), "rb") as f:
            cert_der = f.read()
            c = cert.Certificate.from_der(cert_der)
        self.assertTrue(isinstance(c, cert.Certificate))
        self.assertEqual(c.to_der(), cert_der)

    def test_invalid_encoding_raises(self):
        self.assertRaises(error.EncodingError, cert.Certificate.from_der,
                          "bogus_der_string")
        self.assertRaises(error.EncodingError, cert.Certificate.from_pem,
                          "bogus_pem_string")

    def test_to_der(self):
        with open(self.get_file(self._DER_FILE), "rb") as f:
            der_string = f.read()
        c = cert.Certificate(der_string)
        self.assertEqual(der_string, c.to_der())

    def test_parse_matrixssl(self):
        """Test parsing of old MatrixSSL.org sample certificate

        As of 2013-10-01, about 0.5% of all SSL sites use an old
        sample certificate from MatrixSSL.org. It appears it's used
        mostly for various home routers.  Unfortunately it uses a
        non-DER encoding for boolean value: the DER encoding of True
        is 0xFF but this cert uses a BER encoding of 0x01. This causes
        pure DER parsers to break.  This test makes sure we can parse
        this cert without exceptions or errors.
        """
        self.assertRaises(error.ASN1Error,
                          self.cert_from_pem_file, self._PEM_MATRIXSSL)
        c = self.cert_from_pem_file(self._PEM_MATRIXSSL, strict=False)
        issuer = c.print_issuer_name()
        self.assertTrue("MatrixSSL Sample Server" in issuer)

    def test_parse_marchnetworks(self):
        """Test parsing certificates issued by marchnetworks.com."""
        c = self.cert_from_pem_file(self._PEM_MARCHNETWORKS)
        issuer = c.print_issuer_name()
        self.assertTrue("March Networks" in issuer)

        # 0001010000Z
        expected = [2000, 1, 1, 0, 0, 0, 5, 1, 0]
        self.assertEqual(list(c.not_before()), expected)

        # 3001010000Z
        expected = [2030, 1, 1, 0, 0, 0, 1, 1, 0]
        self.assertEqual(list(c.not_after()), expected)

    def test_parse_subrigonet(self):
        """Test parsing certificates issued by subrigo.net

        The certificates issued by subrigo.net (non-root)
        use an start date with time zone.

            Not Before: Dec 14 09:31:07 2012
            Not After : Dec 13 09:31:07 2022 GMT

        """
        c = self.cert_from_pem_file(self._PEM_SUBRIGONET)
        issuer = c.print_issuer_name()
        self.assertTrue("subrigo.net" in issuer)

        # timezone format -- 121214093107+0000
        expected = [2012, 12, 14, 9, 31, 7, 4, 349, 0]
        self.assertEqual(list(c.not_before()), expected)

        # standard format -- 221213093107Z
        expected = [2022, 12, 13, 9, 31, 7, 1, 347, 0]
        self.assertEqual(list(c.not_after()), expected)

    def test_utf8_names(self):
        c = self.cert_from_pem_file(self._PEM_CN_UTF8)
        nameutf8 = "ñeco ñýáěšžěšžřěčíě+ščýáíéřáíÚ"
        unicodename = u"ñeco ñýáěšžěšžřěčíě+ščýáíéřáíÚ"
        # Compare UTF-8 strings directly.
        self.assertEqual(c.print_subject_name(), "CN=" + nameutf8)
        self.assertEqual(c.print_issuer_name(), "CN=" + nameutf8)
        cns = c.subject_common_names()
        self.assertEqual(1, len(cns))
        self.assertEqual(cns[0], nameutf8)
        # Name comparison is unicode-based so decode and compare unicode names.
        # TODO(ekasper): implement proper stringprep-based name comparison
        # and use these test cases there.
        self.assertEqual(cns[0].value.decode("utf8"), unicodename)

    def test_null_chars_in_names(self):
        """Test handling null chars in subject and subject alternative names."""
        c = self.cert_from_pem_file(self._PEM_NULL_CHARS)
        cns = c.subject_common_names()
        self.assertEqual(1, len(cns))
        self.assertEqual("null.python.org\000example.org", cns[0])

        alt_names = c.subject_alternative_names()
        self.assertEqual(len(alt_names), 5)
        self.assertEqual(alt_names[0].component_key(), x509_name.DNS_NAME)
        self.assertEqual(alt_names[0].component_value(),
                         "altnull.python.org\000example.com")
        self.assertEqual(alt_names[1].component_key(), x509_name.RFC822_NAME)
        self.assertEqual(alt_names[1].component_value(),
                         "null@python.org\000user@example.org")
        self.assertEqual(alt_names[2].component_key(),x509_name.URI_NAME)
        self.assertEqual(alt_names[2].component_value(),
                         "http://null.python.org\000http://example.org")

        # the following does not contain nulls.
        self.assertEqual(alt_names[3].component_key(),
                         x509_name.IP_ADDRESS_NAME)
        self.assertEqual(alt_names[3].component_value().as_octets(),
                         (192, 0, 2, 1))
        self.assertEqual(alt_names[4].component_key(),
                         x509_name.IP_ADDRESS_NAME)
        self.assertEqual(alt_names[4].component_value().as_octets(),
                         (32, 1, 13, 184, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1))

    def test_parse_promisecom(self):
        """Test parsing certificates issued by promise.com

        The certificates issued by promise.com (non-root)
        use an start date with time zone (and are 512-bit)

            Not Before: Jun 29 15:32:48 2011
            Not After : Jun 26 15:32:48 2021 GMT
        """

        c = self.cert_from_pem_file(self._PEM_PROMISECOM)
        issuer = c.print_issuer_name()
        self.assertTrue("Promise Technology Inc." in issuer)

        # 110629153248-1200
        expected = [2011,6,29,15,32,48,2,180,0]
        self.assertEqual(list(c.not_before()), expected)

        # 210626153248Z
        expected = [2021,6,26,15,32,48,5,177,0]
        self.assertEqual(list(c.not_after()), expected)

    def test_parse_ecdsa_cert(self):
        # TODO(ekasper): Also test the signature algorithm once it's exposed
        # in the API.
        c = self.cert_from_pem_file(self._PEM_ECDSA)
        self.assertTrue("kmonos.jp" in c.print_subject_name())

    def test_print_subject_name(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        subject = c.print_subject_name()
        # C=US, ST=California, L=Mountain View, O=Google Inc, CN=*.google.com
        self.assertTrue("US" in subject)
        self.assertTrue("California" in subject)
        self.assertTrue("Mountain View" in subject)
        self.assertTrue("Google Inc" in subject)
        self.assertTrue("*.google.com" in subject)

    def test_print_issuer_name(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        issuer = c.print_issuer_name()
        # Issuer: C=US, O=Google Inc, CN=Google Internet Authority
        self.assertTrue("US" in issuer)
        self.assertTrue("Google Inc" in issuer)
        self.assertTrue("Google Internet Authority" in issuer)

    def test_subject_common_names(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        cns = c.subject_common_names()
        self.assertEqual(1, len(cns))
        self.assertEqual("*.google.com", cns[0])

    def test_multiple_subject_common_names(self):
        c = self.cert_from_pem_file(self._PEM_MULTIPLE_CN)
        cns = c.subject_common_names()
        self.assertItemsEqual(cns, ["www.rd.io", "rdio.com", "rd.io",
                                    "api.rdio.com", "api.rd.io",
                                    "www.rdio.com"])

    def test_subject_dns_names(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        dns_names = c.subject_dns_names()
        self.assertEqual(44, len(dns_names))
        self.assertTrue("*.youtube.com" in dns_names)

    def test_subject_ip_addresses(self):
        c = self.cert_from_pem_file(self._PEM_MULTIPLE_AN)
        ips = c.subject_ip_addresses()
        self.assertEqual(1, len(ips))
        self.assertEqual((129, 48, 105, 104), ips[0].as_octets())

    def test_subject_alternative_names(self):
        cert = self.cert_from_pem_file(self._PEM_MULTIPLE_AN)
        sans = cert.subject_alternative_names()
        self.assertEqual(4, len(sans))

        self.assertEqual(x509_name.DNS_NAME, sans[0].component_key())
        self.assertEqual("spires.wpafb.af.mil", sans[0].component_value())

        self.assertEqual(x509_name.DIRECTORY_NAME, sans[1].component_key())
        self.assertTrue(isinstance(sans[1].component_value(), x509_name.Name),
        sans[1].component_value())

        self.assertEqual(x509_name.IP_ADDRESS_NAME, sans[2].component_key())
        self.assertEqual((129, 48, 105, 104),
        sans[2].component_value().as_octets())

        self.assertEqual(x509_name.URI_NAME, sans[3].component_key())
        self.assertEqual("spires.wpafb.af.mil", sans[3].component_value())

    def test_no_alternative_names(self):
        c = cert.Certificate.from_pem_file(self.get_file(self._V1_PEM_FILE))
        self.assertEqual(0, len(c.subject_alternative_names()))
        self.assertEqual(0, len(c.subject_dns_names()))
        self.assertEqual(0, len(c.subject_ip_addresses()))

    def test_validity(self):
        certs = list(cert.certs_from_pem_file(
            self.get_file(self._PEM_CHAIN_FILE)))
        self.assertEqual(3, len(certs))
        # notBefore: Sat Aug 22 16:41:51 1998 GMT
        # notAfter: Wed Aug 22 16:41:51 2018 GMT
        c = certs[2]
        # These two will start failing in 2018.
        self.assertTrue(c.is_temporally_valid_now())
        self.assertFalse(c.is_expired())

        self.assertFalse(c.is_not_yet_valid())

        # Aug 22 16:41:51 2018
        self.assertTrue(c.is_temporally_valid_at(time.gmtime(1534956111)))
        # Aug 22 16:41:52 2018
        self.assertFalse(c.is_temporally_valid_at(time.gmtime(1534956112)))

        # Aug 22 16:41:50 1998
        self.assertFalse(c.is_temporally_valid_at(time.gmtime(903804110)))
        # Aug 22 16:41:51 1998
        self.assertTrue(c.is_temporally_valid_at(time.gmtime(903804111)))

    def test_basic_constraints(self):
        certs = list(cert.certs_from_pem_file(
            self.get_file(self._PEM_CHAIN_FILE)))
        self.assertFalse(certs[0].basic_constraint_ca())
        self.assertTrue(certs[1].basic_constraint_ca())
        self.assertIsNone(certs[0].basic_constraint_path_length())
        self.assertEqual(0, certs[1].basic_constraint_path_length())

    def test_version(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        self.assertEqual(2, c.version())

    def test_serial_number(self):
        c = self.cert_from_pem_file(self._PEM_FILE)
        self.assertEqual(454887626504608315115709, c.serial_number())

    def test_negative_serial_number(self):
        # Fails because of the leading ff-octet.
        self.assertRaises(error.ASN1Error, self.cert_from_pem_file,
            self._PEM_NEGATIVE_SERIAL)
        c = self.cert_from_pem_file(self._PEM_NEGATIVE_SERIAL,
                                    strict=False)
        self.assertEqual(-218943125988803304701934765446014018,
                          c.serial_number())

    def test_v1_cert(self):
        c = self.cert_from_pem_file(self._V1_PEM_FILE)
        self.assertEqual(0, c.version())
        self.assertIsNone(c.basic_constraint_ca())

    def test_fingerprint(self):
        c = cert.Certificate.from_der_file(self.get_file(self._DER_FILE))
        self.assertEqual(c.fingerprint().encode("hex"),
                         "570fe2e3bfee986ed4a158aed8770f2e21614659")
        self.assertEqual(c.fingerprint("sha1").encode("hex"),
                         "570fe2e3bfee986ed4a158aed8770f2e21614659")
        self.assertEqual(c.fingerprint("sha256").encode("hex"),
                         "6d4106b4544e9e5e7a0924ee86a577ffefaadae8b8dad73413a7"
                         "d874747a81d1")

    def test_key_usage(self):
        c = cert.Certificate.from_pem_file(self.get_file(self._PEM_FILE))
        self.assertTrue(c.key_usage(x509_ext.KeyUsage.DIGITAL_SIGNATURE))

        certs = [c for c in cert.certs_from_pem_file(self.get_file(
            self._PEM_CHAIN_FILE))]
        # This leaf cert does not have a KeyUsage extension.
        self.assertEqual([], certs[0].key_usages())
        self.assertIsNone(certs[0].key_usage(
            x509_ext.KeyUsage.DIGITAL_SIGNATURE))

        # The second cert has keyCertSign and cRLSign.
        self.assertIsNotNone(certs[1].key_usage(
            x509_ext.KeyUsage.DIGITAL_SIGNATURE))
        self.assertFalse(certs[1].key_usage(
            x509_ext.KeyUsage.DIGITAL_SIGNATURE))
        self.assertTrue(certs[1].key_usage(x509_ext.KeyUsage.KEY_CERT_SIGN))
        self.assertTrue(certs[1].key_usage(x509_ext.KeyUsage.CRL_SIGN))
        self.assertItemsEqual([x509_ext.KeyUsage.KEY_CERT_SIGN,
                               x509_ext.KeyUsage.CRL_SIGN],
                              certs[1].key_usages())

    def test_extended_key_usage(self):
        certs = [c for c in cert.certs_from_pem_file(self.get_file(
            self._PEM_CHAIN_FILE))]
        self.assertTrue(certs[0].extended_key_usage(oid.ID_KP_SERVER_AUTH))
        self.assertIsNotNone(
            certs[0].extended_key_usage(oid.ID_KP_CODE_SIGNING))
        self.assertFalse(certs[0].extended_key_usage(oid.ID_KP_CODE_SIGNING))
        self.assertItemsEqual([oid.ID_KP_SERVER_AUTH, oid.ID_KP_CLIENT_AUTH],
                              certs[0].extended_key_usages())

        # EKU is normally only found in leaf certs.
        self.assertIsNone(certs[1].extended_key_usage(oid.ID_KP_SERVER_AUTH))
        self.assertEqual([], certs[1].extended_key_usages())

    def test_multiple_extensions(self):
        self.assertRaises(error.ASN1Error, cert.Certificate.from_pem_file,
                          self.get_file(self._PEM_MULTIPLE_EKU))

        c = cert.Certificate.from_pem_file(self.get_file(self._PEM_MULTIPLE_EKU),
                                           strict_der=False)
        self.assertTrue("www.m-budget-mobile-abo.ch" in c.subject_common_names())
        self.assertRaises(cert.CertificateError, c.extended_key_usages)

    def test_key_identifiers(self):
        certs = [c for c in cert.certs_from_pem_file(self.get_file(
            self._PEM_CHAIN_FILE))]

        self.assertEqual("\x12\x4a\x06\x24\x28\xc4\x18\xa5\x63\x0b\x41\x6e\x95"
                         "\xbf\x72\xb5\x3e\x1b\x8e\x8f",
                         certs[0].subject_key_identifier())

        self.assertEqual("\xbf\xc0\x30\xeb\xf5\x43\x11\x3e\x67\xba\x9e\x91\xfb"
                         "\xfc\x6a\xda\xe3\x6b\x12\x24",
                         certs[0].authority_key_identifier())

        self.assertIsNone(certs[0].authority_key_identifier(
            identifier_type=x509_ext.AUTHORITY_CERT_ISSUER))
        self.assertIsNone(certs[0].authority_key_identifier(
            identifier_type=x509_ext.AUTHORITY_CERT_SERIAL_NUMBER))

        self.assertEqual(certs[0].authority_key_identifier(),
                         certs[1].subject_key_identifier())

        c = self.cert_from_pem_file(self._PEM_AKID)

        cert_issuers = c.authority_key_identifier(
            identifier_type=x509_ext.AUTHORITY_CERT_ISSUER)
        self.assertEqual(1, len(cert_issuers))

        # A DirectoryName.
        cert_issuer = cert_issuers[0]
        self.assertEqual(x509_name.DIRECTORY_NAME, cert_issuer.component_key())
        self.assertEqual(["KISA RootCA 1"],
                         cert_issuer.component_value().attributes(
                             oid.ID_AT_COMMON_NAME))
        self.assertEqual(10119, c.authority_key_identifier(
            identifier_type=x509_ext.AUTHORITY_CERT_SERIAL_NUMBER))


if __name__ == "__main__":
    sys.argv = FLAGS(sys.argv)
    unittest.main()
