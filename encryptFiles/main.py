import os
import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey,RSAPublicKey
import concurrent.futures
from rich.console import Console
from rich.progress import Progress
from time import time

console=Console()

# 获取32位MD5哈希值
def get_md5_hash(password):
    md5_hash = hashlib.md5(password.encode())
    return md5_hash.hexdigest()

# 生成RSA密钥对
def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

# 用AES加密公钥，并保存到文件
def encrypt_and_save_private_key(private_key:RSAPrivateKey, aes_key:str,folder_path:str):
    pwd=get_md5_hash(aes_key)
    private_key_bytes =private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(pwd.encode())
    )
    with open(os.path.join(folder_path, 'private_key.der'), 'wb') as file:
        file.write(private_key_bytes)

# 加密文件
def encrypt_file(file_path, public_key:RSAPublicKey):
    out=[]
    with open(file_path, 'rb') as file:
        while True:
            data = file.read(100)
            if not data:
                break
            ciphertext = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            out.append(ciphertext)
    with open(file_path + '.enc', 'wb') as file:
        file.write(b'\xc0\x12\x87\x3e\x30\x55\x79\xc2\x25\x43'.join(out))
    os.remove(file_path)

# 解密文件
def decrypt_file(file_path, private_key_byte):
    private_key=serialization.load_der_private_key(private_key_byte,None)
    # console.print(f"[yellow]Decrypting {file_path[:10]}...[/yellow]")
    
    out=[]
    with open(file_path, 'rb') as file:
        datas=file.read().split(b'\xc0\x12\x87\x3e\x30\x55\x79\xc2\x25\x43')
    for data in datas:
        out.append(private_key.decrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        ))
    os.remove(file_path)
    with open(file_path[:-4], 'wb') as file:
        file.write(b"".join(out))
    # console.print(f"[green]Decrypted {file_path[:10]}[/green]")
    return file_path[:-4],out[0]

# 检查文件夹是否已加密
def is_folder_encrypted(folder_path):
    for filepath in  os.listdir(folder_path):
        if filepath.endswith('.enc'):return True
    return False

def is_folder_init(folder_path):
    return os.path.exists(os.path.join(folder_path, 'private_key.der'))
    
# 加密文件夹中的所有文件
def encrypt_folder(folder_path, public_key):
    cnt=0
    for root, dirs, files in os.walk(folder_path):
        cnt+=len(files)
    with Progress() as progress:
        task1 = progress.add_task("[cyan]Encrypting...", total=cnt-2)
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file in ["public_key.pem","private_key.der"]:
                    continue
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and not file_path.endswith('.enc'):
                    encrypt_file(file_path, public_key)
                progress.update(task1, advance=1)

# 解密文件夹中的所有文件
def decrypt_folder(folder_path, private_key):
    # for filename in os.listdir(folder_path):
    #     if filename in ["public_key.pem","private_key.der"]:
    #         continue
    #     file_path = os.path.join(folder_path, filename)
    #     if os.path.isfile(file_path) and file_path.endswith('.enc'):
    #         decrypted_data = decrypt_file(file_path, private_key)
    #         with open(file_path[:-4], 'wb') as file:
    #             file.write(decrypted_data)
    #     progress.advance(task1,1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=16) as executor:
        futures = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file in ["public_key.pem","private_key.der"]:
                    continue
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and file_path.endswith('.enc'):
                    future = executor.submit(decrypt_file, file_path, private_key)
                    futures.append(future)
                
        with Progress() as progress:
            task1 = progress.add_task("[cyan]Decrypting...", total=len(futures))
            while futures:
                for f1 in futures:
                    if f1.done():
                        progress.advance(task1, 1)
                        futures.pop(futures.index(f1))
                        break


# 主函数
def main():
    import sys
    if len(sys.argv)!=2:
        exit(1)
    folder_path = sys.argv[1]  # 指定文件夹路径
    if not is_folder_init(folder_path):
        console.print("[green]Initializing[/green]")
        # 生成RSA密钥对
        private_key, public_key = generate_rsa_key_pair()
        # 获取用户输入的密码并转换为32位MD5哈希值
        pwd = console.input("Enter password: ",password=True)
        encrypt_and_save_private_key(private_key, pwd,folder_path)
        with open (os.path.join(folder_path,'public_key.pem'), 'wb') as f:
            pub = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            f.write(pub)
        # 加密文件夹中的所有文件
        st=time()
        encrypt_folder(folder_path, public_key)
        console.print(f"[green]Encrypted in %.2f s[/green]"%(time()-st))
    else:
        if not is_folder_encrypted(folder_path):
            console.print("[yellow]Encrypt[/yellow]")
            with open(os.path.join(folder_path,'public_key.pem'), 'rb') as f:
                padded_data=f.read()
            public_key = serialization.load_pem_public_key(padded_data)
            st=time()
            encrypt_folder(folder_path, public_key)
            print(f"[green]Encrypted in %.2f s[/green]"%(time()-st))
        else:
            # 加密过，需要解密公钥并解密文件夹中的文件
            console.print("[green]Decrypt[/green]")
            with open(os.path.join(folder_path,'private_key.der'), 'rb') as file:
                encrypted_private_key = file.read()
            pwd = console.input("Enter password: ",password=True)
            
            public_key = serialization.load_der_private_key(
                encrypted_private_key, 
                get_md5_hash(pwd).encode()
            )
            pub = public_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            st=time()
            decrypt_folder(folder_path, pub)
            console.print(f"[green]Decrypted in %.2f s[/green]"%(time()-st))
            

if __name__ == "__main__":
    main()
