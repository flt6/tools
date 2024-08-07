import os
import json
import getpass
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad

TARGET_DIR = Path(".")
ENCRYPT_DIR = TARGET_DIR/".encrypt"
PASSWORD_FILE = ENCRYPT_DIR/"password.dat"

def initialize():
    if not ENCRYPT_DIR.exists():
        ENCRYPT_DIR.mkdir()
        key = RSA.generate(2048)
        private_key = key.export_key()
        public_key = key.publickey().export_key()

        with open(ENCRYPT_DIR/"public.pem", "wb") as f:
            f.write(public_key)

        password = getpass.getpass("Enter password for private key encryption: ")
        salt = get_random_bytes(16)
        key = PBKDF2(password, salt, dkLen=32, count=1000000, hmac_hash_module=SHA256)
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(private_key)
        
        with open(ENCRYPT_DIR/"private.pem", "wb") as f:
            f.write(salt + cipher.nonce + tag + ciphertext)
        print("Initialization complete.")
    else:
        print("Already initialized.")

def is_encrypted(filename:Path):
    return filename.suffix == '.encrypt'

def encrypt_files():
    print("Enter encrypt")
    thisfile=Path(__file__)
    if not ENCRYPT_DIR.exists():
        print("Encryption folder not found. Run initialization first.")
        return

    with open(ENCRYPT_DIR/"public.pem", "rb") as f:
        public_key = RSA.import_key(f.read())

    rsa_cipher = PKCS1_OAEP.new(public_key)

    all_files= list(TARGET_DIR.glob("**/*"))
    
    # print(all_files)

    aes_key = get_random_bytes(32)
    encrypted_aes_key = rsa_cipher.encrypt(aes_key)

    password_data = {}
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, "r") as f:
            password_data = json.load(f)

    for file in all_files:
        if not file.is_file():continue
        if ENCRYPT_DIR in file.parents:continue
        if file.samefile(thisfile):continue
        if not is_encrypted(file):
            file_path = file.absolute()
            with open(file_path, "rb") as f:
                plaintext = f.read()

            aes_cipher = AES.new(aes_key, AES.MODE_CBC)
            ciphertext = aes_cipher.encrypt(pad(plaintext, AES.block_size))
            encrypted_filename = file.with_suffix("".join(file.suffixes)+".encrypt")
            try:
                with open(encrypted_filename, "wb") as f:
                    f.write(aes_cipher.iv + ciphertext)
            except OSError as e:
                print("Please rename this(too long):",file_path)
                print("reason: ",e)
                continue
            except Exception as e:
                from traceback import print_exc
                print(f"Cannot read file {file_path}")
                print_exc()
                continue
            os.remove(file_path)
            password_data[encrypted_aes_key.hex()] = password_data.get(encrypted_aes_key.hex(), []) + [str(encrypted_filename)]

    with open(PASSWORD_FILE, "w") as f:
        json.dump(password_data, f)

    print("Files encrypted.")

def decrypt_files():
    print("enable decrypt")
    if not ENCRYPT_DIR.exists():
        print("Encryption folder not found. Run initialization first.")
        return

    password = getpass.getpass("Enter password for private key decryption: ")

    with open(ENCRYPT_DIR/"private.pem", "rb") as f:
        encrypted_private_key = f.read()

    salt, nonce, tag, ciphertext = encrypted_private_key[:16], encrypted_private_key[16:32], encrypted_private_key[32:48], encrypted_private_key[48:]
    key = PBKDF2(password, salt, dkLen=32, count=1000000, hmac_hash_module=SHA256)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    try:
        private_key = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        print("Incorrect password or corrupted file.")
        return

    private_key = RSA.import_key(private_key)
    rsa_cipher = PKCS1_OAEP.new(private_key)

    if not os.path.exists(PASSWORD_FILE):
        print("No encrypted files found.")
        return

    with open(PASSWORD_FILE, "r") as f:
        password_data = json.load(f)

    for encrypted_key_hex, encrypted_files in password_data.items():
        encrypted_aes_key = bytes.fromhex(encrypted_key_hex)
        aes_key = rsa_cipher.decrypt(encrypted_aes_key)

        for encrypted_file in encrypted_files:
            file_path = encrypted_file
            try:
                with open(file_path, "rb") as f:
                    iv, ciphertext = f.read(16), f.read()
            except OSError as e:
                print(f"Cannot read file {file_path}: {e}")
                continue
            except Exception as e:
                from traceback import print_exc
                print(f"Cannot read file {file_path}")
                print_exc()
                continue

            aes_cipher = AES.new(aes_key, AES.MODE_CBC, iv=iv)
            # print(aes_cipher.decrypt(ciphertext))
            plaintext = unpad(aes_cipher.decrypt(ciphertext), AES.block_size)

            original_filename = encrypted_file[:-8]
            with open(original_filename, "wb") as f:
                f.write(plaintext)

            os.remove(file_path)

    os.remove(PASSWORD_FILE)
    print("Files decrypted.")

def main():
    if not ENCRYPT_DIR.exists():
        print("No config exists, initializing...")
        initialize()
        encrypt_files()
        return 0

    action = 'decrypt'
    thisfile=Path(__file__)
    for file in TARGET_DIR.iterdir():
        if not file.is_file():continue
        if file.samefile(thisfile):continue
        if file.suffix != ".encrypt":
            action="encrypt"
            break

    # action = input("Enter 'encrypt' to encrypt files or 'decrypt' to decrypt files: ").strip().lower()
    
    if action == 'encrypt':
        encrypt_files()
    elif action == 'decrypt':
        decrypt_files()
    else:
        print("Invalid action.")

if __name__ == "__main__":
    main()


# python 实现加密时无需输入密码，只需在解密时输入密码。所需加密的文件夹名由常量指定。
# 具体地，初始化（注1）时，RSA生成一对秘钥，将公钥保存，私钥由用户提供的密码进行加密后保存。均保存至encrypt文件夹中。
# 以后的每一次执行（注1），判断文件是否全部被加密（注3），如果否，生成一个随机秘钥，用AES将未加密的文件进行对等加密，并将该随机秘钥用公钥加密后保存在文件中（注2）。如果全部加密，向用户索要密码，对所有文件进行解密（注2）。

# 注1：初始化时在指定的文件夹中建立encrypt文件夹，程序运行时检测该文件夹是否存在，决定是否执行化逻辑。
# 注2：加密后的文件文件名添加.encrypt，文件夹中维护一个文件encrypt/password.dat，储存一个dict，以加密后的随机秘钥为键，值为使用该随机秘钥加密的文件名的list。每次完成解密后，清空password.dat。
# 注3：穷举所有文件，递归，判断是否均以.encrypt结尾