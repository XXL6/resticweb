import Crypto.Random
from Crypto.Cipher import AES
import hashlib
import logging

SALT_SIZE = 16
NUM_ITERATIONS = 20
AES_MULTIPLE = 16


def generate_key(password, salt, iterations):
    assert iterations > 0
    # print(password.encode('utf-8'))
    # print(salt)
    key = password.encode('utf-8') + salt
    for i in range(iterations):
        key = hashlib.sha256(key).digest()
    return key


def pad_text(text, multiple):
    extra_bytes = len(text) % multiple
    padding_size = multiple - extra_bytes
    padding = chr(padding_size) * padding_size
    padded_text = text.encode('utf-8') + padding.encode('utf-8')
    return padded_text


def unpad_text(padded_text):
    padding_size = padded_text[-1]
    text = padded_text[:-padding_size]
    return text


def encrypt_string(plaintext, password):
    salt = Crypto.Random.get_random_bytes(SALT_SIZE)
    key = generate_key(password, salt, NUM_ITERATIONS)
    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = pad_text(plaintext, AES_MULTIPLE)
    ciphertext = cipher.encrypt(padded_plaintext)
    ciphertext_with_salt = salt + ciphertext
    return ciphertext_with_salt


def decrypt_string(ciphertext, password):
    salt = ciphertext[0:SALT_SIZE]
    ciphertext_sans_salt = ciphertext[SALT_SIZE:]
    key = generate_key(password, salt, NUM_ITERATIONS)
    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = cipher.decrypt(ciphertext_sans_salt)
    plaintext = unpad_text(padded_plaintext)
    return plaintext.decode()
