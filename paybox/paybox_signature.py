# coding: utf-8
import urllib
import base64
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA


class Signature():

    def verify(self, signature, msg, key_path):
        """ check if the signature is correct according to the public key path given
            and the message """
        f = open(key_path, 'r')
        key = RSA.importKey(f.read())
        h = SHA.SHA1Hash().new(msg)
        verifier = PKCS1_v1_5.new(key)
        signature = urllib.unquote(signature)
        signature = base64.b64decode(signature)
        return verifier.verify(h, signature)
