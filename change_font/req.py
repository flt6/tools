from application_json import ApplicationJsonMethods
from base64 import b64encode
from json import dump, load,loads
from os.path import exists


class Req(ApplicationJsonMethods):
    def __init__(self, key_id: str = None, key_sec: str = None,warn=True):
        if key_id is None or key_sec is None:
            self.ready = self.from_file()
        else:
            self.key_id = key_id
            self.key_sec = key_sec
            self.ready = True
        if self.ready:
            super().__init__(self.key_id, self.key_sec)
        elif warn:
            raise Warning("Req is not ready!")

    def from_file(self) -> bool:
        if exists("Config.json"):
            with open("Config.json", "r") as f:
                data = load(f)
                self.key_id = data["id"]
                self.key_sec = data["sec"]
                return True
        else:
            return False
        
    def to_file(self) -> None:
        data={"id":self.key_id, "sec":self.key_sec}
        with open("Config.json", "w") as f:
            dump(data,f)
    
    def set(self,key_id: str, key_sec: str):
        self.key_id = key_id
        self.key_sec = key_sec
        self.ready = True
        self.to_file()
        super().__init__(key_id, key_sec)

    def __call__(self,url:str,filename:str,**argvs) -> dict:
        with open(filename,"rb") as f:
            file=b64encode(f.read()).decode()
            parms=dict(image_base64=file,**argvs)
        ret=self.post(url,parms)
        # print(ret)
        return loads(ret)